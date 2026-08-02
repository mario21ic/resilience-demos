"""Endpoint HTTP protegido por load shedding con prioridades.

GET /api/work?priority=critical|default|sheddable
  -> si hay capacidad para esa prioridad, "trabaja" 1s y responde 200.
  -> si no, responde 503 de inmediato (sin esperar nada).
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from load_shedder import LoadShedder

_shedder = LoadShedder(capacity=10)
_WORK_DURATION_S = 1.0


class LoadSheddingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/work":
            self._respond(404, {"error": "not found"})
            return

        query = parse_qs(parsed.query)
        priority = query.get("priority", ["default"])[0]

        if not _shedder.try_admit(priority):
            self._respond(
                503,
                {
                    "error": "sistema sobrecargado",
                    "priority": priority,
                    "in_flight": _shedder.in_flight,
                    "capacity": _shedder.capacity,
                },
            )
            return

        try:
            time.sleep(_WORK_DURATION_S)  # simula el trabajo real de atender el request
            self._respond(200, {"status": "ok", "priority": priority})
        finally:
            _shedder.release()

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


def start_server(host="localhost", port=8773):
    return ThreadingHTTPServer((host, port), LoadSheddingHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicio con load shedding escuchando en http://{addr[0]}:{addr[1]}")
    print("GET /api/work?priority=critical|default|sheddable")
    print("Ctrl+C para detener")
    server.serve_forever()
