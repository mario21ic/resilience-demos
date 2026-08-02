"""Demo del patron de resiliencia: Throttling.

El [rate limiting](../3-rate-limiting) protege al servidor
**rechazando** de inmediato lo que supera el limite. El throttling
persigue el mismo objetivo (no dejar que la demanda supere la
capacidad sostenible) pero con otra herramienta: en vez de rechazar,
**encola y demora** el exceso, procesandolo a un ritmo constante.

La diferencia importa: un cliente que recibe un rechazo tiene que
decidir que hacer (reintentar, mostrar un error, usar un fallback). Un
cliente que recibe una respuesta exitosa, aunque tarde un poco mas de
lo normal, no tiene que hacer nada distinto. El throttling cambia
latencia por disponibilidad; el rate limiting cambia una fraccion de
los requests por proteccion inmediata.

Ninguna cola puede ser infinita, asi que el throttling tambien
rechaza — pero solo cuando la espera resultante ya no es razonable,
no ante la primera rafaga.

Este demo tiene dos partes:

  Parte 1: compara, request a request, un rechazo inmediato (el mismo
           concepto que el token bucket de rate limiting) contra un
           leaky bucket que encola con espera acotada.
  Parte 2: el mismo comportamiento contra un endpoint HTTP real,
           midiendo la latencia observada por el cliente en una rafaga
           concurrente.
"""
import json
import threading
import time
import urllib.error
import urllib.request

from leaky_bucket import LeakyBucketThrottle, QueueFullError
from server import start_server

HOST, PORT = "localhost", 8772
BASE_URL = f"http://{HOST}:{PORT}/"

N_BURST = 10


class ImmediateRejectLimiter:
    """El mismo balde que un rate limiter tipo token bucket (ver
    3-rate-limiting), pero SIN cola: lo que no entra se rechaza al
    instante, sin espera. Se usa aca solo como punto de comparacion.
    """

    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_refill = 0.0

    def allow(self, now: float) -> bool:
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


# --- Parte 1: rechazo inmediato vs. cola con espera acotada ---------------


def compare_reject_vs_delay():
    print("Parte 1: rechazo inmediato (rate limiting) vs. cola con espera acotada (throttling)")
    print(f"Rafaga de {N_BURST} requests que llegan practicamente al mismo instante (t=0).\n")

    limiter = ImmediateRejectLimiter(rate=5.0, capacity=5.0)
    throttle = LeakyBucketThrottle(rate=5.0, max_queue_size=5)

    header = f"{'request':>8} | {'rate limiter (rechazo inmediato)':>34} | {'throttle (leaky bucket)':>30}"
    print(header)
    print("-" * len(header))

    accepted_limiter = accepted_throttle = 0
    for i in range(N_BURST):
        now = 0.0  # los N llegan practicamente juntos

        if limiter.allow(now):
            accepted_limiter += 1
            limiter_result = "aceptado (sin espera)"
        else:
            limiter_result = "RECHAZADO"

        try:
            scheduled_at = throttle.schedule(now)
            accepted_throttle += 1
            throttle_result = f"aceptado, espera {scheduled_at:.2f}s"
        except QueueFullError:
            throttle_result = "RECHAZADO (cola llena)"

        print(f"{i + 1:>8} | {limiter_result:>34} | {throttle_result:>30}")

    print(f"\nTotal aceptado -> rate limiter: {accepted_limiter}/{N_BURST}, throttle: {accepted_throttle}/{N_BURST}")
    print("El throttle acepta mas requests en total, a costa de que varios esperan;")
    print("el rate limiter acepta menos, pero ninguno de los aceptados espera nada.\n")


# --- Parte 2: endpoint HTTP real, rafaga concurrente ----------------------


def call_resource(index: int, results: list, lock: threading.Lock):
    started = time.monotonic()
    req = urllib.request.Request(f"{BASE_URL}api/resource")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as response:
            status = response.status
            body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = json.loads(exc.read())
    elapsed = time.monotonic() - started
    with lock:
        results.append((index, status, elapsed, body))


def demo_http_throttling():
    print("Parte 2: endpoint HTTP real con throttling (leaky bucket, tasa=5/s, cola max=5)\n")
    print(f"Rafaga de {N_BURST} requests CONCURRENTES (todas llegan casi al mismo tiempo):")

    results = []
    lock = threading.Lock()
    threads = [threading.Thread(target=call_resource, args=(i, results, lock)) for i in range(N_BURST)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for index, status, elapsed, body in sorted(results, key=lambda r: r[0]):
        marker = "200" if status == 200 else str(status)
        print(f"  request {index + 1:>2}: {marker} en {elapsed:.2f}s -> {body}")


def main():
    compare_reject_vs_delay()

    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)

    demo_http_throttling()

    server.shutdown()


if __name__ == "__main__":
    main()
