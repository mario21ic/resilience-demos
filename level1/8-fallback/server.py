"""Servicio simulado de recomendaciones, con salud configurable.

GET /recommendations?user_id=U      -> devuelve items personalizados
GET /admin/health?state=healthy|slow|down  -> cambia el comportamiento

El estado de salud es global y compartido entre requests, simulando
que el backend real esta sano, degradado (responde tarde) o caido.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

_lock = threading.Lock()
_health = "healthy"  # "healthy" | "slow" | "down"

_CATALOG = {
    "alice": ["zapatillas trail", "medias tecnicas", "mochila 20L"],
    "bob": ["cafetera", "molinillo", "taza termica"],
}
_DEFAULT_ITEMS = ["mas vendidos", "mas vendidos #2", "mas vendidos #3"]


class RecommendationsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/admin/health":
            self._set_health(query.get("state", ["healthy"])[0])
            return

        if parsed.path == "/recommendations":
            self._handle_recommendations(query)
            return

        self._respond(404, b"not found")

    def _set_health(self, state: str):
        global _health
        with _lock:
            _health = state
        self._respond(200, f"health={state}".encode())

    def _handle_recommendations(self, query):
        user_id = query.get("user_id", ["anon"])[0]
        with _lock:
            health = _health

        if health == "down":
            self._respond(503, b"servicio caido")
            return

        if health == "slow":
            time.sleep(3.0)  # mas lento que cualquier timeout razonable del cliente

        items = _CATALOG.get(user_id, _DEFAULT_ITEMS)
        body = json.dumps({"user_id": user_id, "items": items}).encode()
        self._respond(200, body)

    def _respond(self, status: int, body: bytes):
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # el cliente ya se rindio por timeout

    def log_message(self, format, *args):
        pass  # silencia el logging por defecto de cada request


def start_server(host="localhost", port=8768):
    return ThreadingHTTPServer((host, port), RecommendationsHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicio de recomendaciones escuchando en http://{addr[0]}:{addr[1]}")
    print("GET /recommendations?user_id=alice")
    print("GET /admin/health?state=healthy|slow|down")
    print("Ctrl+C para detener")
    server.serve_forever()
