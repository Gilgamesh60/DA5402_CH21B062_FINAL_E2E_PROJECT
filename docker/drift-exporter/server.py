"""Tiny Prometheus textfile exposer.

Serves the concatenation of every `*.prom` file in /metrics/ at
`/metrics`. Currently collects:
  - drift_metrics.prom      (from ssa_monitoring.drift)
  - feedback_metrics.prom   (from ssa_monitoring.feedback_metrics)

If a file is missing the exporter continues serving whatever is present.
"""

from __future__ import annotations

import http.server
import pathlib
import socketserver

METRICS_DIR = pathlib.Path("/metrics")
PORT = 9101


def _load_all() -> bytes:
    parts: list[bytes] = []
    if METRICS_DIR.exists():
        for f in sorted(METRICS_DIR.glob("*.prom")):
            try:
                body = f.read_bytes()
                if body:
                    parts.append(body)
                    if not body.endswith(b"\n"):
                        parts.append(b"\n")
            except OSError:
                continue
    return b"".join(parts)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler interface
        if self.path == "/metrics":
            body = _load_all()
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
