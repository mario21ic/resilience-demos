"""Backend "caro" simulado: cada invocacion real tarda 0.3s y queda
registrada en un contador global, para poder ver cuantas veces se
ejecuto DE VERDAD el trabajo, sin importar cuantos clientes lo hayan
pedido al mismo tiempo.

GET /compute?key=X       -> "calcula" el valor de X (0.3s) y cuenta la llamada
GET /debug/call_count    -> cuantas llamadas reales hubo en total
GET /reset               -> reinicia el contador
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_lock = threading.Lock()
_call_count = 0


class ExpensiveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _call_count
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/debug/call_count":
            self._respond(200, {"call_count": _call_count})
            return

        if parsed.path == "/reset":
            with _lock:
                _call_count = 0
            self._respond(200, {"reset": True})
            return

        if parsed.path == "/compute":
            key = query.get("key", ["default"])[0]
            self._handle_compute(key)
            return

        self._respond(404, {"error": "not found"})

    def _handle_compute(self, key: str):
        global _call_count
        with _lock:
            _call_count += 1
            call_number = _call_count

        time.sleep(0.3)  # trabajo caro: una consulta pesada, un calculo, etc.
        self._respond(200, {"key": key, "computed_at_call": call_number})

    def _respond(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        pass  # silencia el logging por defecto de cada request


def start_server(host="localhost", port=8774):
    return ThreadingHTTPServer((host, port), ExpensiveHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Backend caro escuchando en http://{addr[0]}:{addr[1]}")
    print("GET /compute?key=X")
    print("Ctrl+C para detener")
    server.serve_forever()
