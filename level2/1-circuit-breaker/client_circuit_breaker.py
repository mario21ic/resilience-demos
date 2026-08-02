"""Demo del patron de resiliencia: Circuit breaker (por tasa de error
y por latencia).

Timeout y retry (level1) operan sobre UNA llamada. El circuit breaker
mira el PATRON de varias llamadas recientes: si una fraccion
suficiente de ellas esta fallando o siendo demasiado lenta, asume que
la dependencia esta degradada y deja de intentar por un rato — sin
eso, cada cliente seguiria golpeando (y esperando) a un servicio que
ya sabemos que no va a responder bien, alargando timeouts y
retrasando la deteccion del problema en el resto del sistema.

Este demo recorre las dos causas de disparo sobre la misma
dependencia simulada:

  Parte A: el backend empieza a devolver errores  -> abre por TASA DE ERROR.
  Parte B: el backend responde bien pero lento    -> abre por TASA DE LLAMADAS LENTAS.

En ambas partes se muestra el circuito completo: CLOSED -> OPEN ->
HALF_OPEN -> (vuelve a abrir si la dependencia sigue mal) -> CLOSED
cuando finalmente se recupera.
"""
import threading
import time
import urllib.error
import urllib.request

from circuit_breaker import CircuitBreaker, CircuitOpenError
from server import start_server

HOST, PORT = "localhost", 8769
BASE_URL = f"http://{HOST}:{PORT}/"


def set_backend_behavior(state: str):
    urllib.request.urlopen(f"{BASE_URL}admin/behavior?state={state}", timeout=2).read()


def call_dependency():
    with urllib.request.urlopen(f"{BASE_URL}dependency", timeout=2.0) as response:
        return response.read().decode()


def guarded_call(breaker: CircuitBreaker, label: str):
    try:
        result = breaker.call(call_dependency)
        print(f"  {label:<10} -> OK: {result!r}  [circuito: {breaker.state.value}]")
    except CircuitOpenError:
        print(f"  {label:<10} -> RECHAZADA sin llamar al backend (circuito abierto)  [circuito: {breaker.state.value}]")
    except urllib.error.HTTPError as exc:
        print(f"  {label:<10} -> FALLA real ({exc.code})  [circuito: {breaker.state.value}]")


def wait_for_reset(breaker: CircuitBreaker):
    print(f"  ... esperando {breaker.reset_timeout:.1f}s de reset_timeout para pasar a half-open ...")
    time.sleep(breaker.reset_timeout + 0.05)


def demo_trip_by_error_rate():
    print("=" * 70)
    print("Parte A: el circuito abre por TASA DE ERROR")
    print("=" * 70)
    breaker = CircuitBreaker(
        failure_rate_threshold=0.5,
        slow_call_rate_threshold=0.5,
        slow_call_duration=0.3,
        window_size=6,
        reset_timeout=1.0,
        half_open_max_calls=2,
    )

    print("\n1) Backend sano: se llena la ventana con exitos, el circuito queda cerrado.")
    set_backend_behavior("healthy")
    for i in range(6):
        guarded_call(breaker, f"call {i + 1}")

    print("\n2) El backend empieza a fallar. Tras suficientes fallas en la ventana, abre.")
    set_backend_behavior("error")
    for i in range(4):
        guarded_call(breaker, f"call {i + 1}")
    print(f"  motivo de apertura: {breaker.last_trip_reason}")

    print("\n3) Mientras esta abierto, las llamadas se rechazan sin tocar el backend:")
    for i in range(2):
        guarded_call(breaker, f"call {i + 1}")

    wait_for_reset(breaker)
    print("4) Half-open, pero el backend TODAVIA esta fallando -> vuelve a abrir:")
    guarded_call(breaker, "trial 1")
    print(f"  motivo de apertura: {breaker.last_trip_reason}")

    print("\n5) El backend se recupera de verdad:")
    set_backend_behavior("healthy")
    wait_for_reset(breaker)
    print("  half-open, ahora con backend sano -> las llamadas de prueba cierran el circuito:")
    for i in range(2):
        guarded_call(breaker, f"trial {i + 1}")
    print(f"  estado final: {breaker.state.value}")


def demo_trip_by_latency():
    print("\n" + "=" * 70)
    print("Parte B: el circuito abre por TASA DE LLAMADAS LENTAS")
    print("=" * 70)
    breaker = CircuitBreaker(
        failure_rate_threshold=0.5,
        slow_call_rate_threshold=0.5,
        slow_call_duration=0.3,
        window_size=6,
        reset_timeout=1.0,
        half_open_max_calls=2,
    )

    print("\n1) Backend sano: se llena la ventana con exitos rapidos, el circuito queda cerrado.")
    set_backend_behavior("healthy")
    for i in range(6):
        guarded_call(breaker, f"call {i + 1}")

    print("\n2) El backend sigue respondiendo 200 OK, pero ahora tarda 0.5s (> 0.3s = lento).")
    print("   Ninguna llamada 'falla' en sentido HTTP, pero igual abre el circuito.")
    set_backend_behavior("slow")
    for i in range(4):
        guarded_call(breaker, f"call {i + 1}")
    print(f"  motivo de apertura: {breaker.last_trip_reason}")

    print("\n3) Mientras esta abierto, se ahorra la espera de 0.5s por llamada (fail fast):")
    for i in range(2):
        guarded_call(breaker, f"call {i + 1}")

    print("\n4) El backend vuelve a responder rapido:")
    set_backend_behavior("healthy")
    wait_for_reset(breaker)
    print("  half-open, ahora con respuestas rapidas -> cierra el circuito:")
    for i in range(2):
        guarded_call(breaker, f"trial {i + 1}")
    print(f"  estado final: {breaker.state.value}")


def main():
    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)  # da tiempo a que el servidor quede listo

    demo_trip_by_error_rate()
    demo_trip_by_latency()

    server.shutdown()


if __name__ == "__main__":
    main()
