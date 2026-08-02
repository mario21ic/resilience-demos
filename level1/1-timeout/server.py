"""Servicio simulado con latencia configurable.

Actua como la dependencia "lenta" contra la que probamos el patron
de timeout en client_timeout.py.
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


class SlowServiceHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        delay = float(query.get("delay", ["0"])[0])

        time.sleep(delay)

        body = json.dumps({"delay_simulated": delay, "status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # silencia el logging por defecto de cada request


def start_server(host="localhost", port=8765):
    return ThreadingHTTPServer((host, port), SlowServiceHandler)


if __name__ == "__main__":
    server = start_server()
    addr = server.server_address
    print(f"Servicio lento escuchando en http://{addr[0]}:{addr[1]}")
    print("Prueba: /?delay=2  (espera 2 segundos antes de responder)")
    print("Ctrl+C para detener")
    server.serve_forever()
