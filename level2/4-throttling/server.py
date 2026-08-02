"""Endpoint HTTP con throttling real (leaky bucket).

GET /api/resource -> agenda el request en la cola; si hay lugar,
espera lo que le toque y responde 200. Si la cola ya esta llena,
responde 503 de inmediato (sin esperar nada).
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from leaky_bucket import LeakyBucketThrottle, QueueFullError

_lock = threading.Lock()
_throttle = LeakyBucketThrottle(rate=5.0, max_queue_size=5)
_start_time = time.monotonic()


class ThrottledHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/resource":
            self._respond(404, {"error": "not found"})
            return

        now = time.monotonic() - _start_time
        with _lock:
            try:
                scheduled_at = _throttle.schedule(now)
            except QueueFullError as exc:
                self._respond(503, {"error": "cola llena", "detalle": str(exc)})
                return

        wait = max(0.0, scheduled_at - now)
        time.sleep(wait)  # el "encolado" se modela como esperar aca, fuera del lock
        self._respond(200, {"status": "ok", "esperado_s": round(wait, 2)})

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


def start_server(host="localhost", port=8772):
    return ThreadingHTTPServer((host, port), ThrottledHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicio con throttling escuchando en http://{addr[0]}:{addr[1]}")
    print("GET /api/resource")
    print("Ctrl+C para detener")
    server.serve_forever()
