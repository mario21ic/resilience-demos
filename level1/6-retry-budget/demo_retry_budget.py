"""Demo del patron de resiliencia: Retry budget.

El retry de [2-retry](../2-retry) decide, PARA UNA SOLA LLAMADA,
cuantas veces reintentar. Eso no evita el problema a nivel de flota:
si un backend se degrada y TODAS las llamadas empiezan a fallar,
"cada llamada reintenta una vez" igual duplica (o mas) la carga total
contra un servicio que ya esta sufriendo, justo cuando menos lo
necesita.

El retry budget ataca eso desde otro angulo: un limite COMPARTIDO a
cuantos reintentos se permiten en total (por cliente, por servicio, o
por pool de conexiones), sin importar cuantos reintentos autorizaria
la logica de cada request individual. Cuando el budget se agota, las
llamadas fallidas devuelven el error inmediatamente en vez de
reintentar — protegiendo al backend a costa de exponer la falla un
poco antes al llamador.

Este demo simula 500 llamadas en tres fases (sano -> outage ->
recuperacion) y compara, con la MISMA secuencia de exitos/fallas:

  1) Retry sin budget: siempre reintenta una vez si la llamada falla.
  2) Retry con budget: solo reintenta si `RetryBudget.allow_retry()`
     lo autoriza.
"""
import random
from collections import defaultdict

from retry_budget import RetryBudget

PHASES = [
    ("sano", 200, 0.05),          # 5% de fallas transitorias, normal
    ("outage", 100, 0.95),        # el backend esta caido casi del todo
    ("recuperacion", 200, 0.05),  # vuelve a la normalidad
]


def generate_outcomes(seed: int = 7):
    """Precalcula, para cada request, si el intento original y un
    eventual reintento tendrian exito. Usar la MISMA secuencia en
    ambas simulaciones aisla el efecto del budget en si (no es una
    diferencia de suerte aleatoria).
    """
    random.seed(seed)
    outcomes = []
    for phase_name, count, fail_prob in PHASES:
        for _ in range(count):
            original_ok = random.random() >= fail_prob
            retry_ok = random.random() >= fail_prob
            outcomes.append((phase_name, original_ok, retry_ok))
    return outcomes


def new_stats():
    return {"requests": 0, "retries": 0, "denied": 0, "calls": 0, "successes": 0}


def run_without_budget(outcomes):
    stats = defaultdict(new_stats)
    for phase, original_ok, retry_ok in outcomes:
        s = stats[phase]
        s["requests"] += 1
        s["calls"] += 1
        if original_ok:
            s["successes"] += 1
            continue
        s["retries"] += 1
        s["calls"] += 1
        if retry_ok:
            s["successes"] += 1
    return stats


def run_with_budget(outcomes, budget: RetryBudget):
    stats = defaultdict(new_stats)
    tokens_at_end_of_phase = {}
    for phase, original_ok, retry_ok in outcomes:
        s = stats[phase]
        s["requests"] += 1
        s["calls"] += 1
        if original_ok:
            s["successes"] += 1
            budget.on_success()
        elif budget.allow_retry():
            s["retries"] += 1
            s["calls"] += 1
            if retry_ok:
                s["successes"] += 1
                budget.on_success()
        else:
            s["denied"] += 1
        tokens_at_end_of_phase[phase] = budget.tokens
    return stats, tokens_at_end_of_phase


def print_comparison(without_stats, with_stats, tokens_at_end_of_phase):
    header = f"{'fase':>14} | {'requests':>8} | {'retries sin budget':>18} | {'retries con budget':>18} | {'denegados':>9} | {'tokens al final':>15}"
    print(header)
    print("-" * len(header))
    for phase_name, count, _ in PHASES:
        wo = without_stats[phase_name]
        wi = with_stats[phase_name]
        print(
            f"{phase_name:>14} | {wo['requests']:>8} | {wo['retries']:>18} | "
            f"{wi['retries']:>18} | {wi['denied']:>9} | {tokens_at_end_of_phase[phase_name]:>15.1f}"
        )
    print()

    total_calls_wo = sum(s["calls"] for s in without_stats.values())
    total_calls_wi = sum(s["calls"] for s in with_stats.values())
    total_ok_wo = sum(s["successes"] for s in without_stats.values())
    total_ok_wi = sum(s["successes"] for s in with_stats.values())
    total_requests = sum(count for _, count, _ in PHASES)

    print(f"Llamadas totales al backend  sin budget: {total_calls_wo}")
    print(f"Llamadas totales al backend  con budget: {total_calls_wi}")
    reduction = 100 * (1 - total_calls_wi / total_calls_wo)
    print(f"Reduccion de carga con budget: {reduction:.1f}%\n")

    print(f"Tasa de exito global sin budget: {total_ok_wo}/{total_requests} ({100 * total_ok_wo / total_requests:.1f}%)")
    print(f"Tasa de exito global con budget: {total_ok_wi}/{total_requests} ({100 * total_ok_wi / total_requests:.1f}%)")


def main():
    outcomes = generate_outcomes()

    without_stats = run_without_budget(outcomes)
    budget = RetryBudget(max_tokens=10.0, token_ratio=0.1)
    with_stats, tokens_at_end_of_phase = run_with_budget(outcomes, budget)

    print_comparison(without_stats, with_stats, tokens_at_end_of_phase)

    print()
    print("Durante 'outage', casi toda llamada falla: sin budget, eso significa")
    print("casi el doble de trafico contra un backend que ya esta caido. Con")
    print("budget, los tokens se agotan a los pocos reintentos y el resto de las")
    print("fallas se devuelve de inmediato (fail fast) sin sumar mas carga.")
    print("La tasa de exito global casi no cambia, porque esos reintentos")
    print("denegados casi nunca iban a tener exito de todas formas (fail_prob=0.95).")


if __name__ == "__main__":
    main()
