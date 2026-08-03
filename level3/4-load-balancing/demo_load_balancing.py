"""Demo: Load balancing — round robin, least-connections, EWMA, P2C
(power of two choices) y consistent hashing con bounded loads.

Cuatro partes, cada una mostrando por que la estrategia mas simple no
alcanza en un escenario concreto, y que gana la siguiente:

  Parte 1 — Round robin vs least-connections: un backend es mas lento
            que los demas (menor capacidad, no una falla). Round
            robin le manda la misma proporcion de trafico igual,
            acumulando una cola creciente; least-connections reacciona
            al atraso y le manda menos.
  Parte 2 — Least-connections vs EWMA: un backend sufre un pico de
            latencia TRANSITORIO sin que su cantidad de conexiones en
            curso se dispare demasiado. Least-connections tarda en
            notarlo (mira conteo, no latencia); EWMA lo detecta apenas
            llegan las primeras respuestas lentas.
  Parte 3 — Random vs P2C vs least-loaded, a escala (100 backends):
            el clasico resultado de "power of two choices" — mirar
            solo 2 backends al azar da casi el mismo balance que
            escanear los 100, con una fraccion del costo.
  Parte 4 — Consistent hashing vs consistent hashing con bounded
            loads: unas pocas claves "calientes" sobrecargan al
            backend que les toca en el anillo; bounded loads acota
            cuanto puede acumular cualquier backend, derivando el
            excedente al siguiente nodo del anillo.
"""
import random

from load_balancers import (
    BoundedLoadConsistentHash,
    ConsistentHashRing,
    EWMABalancer,
    LeastConnectionsBalancer,
    P2CBalancer,
    RoundRobinBalancer,
)

# --- Parte 1: round robin vs least-connections (backend lento) ------------


def simulate_queueing(balancer, backend_speeds, arrivals, ticks):
    """`backend_speeds[i]` = ticks que tarda el backend i en procesar
    UN request. Llega 1 request nuevo por tick durante `arrivals`
    ticks. Devuelve el historial de largo de cola por backend, tick a
    tick.
    """
    n = len(backend_speeds)
    queue_len = [0] * n
    remaining = [0] * n
    history = []

    for t in range(ticks):
        if t < arrivals:
            backend = balancer.pick(queue_len)
            queue_len[backend] += 1
        for i in range(n):
            if remaining[i] == 0 and queue_len[i] > 0:
                remaining[i] = backend_speeds[i]
            if remaining[i] > 0:
                remaining[i] -= 1
                if remaining[i] == 0:
                    queue_len[i] -= 1
        history.append(list(queue_len))

    return history


def makespan(history) -> int:
    for t in range(len(history) - 1, -1, -1):
        if sum(history[t]) > 0:
            return t + 1
    return 0


def demo_round_robin_vs_least_connections():
    print("=" * 70)
    print("Parte 1: Round robin vs Least connections (backend mas lento)")
    print("=" * 70)
    print("3 backends: los dos primeros procesan 1 request/tick, el tercero")
    print("tarda 4 ticks por request (4x mas lento, no esta caido).\n")

    speeds = [1, 1, 4]
    rr_history = simulate_queueing(RoundRobinBalancer(3), speeds, arrivals=60, ticks=150)
    lc_history = simulate_queueing(LeastConnectionsBalancer(random.Random(42)), speeds, arrivals=60, ticks=150)

    print(f"  round robin:      cola maxima del backend lento = {max(h[2] for h in rr_history)}, "
          f"todo procesado en el tick {makespan(rr_history)}")
    print(f"  least-connections: cola maxima del backend lento = {max(h[2] for h in lc_history)}, "
          f"todo procesado en el tick {makespan(lc_history)}")
    print(f"\n  least-connections termina de procesar la misma rafaga un "
          f"{100 * (1 - makespan(lc_history) / makespan(rr_history)):.0f}% mas rapido,")
    print("  simplemente por dejar de mandarle tanto trafico al backend lento.\n")


# --- Parte 2: least-connections vs EWMA (pico de latencia) ----------------


def simulate_latency_aware(balancer, degraded_window, arrival_interval, base_latency, degraded_latency, total_ticks, n_backends=3, degraded_backend=1):
    active_ends = [[] for _ in range(n_backends)]
    routed_to_degraded = 0
    total_during_window = 0
    latencies_during_window = []

    t = 0
    while t < total_ticks:
        for i in range(n_backends):
            active_ends[i] = [e for e in active_ends[i] if e > t]
        counts = [len(active_ends[i]) for i in range(n_backends)]

        backend = balancer.pick(counts)
        is_degraded_now = degraded_window[0] <= t < degraded_window[1]
        duration = degraded_latency if (backend == degraded_backend and is_degraded_now) else base_latency
        active_ends[backend].append(t + duration)

        if hasattr(balancer, "record"):
            balancer.record(backend, duration)

        if is_degraded_now:
            total_during_window += 1
            latencies_during_window.append(duration)
            if backend == degraded_backend:
                routed_to_degraded += 1

        t += arrival_interval

    avg_latency = sum(latencies_during_window) / len(latencies_during_window) if latencies_during_window else 0.0
    return routed_to_degraded, total_during_window, avg_latency


