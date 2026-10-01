"""Observabilidad: RED, USE, trazas distribuidas, histogramas (no
promedios).

  - RED (Rate, Errors, Duration): las tres metricas para cualquier
    cosa que atiende REQUESTS. Son indicadores tardios (lagging):
    solo se mueven una vez que el problema YA esta afectando trafico
    real.
  - USE (Utilization, Saturation, Errors): las tres metricas para
    cualquier RECURSO (CPU, disco, una cola). La saturacion es un
    indicador temprano (leading): un recurso puede estar
    saturandose mucho antes de que eso se traduzca en errores o
    latencia real para los clientes.
  - Trazas distribuidas: seguir un unico request a traves de varios
    servicios para saber DONDE se fue el tiempo, no solo cuanto tardo
    en total.
  - Histogramas, no promedios: un promedio es un solo numero que
    puede esconder una realidad bimodal — la mayoria de los requests
    rapidos, una fraccion real y consistente lenta.
"""


def percentile(sorted_values: list, p: float) -> float:
    idx = min(int(len(sorted_values) * p), len(sorted_values) - 1)
    return sorted_values[idx]


def simulate_saturation_vs_errors(ticks: int, arrival_rate: float, service_rate: float, queue_capacity: float = 100.0):
    """Simula una cola que se llena de a poco. La saturacion (USE)
    crece de forma continua y visible ANTES de que la cola se desborde
    del todo y empiecen a aparecer errores reales (RED).
    """
    queue = 0.0
    history = []
    for t in range(ticks):
        queue = max(0.0, min(queue_capacity, queue + arrival_rate - service_rate))
        saturation = queue / queue_capacity
        error_rate = 1.0 if queue >= queue_capacity else 0.0
        history.append((t, saturation, error_rate))
    return history
