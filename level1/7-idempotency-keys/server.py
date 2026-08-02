"""Servicio simulado de "cobros" para demostrar idempotency keys.

Expone POST /charge, que tiene un efecto real (incrementa un contador
de cobros procesados) y opcionalmente demora la respuesta lo
suficiente como para que el cliente se rinda por timeout, aun cuando
el cobro YA se proceso del lado del servidor. Ese es justamente el
escenario donde un retry sin idempotency key duplica el efecto: el
cliente no sabe si su request original realmente fallo o si solo se
perdio la respuesta.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_lock = threading.Lock()
_charge_count = 0
_processed_keys = {}  # idempotency_key -> (charge_id, amount)


class ChargeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/charge":
            self._respond(404, b"not found")
            return

        query = parse_qs(parsed.query)
        amount = query.get("amount", ["10"])[0]
        simulate_lost_response = query.get("simulate_lost_response", ["0"])[0] == "1"
        idempotency_key = self.headers.get("Idempotency-Key")

        global _charge_count
        with _lock:
            if idempotency_key and idempotency_key in _processed_keys:
                charge_id, stored_amount = _processed_keys[idempotency_key]
                body = json.dumps(
                    {"charge_id": charge_id, "amount": stored_amount, "replayed": True}
                ).encode()
                self._respond(200, body)
                return

            # efecto real del lado del servidor: esto pasa una sola vez
            # por idempotency key, sin importar cuantas veces llegue el
            # mismo request.
            _charge_count += 1
            charge_id = f"ch_{_charge_count}"
            if idempotency_key:
                _processed_keys[idempotency_key] = (charge_id, amount)
            body = json.dumps(
                {"charge_id": charge_id, "amount": amount, "replayed": False}
            ).encode()

        if simulate_lost_response:
            # el cobro ya quedo procesado y guardado arriba; esta demora
            # simula que la RESPUESTA se pierde en el camino (ej. el
            # cliente ya se rindio por timeout antes de que esto termine)
            time.sleep(1.5)

        self._respond(200, body)

    def do_GET(self):
        parsed = urlparse(self.path)
        global _charge_count
        if parsed.path == "/debug/charge_count":
            self._respond(200, json.dumps({"charge_count": _charge_count}).encode())
            return
        if parsed.path == "/reset":
            with _lock:
                _charge_count = 0
                _processed_keys.clear()
            self._respond(200, b"reset ok")
            return
        self._respond(404, b"not found")

    def _respond(self, status: int, body: bytes):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # el cliente ya se rindio por timeout; no hay a quien responder

    def log_message(self, format, *args):
        pass  # silencia el logging por defecto de cada request


def start_server(host="localhost", port=8767):
    return ThreadingHTTPServer((host, port), ChargeHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicio de cobros escuchando en http://{addr[0]}:{addr[1]}")
    print("POST /charge?amount=100&simulate_lost_response=1  (header: Idempotency-Key)")
    print("Ctrl+C para detener")
    server.serve_forever()