def demo_least_connections_vs_ewma():
    print("=" * 70)
    print("Parte 2: Least connections vs EWMA (pico de latencia transitorio)")
    print("=" * 70)
    print("3 backends normalmente igual de rapidos (3 ticks/request). El backend")
    print("1 sufre un pico de latencia (24 ticks/request) durante una ventana,")
    print("sin que su cantidad de conexiones en curso llegue a dispararse mucho.\n")

    base, degraded = 3, 24
    window = (20, 50)

    lc = LeastConnectionsBalancer(random.Random(7))
    lc_routed, lc_total, lc_avg = simulate_latency_aware(lc, window, 2, base, degraded, 90)

    ewma = EWMABalancer(3, alpha=0.3, initial_latency=base, rng=random.Random(7))
    ewma_routed, ewma_total, ewma_avg = simulate_latency_aware(ewma, window, 2, base, degraded, 90)

    print(f"  least-connections: {lc_routed}/{lc_total} requests durante el pico fueron al backend "
          f"degradado -> latencia promedio {lc_avg:.1f} (vs baseline {base})")
    print(f"  EWMA:              {ewma_routed}/{ewma_total} requests durante el pico fueron al backend "
          f"degradado -> latencia promedio {ewma_avg:.1f} (vs baseline {base})")
    print("\n  least-connections solo reacciona una vez que el atraso se nota en la cola;")
    print("  EWMA reacciona en cuanto llega la PRIMERA respuesta lenta, porque mide")
    print("  directamente lo que le importa al cliente: la latencia.\n")


# --- Parte 3: random vs P2C vs least-loaded, a escala ----------------------


def simulate_bins(n_backends, n_requests, strategy, rng):
    loads = [0] * n_backends
    inspected = 0
    for _ in range(n_requests):
        if strategy == "random":
            i = rng.randrange(n_backends)
            inspected += 1
        elif strategy == "p2c":
            i, j = rng.sample(range(n_backends), 2)
            inspected += 2
            i = i if loads[i] <= loads[j] else j
        else:  # least_loaded
            i = min(range(n_backends), key=lambda k: loads[k])
            inspected += n_backends
        loads[i] += 1
    return loads, inspected


def demo_p2c():
    print("=" * 70)
    print("Parte 3: Random vs P2C vs least-loaded, a escala (100 backends)")
    print("=" * 70)
    print("1000 requests, 100 backends (promedio ideal: 10 requests c/u).\n")

    n_backends, n_requests = 100, 1000
    header = f"{'estrategia':>14} | {'carga maxima':>12} | {'carga minima':>12} | {'backends inspeccionados/decision':>34}"
    print(header)
    print("-" * len(header))
    for strategy, per_decision in (("random", 1), ("p2c", 2), ("least_loaded", n_backends)):
        loads, _ = simulate_bins(n_backends, n_requests, strategy, random.Random(3))
        print(f"{strategy:>14} | {max(loads):>12} | {min(loads):>12} | {per_decision:>34}")
    print()
    print("P2C, mirando solo 2 backends al azar por decision, logra un balance casi")
    print("tan bueno como escanear los 100 — con 50x menos trabajo por decision.\n")


# --- Parte 4: consistent hashing vs bounded loads --------------------------


def simulate_hot_keys(n_backends, total_requests, hot_keys, hot_key_weight, rng):
    backends = [f"backend-{i}" for i in range(n_backends)]
    plain = ConsistentHashRing(backends)
    bounded = BoundedLoadConsistentHash(backends, balance_factor=1.25)

    plain_load = {b: 0 for b in backends}
    served = 0
    for i in range(total_requests):
        key = rng.choice(hot_keys) if rng.random() < hot_key_weight else f"key-{i}"
        plain_load[plain.get(key)] += 1
        bounded.assign(key, served)
        served += 1

    return plain_load, bounded.load


def demo_consistent_hashing():
    print("=" * 70)
    print("Parte 4: Consistent hashing vs consistent hashing con bounded loads")
    print("=" * 70)
    n_backends, total_requests = 10, 20000
    hot_keys = ["hot-1", "hot-2", "hot-3"]
    avg = total_requests / n_backends
    print(f"{n_backends} backends, {total_requests} requests. 3 claves 'calientes' concentran")
    print("el 50% de todo el trafico entre ellas; el resto son claves unicas.")
    print(f"Promedio ideal por backend: {avg:.0f}\n")

    plain_load, bounded_load = simulate_hot_keys(n_backends, total_requests, hot_keys, 0.5, random.Random(5))

    print(f"  consistent hashing plano:        carga maxima = {max(plain_load.values())} "
          f"({max(plain_load.values()) / avg:.1f}x el promedio)")
    print(f"  consistent hashing + bounded:     carga maxima = {max(bounded_load.values())} "
          f"({max(bounded_load.values()) / avg:.1f}x el promedio)")
    print("\n  el hashing plano concentra 2 de las 3 claves calientes en el mismo backend")
    print("  (asi es el hashing: no sabe cuales claves van a ser populares). Bounded")
    print("  loads detecta que ese backend ya esta al limite y deriva el excedente")
    print("  al siguiente nodo del anillo, sin perder la afinidad para el resto.")


def main():
    demo_round_robin_vs_least_connections()
    demo_least_connections_vs_ewma()
    demo_p2c()
    demo_consistent_hashing()


if __name__ == "__main__":
    main()
