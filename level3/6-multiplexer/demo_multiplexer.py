"""Demo: Multiplexing + connection pooling — HTTP/2 y gRPC.

Abrir una conexion TCP (y su handshake TLS) cuesta tiempo real, pagado
UNA VEZ por conexion. HTTP/1.1 sin keep-alive paga ese costo en cada
request; con keep-alive (pooling), lo paga una vez y reusa la conexion
para muchos requests; HTTP/2 va un paso mas alla y permite MUCHOS
requests concurrentes (streams) sobre esa misma conexion, sin que se
bloqueen entre si.

Esto no es solo una optimizacion de latencia: reducir el costo de
abrir una conexion es lo que hace barato el "hedging" (mandar el mismo
request a un backup en paralelo y quedarse con el que responda
primero, ver el paper "The Tail at Scale" de Google) — sin pooling,
cada hedge pagaria su propio handshake completo.

  Parte 1 — Costo real medido: request nuevo por conexion vs conexion
            reusada (keep-alive).
  Parte 2 — Concurrencia: un pool limitado de conexiones HTTP/1.1 vs
            multiplexado (muchos streams concurrentes sobre una sola
            conexion, como HTTP/2 y gRPC).
  Parte 3 — Hedging barato: mismo hedge, con la conexion al backup
            fria (recien abierta) vs caliente (ya pooled).
  Parte 4 — La sintesis: en un router de proveedores/modelos, el
            "multiplexer" es pool + load balancing + circuit breaker +
            failover empaquetados detras de un solo `.request()`.
"""
import http.client
import random
import threading
import time
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from multiplexer import Multiplexer, Provider
from server import start_server

HOST = "localhost"


# --- Parte 1: costo de conexion, medido de verdad --------------------------


def demo_connection_cost():
    print("=" * 70)
    print("Parte 1: costo de conexion — nueva conexion por request vs reusada")
    print("=" * 70)

    port = 8776
    server = start_server(HOST, port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)

    n_requests = 20
    print(f"{n_requests} requests, cada uno con 10ms de trabajo real en el servidor.")
    print("El servidor simula un handshake de 150ms por CONEXION NUEVA (no por request).\n")

    start = time.monotonic()
    for _ in range(n_requests):
        conn = http.client.HTTPConnection(HOST, port)
        conn.request("GET", "/work?duration=0.01")
        conn.getresponse().read()
        conn.close()
    no_pool_time = time.monotonic() - start

    start = time.monotonic()
    conn = http.client.HTTPConnection(HOST, port)
    for _ in range(n_requests):
        conn.request("GET", "/work?duration=0.01")
        conn.getresponse().read()
    conn.close()
    pool_time = time.monotonic() - start

    print(f"  sin pooling (conexion nueva cada vez): {no_pool_time:.2f}s")
    print(f"  con pooling (una conexion reusada):    {pool_time:.2f}s")
    print(f"  -> {no_pool_time / pool_time:.1f}x mas lento sin pooling, pagando el mismo")
    print(f"     handshake {n_requests} veces en vez de una sola.\n")

    server.shutdown()


# --- Parte 2: concurrencia — pool limitado vs multiplexado -----------------


def simulate_concurrent_slots(request_durations, n_slots) -> float:
    """`n_slots` requests pueden correr en paralelo real; el resto
    espera a que se libere un slot. Devuelve el tiempo total (makespan).
    """
    free_at = [0.0] * n_slots
    for duration in request_durations:
        slot = min(range(n_slots), key=lambda i: free_at[i])
        free_at[slot] += duration
    return max(free_at)


def demo_concurrency():
    print("=" * 70)
    print("Parte 2: concurrencia — pool limitado (HTTP/1.1) vs multiplexado (HTTP/2)")
    print("=" * 70)
    print("20 requests concurrentes, duracion variable (30-70ms cada uno).\n")

    rng = random.Random(9)
    durations = [rng.uniform(0.03, 0.07) for _ in range(20)]

    sequential = simulate_concurrent_slots(durations, n_slots=1)
    pooled = simulate_concurrent_slots(durations, n_slots=6)
    multiplexed = simulate_concurrent_slots(durations, n_slots=100)

    print(f"  1 sola conexion, sin concurrencia:         {sequential:.2f}s")
    print(f"  pool de 6 conexiones HTTP/1.1:              {pooled:.2f}s")
    print(f"  1 conexion HTTP/2 (streams multiplexados): {multiplexed:.2f}s")
    print(f"\n  con pool de 6, los requests de mas tienen que esperar turno de conexion;")
    print(f"  con multiplexado, los 20 corren en paralelo sobre UNA sola conexion, porque")
    print(f"  el limite (cientos de streams) esta muy por encima de la demanda real.\n")


# --- Parte 3: hedging barato con conexion caliente --------------------------


def call(conn, path):
    conn.request("GET", path)
    conn.getresponse().read()


