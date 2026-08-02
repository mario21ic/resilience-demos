"""Request coalescing / single-flight: si varios callers concurrentes
piden la MISMA clave al mismo tiempo, solo el primero ejecuta la
llamada real; el resto espera y recibe el mismo resultado, en vez de
disparar cada uno su propia llamada redundante.

Es la defensa clasica contra el "cache stampede" (o "dog-piling"): una
clave popular expira o nunca estuvo en cache, y muchos requests
concurrentes intentan recalcularla/refetchearla al mismo tiempo. Sin
coordinacion, eso se traduce en tantas llamadas identicas al backend
como requests concurrentes haya. Con coalescing, es una sola.

Basado en el mismo patron que `golang.org/x/sync/singleflight`.
"""
import threading


class _Call:
    def __init__(self):
        self.done = threading.Event()
        self.result = None
        self.exception = None
        self.waiters = 1  # cuenta al lider tambien, solo para reportar en el demo


class SingleFlightGroup:
    def __init__(self):
        self._lock = threading.Lock()
        self._in_flight: dict[str, _Call] = {}

    def do(self, key: str, func, *args, **kwargs):
        """Ejecuta `func(*args, **kwargs)` una sola vez por `key` entre
        todos los callers concurrentes. El primero en llegar es el
        "lider" y hace la llamada real; los que llegan mientras esa
        llamada sigue en curso solo esperan su resultado.
        """
        with self._lock:
            call = self._in_flight.get(key)
            if call is not None:
                call.waiters += 1
                is_leader = False
            else:
                call = _Call()
                self._in_flight[key] = call
                is_leader = True

        if not is_leader:
            call.done.wait()
            if call.exception is not None:
                raise call.exception
            return call.result

        try:
            call.result = func(*args, **kwargs)
        except Exception as exc:
            call.exception = exc
        finally:
            with self._lock:
                del self._in_flight[key]
            call.done.set()

        if call.exception is not None:
            raise call.exception
        return call.result
