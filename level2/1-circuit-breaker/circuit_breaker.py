"""Circuit breaker que dispara tanto por tasa de error como por
latencia (llamadas "lentas"), al estilo de resilience4j.

Estados:

  CLOSED     -> las llamadas pasan normalmente. Se registra cada
               resultado (exito/falla, duracion) en una ventana
               deslizante de tamano fijo. Si al evaluarla la tasa de
               fallas o la tasa de llamadas lentas supera su umbral,
               el circuito se abre.
  OPEN       -> las llamadas se rechazan de inmediato (fail fast), sin
               siquiera intentar la llamada real, hasta que pasa
               `reset_timeout`.
  HALF_OPEN  -> se permite un numero limitado de llamadas de prueba.
               Si todas son exitosas y rapidas, el circuito cierra. Si
               alguna falla o es lenta, vuelve a abrirse.

Un timeout ([1-timeout] en level1) evita que UNA llamada se cuelgue.
Un circuit breaker evita seguir intentando cuando el PATRON de varias
llamadas ya indica que la dependencia esta degradada (por errores o
por lentitud), ahorrandole carga a algo que ya esta sufriendo.
"""
import enum
import time
from collections import deque


class State(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Se lanza cuando el circuito esta abierto: la llamada ni se intenta."""


class CircuitBreaker:
    def __init__(
        self,
        failure_rate_threshold: float = 0.5,
        slow_call_rate_threshold: float = 0.5,
        slow_call_duration: float = 0.3,
        window_size: int = 6,
        reset_timeout: float = 1.0,
        half_open_max_calls: int = 2,
    ):
        self.failure_rate_threshold = failure_rate_threshold
        self.slow_call_rate_threshold = slow_call_rate_threshold
        self.slow_call_duration = slow_call_duration
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = State.CLOSED
        self.window = deque(maxlen=window_size)  # cada item: (ok: bool, is_slow: bool)
        self.opened_at = None
        self.half_open_calls = 0
        self.half_open_successes = 0
        self.last_trip_reason = None

    def allow_request(self) -> bool:
        """Ademas de responder si se puede llamar, evalua de forma
        perezosa si ya paso `reset_timeout` para pasar de OPEN a
        HALF_OPEN — no hace falta un timer en background.
        """
        if self.state == State.OPEN:
            if time.monotonic() - self.opened_at >= self.reset_timeout:
                self._transition_half_open()
            else:
                return False

        if self.state == State.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return True

    def call(self, func, *args, **kwargs):
        if not self.allow_request():
            raise CircuitOpenError("circuito abierto: se rechaza la llamada sin intentarla")

        if self.state == State.HALF_OPEN:
            self.half_open_calls += 1

        started = time.monotonic()
        try:
            result = func(*args, **kwargs)
        except Exception:
            self._record(ok=False, duration=time.monotonic() - started)
            raise
        else:
            self._record(ok=True, duration=time.monotonic() - started)
            return result

    def _record(self, ok: bool, duration: float):
        is_slow = duration >= self.slow_call_duration

        if self.state == State.HALF_OPEN:
            if ok and not is_slow:
                self.half_open_successes += 1
                if self.half_open_successes >= self.half_open_max_calls:
                    self._transition_closed()
            else:
                reason = "fallo" if not ok else "lentitud"
                self._transition_open(f"una llamada de prueba tuvo {reason} en half-open")
            return

        self.window.append((ok, is_slow))
        if len(self.window) == self.window.maxlen:
            self._evaluate_window()

    def _evaluate_window(self):
        n = len(self.window)
        failures = sum(1 for ok, _ in self.window if not ok)
        slow_calls = sum(1 for _, slow in self.window if slow)
        failure_rate = failures / n
        slow_rate = slow_calls / n

        if failure_rate >= self.failure_rate_threshold:
            self._transition_open(f"tasa de error {failure_rate:.0%} >= {self.failure_rate_threshold:.0%}")
        elif slow_rate >= self.slow_call_rate_threshold:
            self._transition_open(f"tasa de llamadas lentas {slow_rate:.0%} >= {self.slow_call_rate_threshold:.0%}")

    def _transition_open(self, reason: str):
        self.state = State.OPEN
        self.opened_at = time.monotonic()
        self.window.clear()
        self.last_trip_reason = reason

    def _transition_half_open(self):
        self.state = State.HALF_OPEN
        self.half_open_calls = 0
        self.half_open_successes = 0

    def _transition_closed(self):
        self.state = State.CLOSED
        self.window.clear()
        self.last_trip_reason = None