def demo_hedging():
    print("=" * 70)
    print("Parte 3: hedging — conexion fria vs conexion caliente (pooled)")
    print("=" * 70)

    primary_port, secondary_port = 8777, 8778
    primary_server = start_server(HOST, primary_port)
    secondary_server = start_server(HOST, secondary_port)
    threading.Thread(target=primary_server.serve_forever, daemon=True).start()
    threading.Thread(target=secondary_server.serve_forever, daemon=True).start()
    time.sleep(0.2)

    primary_work, secondary_work, hedge_delay = 0.30, 0.05, 0.05
    print("Este request en particular es lento en el primario (300ms de cola/trabajo).")
    print(f"Tras {hedge_delay * 1000:.0f}ms sin respuesta, se dispara un hedge al secundario")
    print(f"(que responde en {secondary_work * 1000:.0f}ms una vez conectado).\n")

    # hedge FRIO: la conexion al secundario recien se abre al disparar el hedge
    primary_conn = http.client.HTTPConnection(HOST, primary_port)
    primary_conn.connect()
    time.sleep(0.3)  # la conexion principal ya esta "de siempre" establecida
    pool = ThreadPoolExecutor(max_workers=2)
    start = time.monotonic()
    primary_future = pool.submit(call, primary_conn, f"/work?duration={primary_work}")
    done, _ = wait([primary_future], timeout=hedge_delay)
    if not done:
        cold_conn = http.client.HTTPConnection(HOST, secondary_port)  # SIN pool
        hedge_future = pool.submit(call, cold_conn, f"/work?duration={secondary_work}")
        wait([primary_future, hedge_future], return_when=FIRST_COMPLETED)
    cold_elapsed = time.monotonic() - start
    pool.shutdown(wait=False)

    time.sleep(1.0)

    # hedge CALIENTE: la conexion al secundario ya estaba pooled de antes
    primary_conn = http.client.HTTPConnection(HOST, primary_port)
    primary_conn.connect()
    warm_conn = http.client.HTTPConnection(HOST, secondary_port)
    warm_conn.connect()
    time.sleep(0.3)  # ambas conexiones ya estaban calientes de trafico anterior
    pool = ThreadPoolExecutor(max_workers=2)
    start = time.monotonic()
    primary_future = pool.submit(call, primary_conn, f"/work?duration={primary_work}")
    done, _ = wait([primary_future], timeout=hedge_delay)
    if not done:
        hedge_future = pool.submit(call, warm_conn, f"/work?duration={secondary_work}")
        wait([primary_future, hedge_future], return_when=FIRST_COMPLETED)
    warm_elapsed = time.monotonic() - start
    pool.shutdown(wait=False)

    print(f"  hedge con conexion FRIA (pool nuevo):    {cold_elapsed:.2f}s")
    print(f"  hedge con conexion CALIENTE (ya pooled): {warm_elapsed:.2f}s")
    print(f"\n  ambos ganan al primario lento ({primary_work:.2f}s), pero el hedge frio apenas")
    print(f"  le saca ventaja: gasta la mayor parte de su presupuesto en el handshake que")
    print(f"  el caliente ya no tiene que pagar.\n")

    primary_server.shutdown()
    secondary_server.shutdown()


# --- Parte 4: el multiplexer como sintesis ----------------------------------


def demo_multiplexer_synthesis():
    print("=" * 70)
    print("Parte 4: el 'multiplexer' es pool + LB + circuit breaker + failover")
    print("=" * 70)

    port_a, port_b = 8779, 8780
    server_a = start_server(HOST, port_a)
    server_b = start_server(HOST, port_b)
    threading.Thread(target=server_a.serve_forever, daemon=True).start()
    threading.Thread(target=server_b.serve_forever, daemon=True).start()
    time.sleep(0.3)

    provider_a = Provider("proveedor-A", HOST, port_a)
    provider_b = Provider("proveedor-B", HOST, port_b)
    mux = Multiplexer([provider_a, provider_b])

    def run(path="/work?duration=0.01"):
        served_by, _, attempts = mux.request(path)
        print(f"  {attempts} -> servido por {served_by}")

    print("\nFase 1: ambos proveedores sanos, siempre se prefiere A")
    for _ in range(2):
        run()

    print("\nFase 2: A empieza a fallar — failover automatico y transparente a B")
    urllib.request.urlopen(f"http://{HOST}:{port_a}/admin/behavior?state=error").read()
    for _ in range(5):
        run()
    print("  (tras 3 fallas consecutivas, el circuito de A se abre: ya ni se lo intenta)")

    print("\nFase 3: A se recupera")
    urllib.request.urlopen(f"http://{HOST}:{port_a}/admin/behavior?state=healthy").read()
    time.sleep(1.1)  # supera el reset_timeout del circuit breaker
    for _ in range(2):
        run()

    print("\n  Todo esto ocurrio detras de un solo `mux.request(...)` — quien llama nunca")
    print("  supo que hubo fallas, reintentos, ni cambios de proveedor.")

    server_a.shutdown()
    server_b.shutdown()


def main():
    demo_connection_cost()
    demo_concurrency()
    demo_hedging()
    demo_multiplexer_synthesis()


if __name__ == "__main__":
    main()
