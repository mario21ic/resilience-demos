"""Dos dependencias simuladas, sin relacion entre si:

  GET /service-a  -> comportamiento configurable (healthy | slow)
  GET /service-b  -> siempre sana y rapida

  GET /admin/service-a?state=healthy|slow  -> cambia el comportamiento de A

La idea es que A y B representan servicios totalmente independientes.
Que A se degrade no deberia tener ningun motivo tecnico para afectar
las llamadas a B — el problema que el bulkhead evita es que SI las
afecte por compartir recursos del lado del cliente (ver README).
"""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_lock = threading.Lock()
_service_a_behavior = "healthy"  # "healthy" | "slow"


class TwoServicesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/admin/service-a":
            self._set_service_a_behavior(query.get("state", ["healthy"])[0])
            return

        if parsed.path == "/service-a":
            self._handle_service_a()
            return

        if parsed.path == "/service-b":
            self._handle_service_b()
            return

        self._respond(404, b"not found")

    def _set_service_a_behavior(self, state: str):
        global _service_a_behavior
        with _lock:
            _service_a_behavior = state
        self._respond(200, f"service-a behavior={state}".encode())

    def _handle_service_a(self):
        with _lock:
            behavior = _service_a_behavior
        if behavior == "slow":
            time.sleep(1.0)
        else:
            time.sleep(0.02)
        self._respond(200, b"service-a ok")

    def _handle_service_b(self):
        time.sleep(0.02)  # service-b siempre responde rapido
        self._respond(200, b"service-b ok")

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


def start_server(host="localhost", port=8770):
    return ThreadingHTTPServer((host, port), TwoServicesHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicios simulados escuchando en http://{addr[0]}:{addr[1]}")
    print("GET /service-a, /service-b")
    print("GET /admin/service-a?state=healthy|slow")
    print("Ctrl+C para detener")
    server.serve_forever()
