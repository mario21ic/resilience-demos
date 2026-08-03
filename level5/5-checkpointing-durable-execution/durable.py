"""Checkpointing / durable execution: el mecanismo detras de motores
de workflows como Temporal, AWS Step Functions o Restate. Un workflow
largo (varios pasos, posiblemente horas o dias entre uno y otro) tiene
que sobrevivir a que el WORKER que lo esta ejecutando se caiga o se
reemplace (un deploy, un crash, un reinicio) — sin perder progreso ni
repetir efectos secundarios ya aplicados.

La idea: cada paso que tiene un efecto en el mundo real (cobrar,
reservar, enviar) se registra en un historial DURABLE antes de seguir
adelante. Si el worker muere, uno nuevo puede tomar el workflow desde
cero y volver a "ejecutar" la misma funcion — pero para los pasos que
ya estan en el historial, en vez de repetir el efecto real, se
devuelve el resultado ya grabado (esto es "replay"). Solo los pasos
que todavia no estan en el historial se ejecutan de verdad.

Esto exige que la funcion del workflow sea DETERMINISTICA: dada la
misma secuencia de resultados de pasos previos, siempre tiene que
decidir hacer los mismos pasos siguientes, en el mismo orden — sin eso,
el replay podria no coincidir con lo que realmente paso.
"""


class WorkerCrashed(Exception):
    pass


class History:
    """El registro durable de resultados de pasos ya ejecutados. En un
    sistema real esto se persiste en una base de datos o un log
    replicado; aca es una lista en memoria para poder inspeccionarla
    facil en el demo.
    """

    def __init__(self):
        self.entries: dict = {}

    def has(self, step_name: str) -> bool:
        return step_name in self.entries

    def get(self, step_name: str):
        return self.entries[step_name]

    def record(self, step_name: str, result):
        self.entries[step_name] = result


class World:
    """Los efectos REALES del workflow — lo que le pasa al negocio,
    no al programa. Cuenta cuantas veces se ejecuto cada efecto de
    verdad, para poder detectar duplicados.
    """

    def __init__(self):
        self.reservations = 0
        self.charges = 0
        self.shipments = 0
        self.notifications = 0

    def reserve_inventory(self):
        self.reservations += 1
        return "inventario reservado"

    def charge_payment(self):
        self.charges += 1
        return "pago cobrado"

    def ship_order(self):
        self.shipments += 1
        return "pedido enviado"

    def notify_customer(self):
        self.notifications += 1
        return "cliente notificado"


def run_order_workflow(world: World, history: History, crash_after_real_steps: int = None):
    """La funcion del workflow: siempre pide los mismos 4 pasos, en el
    mismo orden. Para cada uno, si ya esta en el historial, lo REPLAYEA
    (usa el resultado grabado, sin tocar `world`); si no, lo ejecuta de
    verdad y lo graba antes de seguir.

    `crash_after_real_steps` simula que el worker muere despues de
    ejecutar esa cantidad de pasos REALES (no contando los que se
    replayearon) — para poder forzar el punto exacto de la caida en el
    demo.
    """
    steps = [
        ("reserve_inventory", world.reserve_inventory),
        ("charge_payment", world.charge_payment),
        ("ship_order", world.ship_order),
        ("notify_customer", world.notify_customer),
    ]

    real_steps_executed = 0
    results = []

    for step_name, side_effect_fn in steps:
        if history.has(step_name):
            results.append(history.get(step_name))  # replay: NINGUN efecto real
            continue

        if crash_after_real_steps is not None and real_steps_executed >= crash_after_real_steps:
            raise WorkerCrashed(f"el worker murio antes de ejecutar '{step_name}'")

        result = side_effect_fn()
        history.record(step_name, result)
        real_steps_executed += 1
        results.append(result)

    return results
