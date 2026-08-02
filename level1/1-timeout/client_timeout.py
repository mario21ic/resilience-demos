"""Demo del patron de resiliencia: Timeout.

Un timeout acota cuanto tiempo esta dispuesto a esperar el llamador a
que una dependencia responda. Sin el, un servicio lento o colgado
puede bloquear hilos/conexiones indefinidamente, agotando recursos del
llamador y propagando la falla (cascading failure).

Este script levanta el "servicio lento" local y compara:
  1) una llamada donde el timeout alcanza de sobra,
  2) una llamada donde el servicio tarda mas que el timeout, forzando
     un fallo rapido (fail fast) y el uso de un valor de respaldo (fallback).
"""
import threading
import time
import urllib.error
import urllib.request

from server import start_server

HOST, PORT = "localhost", 8765
BASE_URL = f"http://{HOST}:{PORT}/"


def call_service(delay_s: float, timeout_s: float) -> dict:
    """Llama al servicio, abortando si tarda mas de `timeout_s` segundos."""
    url = f"{BASE_URL}?delay={delay_s}"
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return {"ok": True, "body": response.read().decode()}


def call_with_fallback(delay_s: float, timeout_s: float, fallback: dict) -> dict:
    started = time.monotonic()
    try:
        result = call_service(delay_s, timeout_s)
        elapsed = time.monotonic() - started
        print(f"  -> exito en {elapsed:.2f}s: {result['body']}")
        return result
    except (urllib.error.URLError, TimeoutError) as exc:
        elapsed = time.monotonic() - started
        print(f"  -> TIMEOUT tras {elapsed:.2f}s ({exc}); se usa fallback")
        return fallback


def main():
    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)  # da tiempo a que el servidor quede listo

    fallback_response = {"ok": False, "body": "respuesta cacheada/por defecto"}

    print("Escenario 1: el servicio responde rapido (1s), timeout generoso (5s)")
    call_with_fallback(delay_s=1, timeout_s=5, fallback=fallback_response)

    print("\nEscenario 2: el servicio es lento (5s), timeout corto (1s)")
    call_with_fallback(delay_s=5, timeout_s=1, fallback=fallback_response)

    print("\nSin timeout, el llamador habria esperado los 5s completos.")
    print("Con el timeout de 1s, fallamos rapido y nos recuperamos con el fallback.")

    server.shutdown()


if __name__ == "__main__":
    main()
