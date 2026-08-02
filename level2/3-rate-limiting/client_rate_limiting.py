"""Demo del patron de resiliencia: Rate limiting.

El [bulkhead](../2-bulkhead) limita cuanta CAPACIDAD DEL CLIENTE puede
consumir una dependencia. El rate limiting resuelve el problema
simetrico del lado del SERVIDOR: cuantos requests por segundo esta
dispuesto a aceptar, sin importar quien los mande — es un limite de
politica que se aplica siempre, no una reaccion a que algo ya haya
fallado.

Este demo tiene dos partes:

  Parte 1: compara tres algoritmos clasicos (fixed window, sliding
           window log, token bucket) contra la MISMA linea de tiempo
           de requests, exponiendo el defecto de borde del fixed
           window: deja pasar el doble del limite nominal si el
           trafico se concentra justo en el limite entre dos
           ventanas.
  Parte 2: un endpoint HTTP real protegido con token bucket, que
           responde `429 Too Many Requests` con el header
           `Retry-After` cuando se supera el limite — el mismo header
           que un cliente con retry + backoff (level1) deberia leer y
           respetar en vez de reintentar a ciegas.
"""
import json
import threading
import time
import urllib.error
import urllib.request

from rate_limiters import FixedWindowLimiter, SlidingWindowLogLimiter, TokenBucketLimiter
from server import start_server

HOST, PORT = "localhost", 8771
BASE_URL = f"http://{HOST}:{PORT}/"


# --- Parte 1: comparacion de algoritmos -----------------------------------


def build_timeline():
    """20 requests distribuidos en tres fases, todos con el mismo
    limite nominal de 10 req/s como referencia:
      - trafico normal, bien espaciado (5 requests).
      - una rafaga de 10 requests justo ANTES del borde t=1.0s.
      - otra rafaga de 10 requests justo DESPUES del borde t=1.0s.
    Un limitador que solo mira "cuantos requests hubo en la ventana de
    reloj actual" puede dejar pasar las dos rafagas completas, porque
    cada una cae en una ventana distinta.
    """
    events = []
    for t in (0.0, 0.15, 0.30, 0.45, 0.60):
        events.append((t, "trafico normal"))
    for i in range(10):
        events.append((0.90 + i * 0.01, "rafaga previa al borde"))
    for i in range(10):
        events.append((1.01 + i * 0.01, "rafaga posterior al borde"))
    return events


def run_timeline(limiter, events):
    results = {}
    for now, phase in events:
        allowed = limiter.allow_request(now)
        bucket = results.setdefault(phase, [0, 0])
        bucket[0 if allowed else 1] += 1
    return results


def print_algorithm_comparison():
    print("Parte 1: fixed window vs. sliding window log vs. token bucket")
    print("Limite nominal: 10 requests/segundo. Misma linea de tiempo para los tres.\n")

    events = build_timeline()
    limiters = {
        "Fixed window": FixedWindowLimiter(max_requests=10, window_size=1.0),
        "Sliding window log": SlidingWindowLogLimiter(max_requests=10, window_size=1.0),
        "Token bucket": TokenBucketLimiter(rate=10.0, capacity=10.0),
    }

    for name, limiter in limiters.items():
        results = run_timeline(limiter, events)
        total_allowed = sum(allowed for allowed, _ in results.values())
        burst_allowed = (
            results.get("rafaga previa al borde", [0, 0])[0]
            + results.get("rafaga posterior al borde", [0, 0])[0]
        )
        print(f"{name}:")
        for phase, (allowed, denied) in results.items():
            print(f"  {phase:<28} allowed={allowed:>2}  denied={denied:>2}")
        print(
            f"  -> total permitido: {total_allowed}/20 "
            f"(de los cuales {burst_allowed} son parte de la rafaga de 20 alrededor del borde)\n"
        )


# --- Parte 2: endpoint HTTP real con token bucket -------------------------


def call_resource():
    req = urllib.request.Request(f"{BASE_URL}api/resource")
    try:
        with urllib.request.urlopen(req, timeout=2.0) as response:
            return response.status, json.loads(response.read()), None
    except urllib.error.HTTPError as exc:
        retry_after = exc.headers.get("Retry-After")
        return exc.code, json.loads(exc.read()), retry_after


def demo_http_rate_limit():
    print("Parte 2: endpoint HTTP real protegido con token bucket (capacidad=5, tasa=5/s)\n")

    print("Rafaga de 10 requests inmediatos (mas rapido de lo que el balde se recarga):")
    first_retry_after = None
    for i in range(10):
        status, body, retry_after = call_resource()
        marker = "200" if status == 200 else "429"
        print(f"  request {i + 1:>2}: {marker} {body}")
        if status == 429 and first_retry_after is None:
            first_retry_after = float(retry_after)

    print(f"\nEsperando {first_retry_after:.2f}s (el Retry-After sugerido) a que se recarguen tokens...")
    time.sleep(first_retry_after + 0.05)

    print("Reintentando despues de esperar:")
    for i in range(3):
        status, body, _ = call_resource()
        marker = "200" if status == 200 else "429"
        print(f"  request {i + 1:>2}: {marker} {body}")


def main():
    print_algorithm_comparison()

    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)

    demo_http_rate_limit()

    server.shutdown()


if __name__ == "__main__":
    main()
