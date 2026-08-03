"""Progressive delivery con auto-rollback por SLO (el modelo de
Flagger / Argo Rollouts): durante un rollout por oleadas, un analizador
automatico mide metricas reales en cada oleada contra los SLOs
definidos, y si se violan, hace ROLLBACK completo — no solo frena,
vuelve el trafico a la version estable — sin que nadie tenga que
reaccionar a mano.

Esto va un paso mas alla del criterio automatico simple de
[1-canary-blue-green-rolling](../1-canary-blue-green-rolling): en vez
de mirar una sola metrica una vez por oleada, mira VARIAS metricas
(error rate Y latencia — cualquiera de las dos puede disparar el
rollback) y exige varios chequeos seguidos fallando antes de actuar,
para no reaccionar a ruido estadistico normal.
"""
import random

ERROR_RATE_SLO = 0.05
LATENCY_SLO_MS = 300.0

STAGES = [10, 25, 50, 75, 100]


def draw_metrics(rng: random.Random, latency_degraded: bool = False, spike_probability: float = 0.0):
    """Genera una muestra de metricas para un chequeo. `latency_degraded`
    simula un problema real y sostenido; `spike_probability` simula
    ruido normal (picos aislados en una version sana).
    """
    error_rate = rng.uniform(0.0, 0.02)

    if latency_degraded:
        p99_latency = rng.uniform(400.0, 600.0)
    elif rng.random() < spike_probability:
        p99_latency = rng.uniform(LATENCY_SLO_MS + 10, LATENCY_SLO_MS + 50)
    else:
        p99_latency = rng.uniform(100.0, 150.0)

    return error_rate, p99_latency


def run_progressive_delivery(
    rng: random.Random,
    metrics_fn,
    checks_per_stage: int,
    required_consecutive_failures: int,
    check_latency: bool = True,
):
    """Avanza oleada por oleada. En cada oleada, corre
    `checks_per_stage` chequeos; si `required_consecutive_failures`
    chequeos SEGUIDOS violan el SLO (de cualquiera de las metricas
    habilitadas), hace rollback completo de inmediato.

    Devuelve ("rolled_back", oleada) o ("fully_promoted", 100).
    """
    for stage_pct in STAGES:
        consecutive_failures = 0
        for _ in range(checks_per_stage):
            error_rate, p99_latency = metrics_fn(rng)
            violates_slo = error_rate > ERROR_RATE_SLO or (check_latency and p99_latency > LATENCY_SLO_MS)
            consecutive_failures = consecutive_failures + 1 if violates_slo else 0
            if consecutive_failures >= required_consecutive_failures:
                return "rolled_back", stage_pct

    return "fully_promoted", STAGES[-1]
