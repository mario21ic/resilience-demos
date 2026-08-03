"""Servidor HTTP con un costo de "handshake" simulado que se paga UNA
SOLA VEZ por conexion TCP aceptada (en `setup()`, antes de leer ningun
request) — igual que el costo real de un handshake TCP+TLS. Con
HTTP/1.1 keep-alive, varios requests pueden reusar la misma conexion y
pagar ese costo una sola vez entre todos, en vez de una vez cada uno.

GET /work?duration=0.05                    -> "hace trabajo" ese tiempo
GET /admin/behavior?state=healthy|slow|error -> cambia el comportamiento
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HANDSHAKE_COST = 0.15  # simula el costo de TCP+TLS handshake, una vez por conexion nueva


class MultiplexHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # habilita keep-alive: una conexion, muchos requests

    def setup(self):
        super().setup()
        time.sleep(HANDSHAKE_COST)  # se paga UNA VEZ por conexion aceptada, no por request

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/admin/behavior":
            self._set_behavior(query.get("state", ["healthy"])[0])
            return

        if parsed.path == "/work":
            self._handle_work(query)
            return

        self._respond(404, {"error": "not found"})

    def _set_behavior(self, state: str):
        with self.server.behavior_lock:
            self.server.behavior = state
        self._respond(200, {"behavior": state})

    def _handle_work(self, query):
        with self.server.behavior_lock:
            behavior = self.server.behavior

        if behavior == "error":
            self._respond(500, {"error": "internal error"})
            return

        duration = float(query.get("duration", ["0.01"])[0])
        if behavior == "slow":
            duration *= 10
        time.sleep(duration)
        self._respond(200, {"status": "ok", "duration": duration})

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


def start_server(host="localhost", port=8776):
    server = ThreadingHTTPServer((host, port), MultiplexHandler)
    server.behavior = "healthy"  # "healthy" | "slow" | "error" -- estado propio de ESTA instancia
    server.behavior_lock = threading.Lock()
    return server


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servidor con costo de handshake simulado en http://{addr[0]}:{addr[1]}")
    print(f"Costo de handshake por conexion nueva: {HANDSHAKE_COST * 1000:.0f}ms")
    print("GET /work?duration=0.01")
    print("GET /admin/behavior?state=healthy|slow|error")
    server.serve_forever()
