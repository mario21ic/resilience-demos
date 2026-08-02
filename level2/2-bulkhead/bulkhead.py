"""Bulkhead: limita cuantas llamadas concurrentes puede haber hacia una
dependencia especifica, usando un semaforo no bloqueante.

El nombre viene de los mamparos (bulkheads) que dividen el casco de un
barco en compartimentos estancos: si uno se inunda, el agua no pasa a
los demas y el barco no se hunde entero. Aplicado a software: si una
dependencia se degrada y consume todos los recursos (threads,
conexiones) que tiene asignados, eso no deberia afectar las llamadas a
OTRAS dependencias que comparten el mismo proceso.

Este bulkhead rechaza de inmediato (fail fast) las llamadas que
excedan el limite, en vez de encolarlas: una cola sin limite es en si
misma un problema (memoria, latencia acumulada); rechazar rapido es
una degradacion mas previsible y facil de razonar.
"""
import threading


class BulkheadFullError(Exception):
    """Se lanza cuando el bulkhead ya tiene `max_concurrent_calls` en curso."""


class Bulkhead:
    def __init__(self, name: str, max_concurrent_calls: int):
        self.name = name
        self.max_concurrent_calls = max_concurrent_calls
        self._semaphore = threading.Semaphore(max_concurrent_calls)
        self._lock = threading.Lock()
        self._in_flight = 0

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    def call(self, func, *args, **kwargs):
        acquired = self._semaphore.acquire(blocking=False)
        if not acquired:
            raise BulkheadFullError(
                f"bulkhead '{self.name}' lleno "
                f"({self.max_concurrent_calls} llamadas concurrentes en curso)"
            )
        with self._lock:
            self._in_flight += 1
        try:
            return func(*args, **kwargs)
        finally:
            with self._lock:
                self._in_flight -= 1
            self._semaphore.release()
