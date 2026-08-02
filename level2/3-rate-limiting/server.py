"""Endpoint HTTP protegido por rate limiting (token bucket).

GET /api/resource -> 200 si hay tokens disponibles; 429 con header
`Retry-After` si el limite ya se alcanzo.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rate_limiters import TokenBucketLimiter

_lock = threading.Lock()
_limiter = TokenBucketLimiter(rate=5.0, capacity=5.0)
_start_time = time.monotonic()


class RateLimitedHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/resource":
            self._respond(404, {"error": "not found"})
            return

        now = time.monotonic() - _start_time
        with _lock:
            allowed = _limiter.allow_request(now)
            tokens_left = _limiter.tokens

        if allowed:
            self._respond(200, {"status": "ok", "tokens_restantes": round(tokens_left, 2)})
            return

        retry_after = max(0.0, (1.0 - tokens_left) / _limiter.rate)
        self._respond(
            429,
            {"error": "rate limit excedido", "retry_after_s": round(retry_after, 2)},
            extra_headers={"Retry-After": str(round(retry_after, 2))},
        )

    def _respond(self, status: int, payload: dict, extra_headers: dict | None = None):
        body = json.dumps(payload).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        pass  # silencia el logging por defecto de cada request


def start_server(host="localhost", port=8771):
    return ThreadingHTTPServer((host, port), RateLimitedHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicio con rate limiting escuchando en http://{addr[0]}:{addr[1]}")
    print("GET /api/resource")
    print("Ctrl+C para detener")
    server.serve_forever()
