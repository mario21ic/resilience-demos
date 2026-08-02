"""Load shedding: cuando el sistema esta cerca de su capacidad, no se
trata a todos los requests por igual — se rechazan primero los de
MENOR prioridad, preservando la capacidad restante para los mas
importantes. Inspirado en las clases de criticidad (CRITICAL, DEFAULT,
SHEDDABLE) que describe el libro de SRE de Google en el capitulo de
manejo de sobrecarga.

A diferencia del rate limiting ([3-rate-limiting](../3-rate-limiting),
un limite fijo por cliente/clave) y del throttling
([4-throttling](../4-throttling), encolar con espera), el load
shedding mira la capacidad PROPIA del sistema en este momento (cuantos
requests hay en curso) y decide admitir o rechazar de inmediato segun
eso y la prioridad del request — sin cola, sin espera: se acepta ya o
se rechaza ya.
"""
import threading


class LoadSheddingError(Exception):
    """Se lanza cuando el sistema esta demasiado cargado para esta prioridad."""


class LoadShedder:
    # A mayor "utilizacion admitida", mas protegida esta esa
    # prioridad: sheddable empieza a rechazarse desde el 50% de uso,
    # default desde el 80%, y critical recien al llegar al 100% —
    # asi siempre queda margen reservado para lo mas importante.
    DEFAULT_THRESHOLDS = {
        "sheddable": 0.5,
        "default": 0.8,
        "critical": 1.0,
    }

    def __init__(self, capacity: int, thresholds: dict | None = None):
        self.capacity = capacity
        self.thresholds = thresholds if thresholds is not None else dict(self.DEFAULT_THRESHOLDS)
        self._in_flight = 0
        self._lock = threading.Lock()

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    def try_admit(self, priority: str) -> bool:
        threshold = self.thresholds[priority]
        with self._lock:
            utilization = self._in_flight / self.capacity
            if utilization >= threshold:
                return False
            self._in_flight += 1
            return True

    def release(self):
        with self._lock:
            self._in_flight -= 1
