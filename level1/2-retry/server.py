"""Servicio simulado que falla las primeras N veces y luego se recupera.

Se usa para demostrar el patron de retry en client_retry.py. El estado
de fallos se guarda por "key" para poder correr varios escenarios
independientes contra el mismo servidor sin que se pisen entre si.
"""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_lock = threading.Lock()
_attempts_by_key = {}


class FlakyServiceHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/reset":
            key = query.get("key", ["default"])[0]
            with _lock:
                _attempts_by_key.pop(key, None)
            self._respond(200, b"reset ok")
            return

        if parsed.path == "/flaky":
            key = query.get("key", ["default"])[0]
            fail_times = int(query.get("fail_times", ["0"])[0])

            with _lock:
                _attempts_by_key[key] = _attempts_by_key.get(key, 0) + 1
                attempt = _attempts_by_key[key]

            if attempt <= fail_times:
                self._respond(503, f"fallo transitorio (intento {attempt})".encode())
            else:
                self._respond(200, f"ok tras {attempt} intento(s)".encode())
            return

        self._respond(404, b"not found")

    def _respond(self, status: int, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # silencia el logging por defecto de cada request


def start_server(host="localhost", port=8766):
    return ThreadingHTTPServer((host, port), FlakyServiceHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicio flaky escuchando en http://{addr[0]}:{addr[1]}")
    print("Prueba: /flaky?key=demo&fail_times=2")
    print("Reset:  /reset?key=demo")
    print("Ctrl+C para detener")
    server.serve_forever()
