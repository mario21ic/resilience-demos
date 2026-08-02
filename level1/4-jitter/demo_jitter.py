"""Demo del patron de resiliencia: Jitter (variantes de AWS).

El backoff exponencial (ver 3-backoff-exp) define un TOPE de espera
que crece con el numero de intento, pero por si solo es determinista:
todos los clientes que fallan al mismo tiempo calculan exactamente el
mismo numero y reintentan juntos ("thundering herd"). El jitter le
agrega aleatoriedad a ese calculo para romper esa sincronizacion.

Este demo compara full jitter, equal jitter y decorrelated jitter en
dos niveles:

  1) La FORMA de la distribucion que produce cada una para un mismo
     intento (rango, promedio, histograma).
  2) El efecto real en una simulacion de recuperacion: muchos clientes
     reintentando contra un servidor de capacidad limitada, midiendo
     tiempo total y numero de llamadas hasta que todos tienen exito.
"""
import random
import statistics
from collections import defaultdict

from jitter import decorrelated_jitter, equal_jitter, exponential_cap, full_jitter

BASE = 0.5
FACTOR = 2.0
MAX_DELAY = 30.0
SAMPLE_SIZE = 5000
BUCKET_WIDTH = 0.5


# --- Parte 1: forma de la distribucion -----------------------------------


def sample_stats(name: str, samples: list[float]):
    print(f"{name}")
    print(
        f"  n={len(samples)}  min={min(samples):.2f}s  max={max(samples):.2f}s  "
        f"media={statistics.mean(samples):.2f}s  stdev={statistics.stdev(samples):.2f}s"
    )


def ascii_histogram(samples: list[float], max_value: float):
    n_buckets = int(max_value / BUCKET_WIDTH) + 1
    buckets = [0] * n_buckets
    for s in samples:
        idx = min(n_buckets - 1, int(s / BUCKET_WIDTH))
        buckets[idx] += 1
    peak = max(buckets) or 1
    scale = peak / 40 if peak > 40 else 1
    for i, count in enumerate(buckets):
        start = i * BUCKET_WIDTH
        bar_len = int(count / scale)
        print(f"  {start:5.1f}s | {'#' * bar_len} ({count})")


def compare_distributions():
    attempt = 5  # cap = 0.5 * 2^4 = 8s
    prev_delay = exponential_cap(attempt - 1, BASE, FACTOR, MAX_DELAY)  # 4s
    cap = exponential_cap(attempt, BASE, FACTOR, MAX_DELAY)  # 8s

    print(f"Distribucion de cada variante en el intento #{attempt} (cap determinista = {cap:.2f}s)")
    print(f"({SAMPLE_SIZE} muestras por variante)\n")

    full_samples = [full_jitter(attempt, BASE, FACTOR, MAX_DELAY) for _ in range(SAMPLE_SIZE)]
    equal_samples = [equal_jitter(attempt, BASE, FACTOR, MAX_DELAY) for _ in range(SAMPLE_SIZE)]
    decorr_samples = [decorrelated_jitter(prev_delay, BASE, MAX_DELAY) for _ in range(SAMPLE_SIZE)]

    sample_stats("Full jitter          [0, cap]", full_samples)
    sample_stats("Equal jitter         [cap/2, cap]", equal_samples)
    sample_stats("Decorrelated jitter  [base, prev*3]", decorr_samples)

    print("\nFull jitter:")
    ascii_histogram(full_samples, cap)
    print("\nEqual jitter:")
    ascii_histogram(equal_samples, cap)
    print("\nDecorrelated jitter:")
    ascii_histogram(decorr_samples, prev_delay * 3)
    print()


# --- Parte 2: simulacion de recuperacion con capacidad limitada ----------

WINDOW = 0.5      # ancho de la ventana de tiempo del servidor, en segundos
CAPACITY = 8      # requests que el servidor puede aceptar por ventana
N_CLIENTS = 100
MAX_ATTEMPTS = 20


def compute_delay(strategy: str, attempt: int, prev_delay: float) -> float:
    if strategy == "sin_jitter":
        return exponential_cap(attempt, BASE, FACTOR, MAX_DELAY)
    if strategy == "full_jitter":
        return full_jitter(attempt, BASE, FACTOR, MAX_DELAY)
    if strategy == "equal_jitter":
        return equal_jitter(attempt, BASE, FACTOR, MAX_DELAY)
    if strategy == "decorrelated_jitter":
        return decorrelated_jitter(prev_delay, BASE, MAX_DELAY)
    raise ValueError(strategy)


def run_recovery_simulation(strategy: str) -> tuple[float, int, int]:
    """Todos los clientes fallan a t=0 y reintentan segun `strategy` hasta
    tener exito. El servidor solo acepta `CAPACITY` requests por ventana
    de `WINDOW` segundos (capacidad acumulada por ventana, no por pasada).

    Retorna (tiempo_total, llamadas_totales, clientes_abandonados).
    """
    pending = [{"attempt": 0, "prev_delay": BASE, "next_try": 0.0} for _ in range(N_CLIENTS)]
    capacity_used: dict[int, int] = defaultdict(int)
    total_calls = 0
    abandoned = 0
    max_time = 0.0

    while pending:
        by_window: dict[int, list[dict]] = defaultdict(list)
        for client in pending:
            by_window[int(client["next_try"] / WINDOW)].append(client)

        still_pending = []
        for window_idx, clients_in_window in by_window.items():
            total_calls += len(clients_in_window)
            window_end = (window_idx + 1) * WINDOW
            max_time = max(max_time, window_end)

            available = CAPACITY - capacity_used[window_idx]
            random.shuffle(clients_in_window)
            succeed_count = max(0, min(len(clients_in_window), available))
            capacity_used[window_idx] += succeed_count

            for client in clients_in_window[succeed_count:]:
                client["attempt"] += 1
                if client["attempt"] > MAX_ATTEMPTS:
                    abandoned += 1
                    continue
                delay = compute_delay(strategy, client["attempt"], client["prev_delay"])
                client["next_try"] = window_end + delay
                client["prev_delay"] = delay
                still_pending.append(client)

        pending = still_pending

    return max_time, total_calls, abandoned


def compare_recovery():
    print(f"Simulacion: {N_CLIENTS} clientes fallan a la vez contra un servidor")
    print(f"que solo acepta {CAPACITY} requests por ventana de {WINDOW}s.\n")
    print(f"{'estrategia':>22} | {'tiempo total':>12} | {'llamadas totales':>17} | {'abandonados':>11}")
    print("-" * 72)
    for strategy in ("sin_jitter", "full_jitter", "equal_jitter", "decorrelated_jitter"):
        total_time, total_calls, abandoned = run_recovery_simulation(strategy)
        print(f"{strategy:>22} | {total_time:>11.2f}s | {total_calls:>17} | {abandoned:>11}")
    print()
    print("Sin jitter, todos los que fallan comparten el mismo numero de intento y")
    print("por lo tanto la misma espera: siguen colisionando en bloque contra la")
    print("capacidad del servidor en cada ronda. El jitter dispersa esas colisiones,")
    print("bajando el tiempo total y, en varios casos, tambien las llamadas extra.")


def main():
    random.seed(42)
    compare_distributions()
    compare_recovery()


if __name__ == "__main__":
    main()
