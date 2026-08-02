"""Tres algoritmos de rate limiting con la misma interfaz:
`allow_request(now: float) -> bool`.

Todos deciden, dado un timestamp `now`, si el request de ese instante
se deja pasar o se rechaza, en base a cuantos requests ya se
permitieron recientemente. Ninguno hace I/O: son puro calculo, para
poder compararlos contra la misma linea de tiempo simulada.
"""
from collections import deque


class FixedWindowLimiter:
    """Cuenta requests en ventanas de tiempo fijas y no superpuestas
    (ej. "por cada segundo del reloj, ventana [0,1), [1,2), ...").

    Simple y barato, pero tiene un defecto conocido: un cliente puede
    mandar `max_requests` justo al final de una ventana y otros
    `max_requests` justo al principio de la siguiente, logrando el
    doble del limite nominal en una fraccion de segundo.
    """

    def __init__(self, max_requests: int, window_size: float = 1.0):
        self.max_requests = max_requests
        self.window_size = window_size
        self._window_start = None
        self._count = 0

    def allow_request(self, now: float) -> bool:
        window_index = int(now // self.window_size)
        current_window_start = window_index * self.window_size
        if self._window_start != current_window_start:
            self._window_start = current_window_start
            self._count = 0

        if self._count < self.max_requests:
            self._count += 1
            return True
        return False


class SlidingWindowLogLimiter:
    """Guarda el timestamp de cada request aceptado y, para cada
    request nuevo, descarta los que ya salieron de la ventana
    deslizante de `window_size` segundos hacia atras.

    Sin el defecto de borde del fixed window (siempre mira los
    ultimos `window_size` segundos reales, no una ventana fija del
    reloj), a costa de guardar mas estado por cliente.
    """

    def __init__(self, max_requests: int, window_size: float = 1.0):
        self.max_requests = max_requests
        self.window_size = window_size
        self._timestamps = deque()

    def allow_request(self, now: float) -> bool:
        cutoff = now - self.window_size
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) < self.max_requests:
            self._timestamps.append(now)
            return True
        return False


class TokenBucketLimiter:
    """Un balde con `capacity` tokens que se recargan continuamente a
    `rate` tokens por segundo. Cada request consume 1 token; si no hay
    tokens disponibles, se rechaza.

    Permite absorber rafagas cortas (hasta `capacity` de una vez) sin
    dejar de limitar el promedio sostenido a `rate` requests/segundo -
    el mismo algoritmo que usan AWS API Gateway y Stripe, entre otros.
    """

    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_refill = 0.0

    @property
    def tokens(self) -> float:
        return self._tokens

    def allow_request(self, now: float) -> bool:
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False
