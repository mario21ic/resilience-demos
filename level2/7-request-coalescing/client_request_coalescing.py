"""Demo del patron de resiliencia: Request coalescing / single-flight.

Cuando una clave popular expira de un cache (o nunca estuvo), es comun
que muchos requests concurrentes intenten recalcularla/refetchearla al
mismo tiempo — un "cache stampede" o "dog-piling". Sin coordinacion,
cada uno de esos requests dispara su propia llamada identica al
backend, multiplicando por N un trabajo que solo hacia falta hacer una
vez.

El request coalescing (single-flight) resuelve esto del lado del
CLIENTE (o de una capa intermedia, como un cache-aside layer o un API
gateway): el primer caller para una clave ejecuta la llamada real; el
resto de los callers concurrentes para esa MISMA clave esperan y
reciben el mismo resultado, sin generar ninguna llamada adicional.

Este demo compara, contra el mismo backend "caro" (0.3s por llamada
real, que cuenta cada invocacion en un contador global):

  Parte 1: N requests concurrentes por la MISMA clave, sin coalescing.
  Parte 2: los mismos N requests, ahora con un SingleFlightGroup.
  Parte 3: coalescing con DOS claves distintas mezcladas, mostrando
           que la deduplicacion es por clave, no global.
"""
import json
import threading
import time
import urllib.request

from server import start_server
from single_flight import SingleFlightGroup

HOST, PORT = "localhost", 8774
BASE_URL = f"http://{HOST}:{PORT}/"

N_CONCURRENT = 20


def reset_server():
    urllib.request.urlopen(f"{BASE_URL}reset", timeout=2).read()


def get_call_count() -> int:
    with urllib.request.urlopen(f"{BASE_URL}debug/call_count", timeout=2) as response:
        return json.loads(response.read())["call_count"]


def fetch(key: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}compute?key={key}", timeout=5) as response:
        return json.loads(response.read())


def worker_without_coalescing(key: str, results: list, lock: threading.Lock):
    result = fetch(key)
    with lock:
        results.append(result)


def worker_with_coalescing(group: SingleFlightGroup, key: str, results: list, lock: threading.Lock):
    result = group.do(key, fetch, key)
    with lock:
        results.append(result)


def demo_without_coalescing():
    print(f"Parte 1: {N_CONCURRENT} requests concurrentes por la MISMA clave, SIN coalescing\n")
    reset_server()

    results = []
    lock = threading.Lock()
    threads = [
        threading.Thread(target=worker_without_coalescing, args=("popular_key", results, lock))
        for _ in range(N_CONCURRENT)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"  llamadas reales al backend: {get_call_count()} (una por cada request concurrente)\n")


def demo_with_coalescing():
    print(f"Parte 2: los mismos {N_CONCURRENT} requests concurrentes, CON single-flight\n")
    reset_server()
    group = SingleFlightGroup()

    results = []
    lock = threading.Lock()
    threads = [
        threading.Thread(target=worker_with_coalescing, args=(group, "popular_key", results, lock))
        for _ in range(N_CONCURRENT)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    distinct_results = {result["computed_at_call"] for result in results}
    print(f"  llamadas reales al backend: {get_call_count()} (una sola, compartida por los {N_CONCURRENT})")
    print(f"  valores distintos de 'computed_at_call' recibidos: {distinct_results} (todos comparten la misma respuesta)\n")


def demo_mixed_keys():
    print("Parte 3: coalescing con DOS claves distintas mezcladas (15 + 5 concurrentes)\n")
    reset_server()
    group = SingleFlightGroup()

    results = []
    lock = threading.Lock()
    threads = [
        threading.Thread(target=worker_with_coalescing, args=(group, "key_a", results, lock)) for _ in range(15)
    ]
    threads += [
        threading.Thread(target=worker_with_coalescing, args=(group, "key_b", results, lock)) for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"  llamadas reales al backend: {get_call_count()} (una por CADA clave distinta, no una sola global)")


def main():
    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)

    demo_without_coalescing()
    demo_with_coalescing()
    demo_mixed_keys()

    server.shutdown()


if __name__ == "__main__":
    main()
