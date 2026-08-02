"""Demo del patron de resiliencia: Retry (con backoff + jitter).

Un retry reintenta una operacion que fallo, asumiendo que la falla es
transitoria (una caida momentanea de red, un pico de carga puntual,
etc.). Reintentar sin cuidado puede empeorar las cosas: si un cliente
(o miles de clientes) reintentan de inmediato y en rafaga, generan un
"retry storm" que mantiene caido a un servicio que recien estaba
recuperandose.

Este demo compara:
  1) Retry naive: reintenta de inmediato, sin espera entre intentos.
  2) Retry con backoff exponencial + jitter: espera creciente y
     aleatoria entre intentos, con un limite maximo de reintentos.
  3) Que pasa cuando la falla es permanente y se agotan los reintentos.
"""
import random
import threading
import time
import urllib.error
import urllib.request

from server import start_server

HOST, PORT = "localhost", 8766
BASE_URL = f"http://{HOST}:{PORT}/"


class RetryExhausted(Exception):
    pass


def call_flaky_service(key: str, fail_times: int, timeout_s: float = 2.0) -> str:
    """Cada intento individual debe llevar su propio timeout (ver 1-timeout)."""
    url = f"{BASE_URL}flaky?key={key}&fail_times={fail_times}"
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return response.read().decode()


def reset_scenario(key: str):
    urllib.request.urlopen(f"{BASE_URL}reset?key={key}", timeout=2.0).read()


def retry_naive(key: str, fail_times: int, max_attempts: int = 5) -> str:
    """Reintenta inmediatamente, sin espera entre intentos. NO recomendado."""
    for attempt in range(1, max_attempts + 1):
        try:
            body = call_flaky_service(key, fail_times)
            print(f"  intento {attempt}: exito -> {body}")
            return body
        except urllib.error.HTTPError as exc:
            print(f"  intento {attempt}: fallo ({exc.code}), reintentando sin espera...")
    raise RetryExhausted(f"se agotaron {max_attempts} intentos")


def retry_with_backoff(
    key: str,
    fail_times: int,
    max_attempts: int = 5,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
) -> str:
    """Backoff exponencial (base * 2^intento) acotado a max_delay, con jitter."""
    for attempt in range(1, max_attempts + 1):
        try:
            body = call_flaky_service(key, fail_times)
            print(f"  intento {attempt}: exito -> {body}")
            return body
        except urllib.error.HTTPError as exc:
            if attempt == max_attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay_with_jitter = random.uniform(0, delay)
            print(
                f"  intento {attempt}: fallo ({exc.code}), "
                f"esperando {delay_with_jitter:.2f}s antes de reintentar..."
            )
            time.sleep(delay_with_jitter)
    raise RetryExhausted(f"se agotaron {max_attempts} intentos")


def main():
    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)  # da tiempo a que el servidor quede listo

    print("Escenario 1: retry naive contra una falla transitoria (falla 2 veces, luego exito)")
    reset_scenario("naive")
    started = time.monotonic()
    retry_naive("naive", fail_times=2)
    print(f"  tiempo total: {time.monotonic() - started:.2f}s\n")

    print("Escenario 2: retry con backoff exponencial + jitter, misma falla transitoria")
    reset_scenario("backoff")
    started = time.monotonic()
    retry_with_backoff("backoff", fail_times=2)
    print(f"  tiempo total: {time.monotonic() - started:.2f}s\n")

    print("Escenario 3: falla permanente (el servicio nunca se recupera) -> se agotan los reintentos")
    reset_scenario("permanent")
    try:
        retry_with_backoff("permanent", fail_times=999, max_attempts=4)
    except RetryExhausted as exc:
        print(f"  -> {exc}; hay que usar un fallback o propagar el error al llamador")

    server.shutdown()


if __name__ == "__main__":
    main()
