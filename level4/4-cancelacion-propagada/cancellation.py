"""Cancelacion propagada: cuando un cliente se rinde (su deadline
vence, o cancela explicitamente), esa señal deberia liberar TODO el
trabajo que se estaba haciendo en su nombre — no solo del lado del
cliente, sino tambien en el servidor y en cualquier llamada aguas
abajo que ese request haya disparado. Es el mismo concepto que el
`context.Context` cancelable de Go, o la deteccion de desconexion de
un stream de gRPC.

Sin esto, un servidor sigue procesando "requests zombie": trabajo
cuyo resultado nadie va a leer nunca, porque el cliente que lo pidio
ya se fue (y, tipicamente, ya reintento — ver
[level1/2-retry](../../level1/2-retry)). Eso no es solo un
desperdicio aislado: bajo carga sostenida, el trabajo zombie compite
por los mismos recursos (threads, conexiones) que hacen falta para
procesar el trabajo REAL, incluyendo los reintentos — un problema que
se retroalimenta solo.
"""
import random

WORKERS = 10
CLIENT_DEADLINE = 20     # ticks: cuanto espera el cliente antes de rendirse y reintentar
SLOW_WINDOW = (50, 100)  # el incidente: la dependencia se pone lenta durante estos ticks
ARRIVAL_P = 0.8          # probabilidad de que llegue un request nuevo en cada tick


def draw_duration(rng: random.Random, t: int) -> float:
    if SLOW_WINDOW[0] <= t < SLOW_WINDOW[1]:
        return rng.uniform(30.0, 50.0)
    return rng.uniform(5.0, 15.0)


class Job:
    __slots__ = ("remaining", "age", "abandoned")

    def __init__(self, duration: float):
        self.remaining = duration
        self.age = 0
        self.abandoned = False


def simulate_pileup(rng: random.Random, propagate_cancellation: bool, ticks: int):
    """Simula un pool fijo de `WORKERS` procesando requests, con un
    incidente temporal que hace que muchos excedan el deadline del
    cliente y generen un retry.

    Si `propagate_cancellation` es True, el worker que atendia un
    request abandonado se libera EN EL MISMO INSTANTE en que el
    cliente se rinde. Si es False, el worker sigue "atendiendo" al
    request abandonado hasta que termina solo — trabajo zombie que ya
    no le sirve a nadie, pero que sigue ocupando un recurso real.

    Devuelve (longitudes_de_cola, ticks_de_worker_desperdiciados,
    ticks_de_worker_utiles, cantidad_de_retries_generados).
    """
    busy: list = []
    queue: list = []
    queue_lengths = []
    wasted_worker_ticks = 0
    useful_worker_ticks = 0
    retries_generated = 0

    for t in range(ticks):
        if rng.random() < ARRIVAL_P:
            queue.append(Job(draw_duration(rng, t)))

        while len(busy) < WORKERS and queue:
            busy.append(queue.pop(0))

        still_busy = []
        for job in busy:
            job.age += 1
            job.remaining -= 1

            if not job.abandoned and job.age >= CLIENT_DEADLINE and job.remaining > 0:
                job.abandoned = True
                retries_generated += 1
                queue.append(Job(draw_duration(rng, t)))
                if propagate_cancellation:
                    continue  # se libera el worker ya mismo, no se re-agrega a still_busy

            if job.remaining <= 0:
                continue

            still_busy.append(job)
            if job.abandoned:
                wasted_worker_ticks += 1
            else:
                useful_worker_ticks += 1

        busy = still_busy
        queue_lengths.append(len(queue))

    return queue_lengths, wasted_worker_ticks, useful_worker_ticks, retries_generated


def find_recovery_tick(queue_lengths: list, after: int, window: int = 10):
    """El primer tick, buscando a partir de `after` (tipicamente el
    fin del incidente), a partir del cual la cola se mantiene en <=1
    durante `window` ticks seguidos — la señal de que el sistema ya
    volvio a un estado estable."""
    for t in range(after, len(queue_lengths)):
        if all(q <= 1 for q in queue_lengths[t:t + window]):
            return t
    return None
