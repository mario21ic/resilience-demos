"""SLO + error budgets: el marco que decide cuanta resiliencia
comprar.

Un SLO (Service Level Objective) es un objetivo de confiabilidad
("99.9% de los requests exitosos en una ventana de 30 dias"). Su
complemento es el **error budget**: la cantidad de falla que el SLO
permite, expresada como una cantidad CONCRETA y GASTABLE — minutos de
downtime, o requests fallidos — no solo un porcentaje abstracto.

Convertir la confiabilidad en un presupuesto gastable habilita
decisiones explicitas: si queda presupuesto, tiene sentido asumir mas
riesgo (desplegar mas seguido, experimentar); si el presupuesto ya se
gasto, toca frenar cambios riesgosos y priorizar estabilidad. El SLO
no es un piso que hay que superar siempre — es un objetivo que, una
vez cumplido, libera margen para otras prioridades.
"""


def allowed_downtime_minutes(slo: float, period_days: int) -> float:
    period_minutes = period_days * 24 * 60
    return period_minutes * (1 - slo)


def error_budget_requests(slo: float, requests_per_day: float, period_days: int) -> float:
    total_requests = requests_per_day * period_days
    return total_requests * (1 - slo)


def time_to_exhaust_days(burn_rate: float, period_days: int) -> float:
    """Si el presupuesto se esta gastando a `burn_rate` veces el ritmo
    sostenible (1.0 = exactamente al ritmo que agota el presupuesto
    justo al final del periodo), devuelve en cuantos dias se agota."""
    if burn_rate <= 0:
        return float("inf")
    return period_days / burn_rate
