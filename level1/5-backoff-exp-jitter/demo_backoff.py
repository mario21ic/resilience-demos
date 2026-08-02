"""Demo del patron de resiliencia: Backoff exponencial.

El backoff exponencial hace crecer la espera entre reintentos
(base * factor^intento) en vez de reintentar a ritmo constante, dando
tiempo real a que una dependencia sobrecargada se recupere. Pero el
backoff exponencial "puro" (sin aleatoriedad) tiene un problema: si
muchos clientes fallan al mismo tiempo (por ejemplo, un servicio se
reinicia y tumba a todas las conexiones activas), todos calculan
exactamente la misma espera y todos vuelven a golpear al servicio en
el mismo instante -> "thundering herd" / retry storm sincronizado.

Este demo muestra:
  1) Como crece la espera intento a intento para cada estrategia.
  2) Que pasa cuando 24 clientes fallan a la vez y reintentan: sin
     jitter llegan todos juntos; con jitter se dispersan en el tiempo.
"""
import random

from backoff import decorrelated_jitter, equal_jitter, exponential_delay, full_jitter

BASE = 0.5
FACTOR = 2.0
MAX_DELAY = 30.0
MAX_ATTEMPTS = 8
N_CLIENTS = 24
BUCKET_WIDTH = 0.2  # segundos, para el histograma


def print_growth_table():
    print("Crecimiento del delay por intento (segundos)")
    print(f"{'intento':>7} | {'sin jitter':>10} | {'full jitter (rango)':>20} | {'equal jitter (rango)':>20}")
    print("-" * 68)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        cap = exponential_delay(attempt, BASE, FACTOR, MAX_DELAY)
        full_range = f"[0.00, {cap:.2f}]"
        equal_range = f"[{cap / 2:.2f}, {cap:.2f}]"
        print(f"{attempt:>7} | {cap:>10.2f} | {full_range:>20} | {equal_range:>20}")
    print()
    print("El backoff sin jitter siempre da el MISMO numero para todos los")
    print("clientes en el mismo intento; ahi esta el problema que resuelve el jitter.\n")


def ascii_histogram(delays: list[float], title: str):
    print(title)
    max_delay = max(delays) if delays else 0.0
    n_buckets = max(1, int(max_delay / BUCKET_WIDTH) + 1)
    buckets = [0] * n_buckets

    for d in delays:
        idx = min(n_buckets - 1, int(d / BUCKET_WIDTH))
        buckets[idx] += 1

    for i, count in enumerate(buckets):
        start = i * BUCKET_WIDTH
        end = start + BUCKET_WIDTH
        bar = "#" * count
        print(f"  {start:5.2f}-{end:5.2f}s | {bar} ({count})")
    print()


def simulate_no_jitter():
    """Todos los clientes fallan a la vez; sin jitter, todos reintentan igual."""
    return [exponential_delay(1, BASE, FACTOR, MAX_DELAY) for _ in range(N_CLIENTS)]


def simulate_full_jitter():
    return [full_jitter(1, BASE, FACTOR, MAX_DELAY) for _ in range(N_CLIENTS)]


def simulate_decorrelated_jitter():
    delays = []
    for _ in range(N_CLIENTS):
        # primer intento: no hay "prev_delay" todavia, se usa BASE como semilla
        delays.append(decorrelated_jitter(prev_delay=BASE, base=BASE, max_delay=MAX_DELAY))
    return delays


def main():
    random.seed(7)  # salida reproducible para el demo

    print_growth_table()

    print(f"Simulacion: {N_CLIENTS} clientes fallan al mismo tiempo (t=0) y")
    print("calculan su proximo reintento (intento #1) con cada estrategia.\n")

    ascii_histogram(simulate_no_jitter(), "Sin jitter (backoff exponencial puro) -> thundering herd:")
    ascii_histogram(simulate_full_jitter(), "Con full jitter -> reintentos dispersos en el tiempo:")
    ascii_histogram(simulate_decorrelated_jitter(), "Con decorrelated jitter -> dispersos y con piso minimo (base):")

    print("Conclusion: el histograma 'sin jitter' concentra los 24 reintentos")
    print("en un unico bucket (misma espera para todos). Con jitter, la carga")
    print("se reparte en varios buckets, reduciendo el pico de requests")
    print("simultaneos contra el servicio que se esta recuperando.")


if __name__ == "__main__":
    main()
