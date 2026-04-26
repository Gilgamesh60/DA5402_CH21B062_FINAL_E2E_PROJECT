"""Tiny Prometheus textfile exposer.

Serves whatever lives in `/metrics/drift_metrics.prom` at `/metrics`.
If the file is missing, serves an empty body (still 200) — Prometheus
will continue scraping and pick up the file once the first drift job
has written it.
"""

from __future__ import annotations

import http.server
import pathlib
import socketserver

METRICS_FILE = pathlib.Path("/metrics/drift_metrics.prom")
PORT = 9101


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler interface
        if self.path == "/metrics":
            body = METRICS_FILE.read_bytes() if METRICS_FILE.exists() else b""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/health", "/healthz"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        # Silence the default per-request stdout log.
        return


def main() -> None:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
