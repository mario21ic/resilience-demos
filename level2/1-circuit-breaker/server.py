"""Dependencia simulada con comportamiento configurable, para poder
disparar el circuit breaker tanto por tasa de error como por latencia.

GET /dependency                       -> responde segun el comportamiento actual
GET /admin/behavior?state=healthy|error|slow  -> cambia el comportamiento
"""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_lock = threading.Lock()
_behavior = "healthy"  # "healthy" | "error" | "slow"


class DependencyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/admin/behavior":
            self._set_behavior(query.get("state", ["healthy"])[0])
            return

        if parsed.path == "/dependency":
            self._handle_dependency()
            return

        self._respond(404, b"not found")

    def _set_behavior(self, state: str):
        global _behavior
        with _lock:
            _behavior = state
        self._respond(200, f"behavior={state}".encode())

    def _handle_dependency(self):
        with _lock:
            behavior = _behavior

        if behavior == "error":
            self._respond(500, b"internal error")
            return

        if behavior == "slow":
            time.sleep(0.5)  # responde bien, pero lento
            self._respond(200, b"ok (lento)")
            return

        time.sleep(0.02)  # latencia normal de una dependencia sana
        self._respond(200, b"ok")

    def _respond(self, status: int, body: bytes):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        pass  # silencia el logging por defecto de cada request


def start_server(host="localhost", port=8769):
    return ThreadingHTTPServer((host, port), DependencyHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Dependencia simulada escuchando en http://{addr[0]}:{addr[1]}")
    print("GET /dependency")
    print("GET /admin/behavior?state=healthy|error|slow")
    print("Ctrl+C para detener")
    server.serve_forever()
