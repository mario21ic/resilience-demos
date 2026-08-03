"""El "multiplexer" de un router de proveedores/modelos (llamar a
distintos backends de LLM, distintas regiones de una misma API, etc.)
parece, desde afuera, un objeto simple: `multiplexer.request(payload)`.
Por dentro es la composicion de varios patrones ya vistos:

  - connection pooling: cada proveedor tiene su conexion ya
    establecida y reusada (ver demo_multiplexer.py Parte 1).
  - circuit breaker: cada proveedor tiene el suyo — versión
    simplificada aca; la version completa (con deteccion por latencia
    ademas de errores) esta en level2/1-circuit-breaker.
  - failover: si el proveedor preferido falla o tiene el circuito
    abierto, se sigue automaticamente al siguiente en la lista.
  - load balancing: el ORDEN de `providers` es, en su forma mas
    simple, una politica de balanceo (siempre preferir el primero
    disponible) — las estrategias de level3/4-load-balancing aplican
    igual de bien aca para elegir a quien probar primero.
"""
import http.client
import time


class SimpleCircuitBreaker:
    """Version minima de level2/1-circuit-breaker: solo cuenta fallas
    consecutivas. Suficiente para mostrar la composicion; para
    deteccion por latencia y ventana deslizante, ver la version
    completa.
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 1.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._consecutive_failures = 0
        self._opened_at = None

    def allow_request(self) -> bool:
        if self._opened_at is None:
            return True
        if time.monotonic() - self._opened_at >= self.reset_timeout:
            return True  # medio abierto: se deja pasar un intento de prueba
        return False

    def record_success(self):
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self):
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._opened_at = time.monotonic()


class Provider:
    """Un backend con su propia conexion pooled (ya conectada, se
    reusa entre requests) y su propio circuit breaker.
    """

    def __init__(self, name: str, host: str, port: int):
        self.name = name
        self.conn = http.client.HTTPConnection(host, port)
        self.conn.connect()
        self.circuit = SimpleCircuitBreaker()

    def call(self, path: str) -> bytes:
        self.conn.request("GET", path)
        response = self.conn.getresponse()
        body = response.read()
        if response.status >= 500:
            raise RuntimeError(f"{self.name} devolvio {response.status}")
        return body


class Multiplexer:
    """Prueba los proveedores en orden (la politica de balanceo mas
    simple posible: preferencia fija); salta los que tienen el
    circuito abierto; si uno falla, sigue automaticamente al proximo
    — todo dentro de UN solo `request()`, transparente para quien
    llama.
    """

    def __init__(self, providers: list):
        self.providers = providers

    def request(self, path: str):
        attempts = []
        for provider in self.providers:
            if not provider.circuit.allow_request():
                attempts.append(f"{provider.name}(circuito abierto, se salta)")
                continue
            try:
                result = provider.call(path)
                provider.circuit.record_success()
                attempts.append(f"{provider.name}(OK)")
                return provider.name, result, attempts
            except RuntimeError:
                provider.circuit.record_failure()
                attempts.append(f"{provider.name}(fallo)")

        raise RuntimeError(f"todos los proveedores fallaron: {attempts}")
