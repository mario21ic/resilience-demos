"""Leaky bucket como cola: en vez de rechazar de inmediato a quien
supera la capacidad instantanea (lo que hace un rate limiter comun,
ver [3-rate-limiting](../3-rate-limiting)), el throttling ENCOLA el
exceso y lo procesa a un ritmo constante, convirtiendo una rafaga en
una fila con espera acotada — se cambia latencia por disponibilidad,
en vez de simplemente rechazar.

Se modela como una cola FIFO con tiempo de servicio fijo (`1/rate` por
request): cada request nuevo se agenda para el primer momento libre
del "servidor". Si ese momento cae mas alla de lo que la cola puede
absorber (`max_queue_size / rate`), se rechaza — ninguna cola real
puede ser infinita, y una cola sin limite es en si misma un riesgo
(memoria, latencia sin techo para el ultimo de la fila).
"""


class QueueFullError(Exception):
    """La espera resultante supera lo que la cola puede absorber."""


class LeakyBucketThrottle:
    def __init__(self, rate: float, max_queue_size: int):
        self.rate = rate
        self.max_queue_size = max_queue_size
        self.max_wait = max_queue_size / rate
        self._next_free_slot = 0.0

    def schedule(self, now: float) -> float:
        """Devuelve el instante (relativo a `now`) en que este request
        sera atendido, o lanza `QueueFullError` si la espera necesaria
        excede lo que la cola admite.

        Un request rechazado no reserva turno ni le quita lugar a
        nadie: `_next_free_slot` solo avanza para los que se aceptan.
        """
        earliest_service_time = max(now, self._next_free_slot)
        wait = earliest_service_time - now
        if wait > self.max_wait:
            raise QueueFullError(
                f"la espera resultante ({wait:.2f}s) supera lo que la cola admite ({self.max_wait:.2f}s)"
            )
        self._next_free_slot = earliest_service_time + (1.0 / self.rate)
        return earliest_service_time
