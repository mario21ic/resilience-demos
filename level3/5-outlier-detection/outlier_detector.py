"""Outlier detection / ejection pasiva: en vez de preguntarle
activamente a cada replica "¿estas sana?" (health checks activos, ver
level3/3-health-check), el load balancer observa los resultados REALES
del trafico que ya esta enviando, y saca del pool a la replica que se
comporta peor que sus pares — sin necesidad de un endpoint de health
check dedicado.

Es lo mismo que hace el "outlier detection" de Envoy: pasivo, basado
en trafico real, y pensado como COMPLEMENTO (no sustituto) de los
health checks activos — un health check activo puede tardar en notar
un problema que ya se esta viendo en cada request real.
"""
import statistics
from collections import deque


class ConsecutiveFailureEjector:
    """Eyecta una replica tras `consecutive_failures_threshold` fallas
    SEGUIDAS (una falla aislada no alcanza). La duracion de la
    ejeccion crece con cada vez que la MISMA replica vuelve a fallar
    apenas se la reincorpora (`base_ejection_time * veces_eyectada`,
    igual que Envoy) — evita que una replica que "flapea" entre y
    salga del pool sin parar.
    """

    def __init__(self, consecutive_failures_threshold: int = 5, base_ejection_time: int = 5, max_ejection_time: int = 60):
        self.threshold = consecutive_failures_threshold
        self.base_ejection_time = base_ejection_time
        self.max_ejection_time = max_ejection_time
        self._consecutive_failures: dict = {}
        self._ejected_until: dict = {}
        self._ejection_count: dict = {}

    def is_ejected(self, backend: str, now: int) -> bool:
        return self._ejected_until.get(backend, -1) > now

    def ejected_until(self, backend: str):
        return self._ejected_until.get(backend)

    def record_result(self, backend: str, ok: bool, now: int) -> bool:
        """Devuelve True si esta llamada dispara una nueva ejeccion."""
        if ok:
            self._consecutive_failures[backend] = 0
            return False

        self._consecutive_failures[backend] = self._consecutive_failures.get(backend, 0) + 1
        if self._consecutive_failures[backend] >= self.threshold:
            self._eject(backend, now)
            self._consecutive_failures[backend] = 0
            return True
        return False

    def _eject(self, backend: str, now: int):
        count = self._ejection_count.get(backend, 0) + 1
        self._ejection_count[backend] = count
        duration = min(self.max_ejection_time, self.base_ejection_time * count)
        self._ejected_until[backend] = now + duration


class SuccessRateOutlierDetector:
    """Eyecta replicas cuya tasa de exito reciente esta muy por debajo
    del promedio del resto del pool (outlier estadistico), con dos
    resguardos:

      - no actua si todavia no hay suficiente señal
        (`min_requests` por replica, y un minimo de replicas
        comparables).
      - nunca eyecta mas de `max_ejection_fraction` del pool de una
        sola vez: si una GRAN parte del pool luce mal al mismo tiempo,
        lo mas probable es un problema compartido (una dependencia
        comun caida), no que cada replica individualmente este mal —
        eyectarlas a todas dejaria cero capacidad en vez de proteger
        algo.
    """

    def __init__(self, window_size: int = 20, min_requests: int = 20, stdev_factor: float = 1.5, max_ejection_fraction: float = 0.34):
        self.window_size = window_size
        self.min_requests = min_requests
        self.stdev_factor = stdev_factor
        self.max_ejection_fraction = max_ejection_fraction
        self._windows: dict = {}

    def record_result(self, backend: str, ok: bool):
        window = self._windows.setdefault(backend, deque(maxlen=self.window_size))
        window.append(ok)

    def success_rate(self, backend: str):
        window = self._windows.get(backend)
        if not window:
            return None
        return sum(window) / len(window)

    def compute_ejections(self) -> set:
        rates = {b: self.success_rate(b) for b, w in self._windows.items() if len(w) >= self.min_requests}
        if len(rates) < 3:
            return set()

        values = list(rates.values())
        mean = statistics.mean(values)
        stdev = statistics.pstdev(values) or 1e-9
        threshold = mean - self.stdev_factor * stdev

        below_threshold = sorted((b for b, r in rates.items() if r < threshold), key=lambda b: rates[b])
        max_ejections = max(0, int(len(rates) * self.max_ejection_fraction))
        return set(below_threshold[:max_ejections])
