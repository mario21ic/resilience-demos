"""Demo del patron de resiliencia: Bulkhead.

El circuit breaker (level2/1) protege a la DEPENDENCIA de que el
cliente le siga mandando trafico cuando esta degradada. El bulkhead
resuelve un problema distinto: protege al CLIENTE de si mismo, cuando
varias dependencias comparten los mismos recursos limitados (threads,
conexiones, colas).

El escenario clasico: la app llama a `service_a` y a `service_b`, dos
dependencias sin ninguna relacion entre si. Si ambas comparten el
mismo pool de recursos del lado del cliente y `service_a` se pone
lenta, cada llamada a A ocupa un lugar del pool durante mas tiempo —
eventualmente el pool se llena de llamadas a A y las llamadas a B
(que en si misma esta perfectamente sana) tambien empiezan a fallar,
simplemente porque no consiguen un lugar libre. Un problema de A
termina tumbando a B sin que exista ninguna razon tecnica para que eso
pase, mas alla de compartir el mismo pool.

El bulkhead le da a cada dependencia su PROPIO pool aislado (aca, un
`Bulkhead` = un semaforo con limite propio). Si A se degrada, su pool
se satura y algunas llamadas a A se rechazan — pero el pool de B ni se
entera.

Este demo lanza una rafaga de 12 llamadas a service_a (lento) y 4 a
service_b (sano) al mismo tiempo, y compara:

  Escenario 1: A y B comparten un unico Bulkhead (pool compartido).
  Escenario 2: A y B tienen cada uno su propio Bulkhead (aislados).
"""
import threading
import time
import urllib.error
import urllib.request

from bulkhead import Bulkhead, BulkheadFullError
from server import start_server

HOST, PORT = "localhost", 8770
BASE_URL = f"http://{HOST}:{PORT}/"

N_SERVICE_A_CALLS = 12
N_SERVICE_B_CALLS = 4
STAGGER_S = 0.05  # asegura que A ya tomo sus lugares en el pool antes de que llegue B


def set_service_a_behavior(state: str):
    urllib.request.urlopen(f"{BASE_URL}admin/service-a?state={state}", timeout=2).read()


def call_service_a():
    with urllib.request.urlopen(f"{BASE_URL}service-a", timeout=3.0) as response:
        return response.read().decode()


def call_service_b():
    with urllib.request.urlopen(f"{BASE_URL}service-b", timeout=3.0) as response:
        return response.read().decode()


def worker(bulkhead: Bulkhead, service_name: str, call_fn, results: list, lock: threading.Lock):
    try:
        bulkhead.call(call_fn)
        outcome = "ok"
    except BulkheadFullError:
        outcome = "rechazada (bulkhead lleno)"
    except (urllib.error.URLError, TimeoutError):
        outcome = "error de red"
    with lock:
        results.append({"service": service_name, "outcome": outcome})


def run_burst(bulkhead_a: Bulkhead, bulkhead_b: Bulkhead) -> list:
    results = []
    lock = threading.Lock()

    a_threads = [
        threading.Thread(target=worker, args=(bulkhead_a, "service_a", call_service_a, results, lock))
        for _ in range(N_SERVICE_A_CALLS)
    ]
    b_threads = [
        threading.Thread(target=worker, args=(bulkhead_b, "service_b", call_service_b, results, lock))
        for _ in range(N_SERVICE_B_CALLS)
    ]

    for t in a_threads:
        t.start()
    time.sleep(STAGGER_S)
    for t in b_threads:
        t.start()

    for t in a_threads + b_threads:
        t.join()

    return results


def summarize(results: list):
    for service in ("service_a", "service_b"):
        subset = [r for r in results if r["service"] == service]
        ok = sum(1 for r in subset if r["outcome"] == "ok")
        rejected = sum(1 for r in subset if "bulkhead" in r["outcome"])
        print(f"  {service}: {len(subset)} llamadas -> {ok} exitosas, {rejected} rechazadas por bulkhead lleno")
    print()


def main():
    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)

    set_service_a_behavior("slow")

    print("Escenario 1: SIN bulkhead — service_a y service_b comparten un pool de 4")
    shared_pool = Bulkhead("pool_compartido", max_concurrent_calls=4)
    results = run_burst(bulkhead_a=shared_pool, bulkhead_b=shared_pool)
    summarize(results)
    print("  service_b esta perfectamente sano y aun asi sus llamadas se rechazan:")
    print("  el pool compartido ya estaba lleno de llamadas lentas a service_a.\n")

    print("Escenario 2: CON bulkhead — cada servicio tiene su propio pool aislado")
    bulkhead_a = Bulkhead("pool_service_a", max_concurrent_calls=2)
    bulkhead_b = Bulkhead("pool_service_b", max_concurrent_calls=4)
    results = run_burst(bulkhead_a=bulkhead_a, bulkhead_b=bulkhead_b)
    summarize(results)
    print("  service_a sigue tan lento como antes y absorbe sus propios rechazos,")
    print("  pero service_b ahora tiene el 100% de exito: su pool nunca se entero")
    print("  de que service_a estaba degradado.")

    server.shutdown()


if __name__ == "__main__":
    main()
