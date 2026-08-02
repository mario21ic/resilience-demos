"""Demo del patron de resiliencia: Idempotency keys.

El retry (ver 2-retry) asume que reintentar una operacion fallida es
seguro. Eso es cierto para operaciones idempotentes (un GET, un
"set X=5"), pero NO para operaciones con efectos secundarios como
"cobrar una tarjeta" o "crear un pedido": si el request original en
realidad SI se proceso en el servidor pero la respuesta se perdio (un
timeout del lado del cliente, una caida de red justo despues), un
retry ciego puede duplicar el efecto.

Una idempotency key resuelve esto: el cliente genera una clave unica
por OPERACION LOGICA (no por intento de red) y la reenvia igual en
cada retry. El servidor recuerda que clave ya proceso y, si la ve de
nuevo, devuelve el resultado guardado en vez de repetir el efecto.

Este demo compara, contra el mismo servicio de "cobros":

  Escenario A: el cliente reintenta SIN reutilizar una idempotency
               key -> el cobro se duplica.
  Escenario B: el cliente reintenta reutilizando la MISMA idempotency
               key -> el servidor detecta el duplicado y responde con
               el resultado ya calculado (replayed=True), sin cobrar
               una segunda vez.
"""
import json
import threading
import time
import urllib.error
import urllib.request
import uuid

from server import start_server

HOST, PORT = "localhost", 8767
BASE_URL = f"http://{HOST}:{PORT}/"


def charge(amount: int, idempotency_key: str | None, timeout_s: float, simulate_lost_response: bool) -> dict:
    url = f"{BASE_URL}charge?amount={amount}&simulate_lost_response={'1' if simulate_lost_response else '0'}"
    req = urllib.request.Request(url, method="POST")
    if idempotency_key:
        req.add_header("Idempotency-Key", idempotency_key)
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read())


def get_charge_count() -> int:
    with urllib.request.urlopen(f"{BASE_URL}debug/charge_count", timeout=2) as response:
        return json.loads(response.read())["charge_count"]


def reset_server():
    urllib.request.urlopen(f"{BASE_URL}reset", timeout=2).read()


def scenario_without_idempotency_key():
    print("Escenario A: retry SIN reutilizar idempotency key")
    reset_server()
    amount = 100

    print("  intento 1: respuesta lenta simulada, timeout corto del cliente (0.5s)")
    try:
        result = charge(amount, idempotency_key=None, timeout_s=0.5, simulate_lost_response=True)
        print(f"    -> respuesta: {result}")
    except (urllib.error.URLError, TimeoutError):
        print("    -> TIMEOUT en el cliente (el servidor SI llego a procesar el cobro)")

    print("  intento 2 (retry): el cliente cree que el intento 1 fallo del todo,")
    print("  y no tiene forma de decirle al servidor 'esto ya lo intente antes'")
    result = charge(amount, idempotency_key=None, timeout_s=5, simulate_lost_response=False)
    print(f"    -> respuesta: {result}")

    count = get_charge_count()
    print(f"  cobros reales procesados por el servidor: {count} (se cobro DOS veces por una sola compra)\n")


def scenario_with_idempotency_key():
    print("Escenario B: retry reutilizando la MISMA idempotency key")
    reset_server()
    amount = 100
    idempotency_key = str(uuid.uuid4())
    print(f"  idempotency key generada para esta operacion: {idempotency_key}")

    print("  intento 1: misma respuesta lenta simulada, mismo timeout corto (0.5s)")
    try:
        result = charge(amount, idempotency_key, timeout_s=0.5, simulate_lost_response=True)
        print(f"    -> respuesta: {result}")
    except (urllib.error.URLError, TimeoutError):
        print("    -> TIMEOUT en el cliente (el servidor SI llego a procesar el cobro)")

    print("  intento 2 (retry): se reenvia la MISMA idempotency key")
    result = charge(amount, idempotency_key, timeout_s=5, simulate_lost_response=False)
    print(f"    -> respuesta: {result}")

    count = get_charge_count()
    print(f"  cobros reales procesados por el servidor: {count} (una sola vez, el retry solo repitio la respuesta)\n")


def main():
    server = start_server(HOST, PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.2)  # da tiempo a que el servidor quede listo

    scenario_without_idempotency_key()
    scenario_with_idempotency_key()

    server.shutdown()


if __name__ == "__main__":
    main()
