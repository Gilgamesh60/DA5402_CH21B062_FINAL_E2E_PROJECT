# Tiny HTTP server that exposes whatever `.prom` file is in /metrics/
# under the path `/metrics`. Prometheus scrapes this service like any
# other. Drift jobs (run by Airflow) write the file.

FROM python:3.11-slim

WORKDIR /app

COPY docker/drift-exporter/server.py /app/server.py

EXPOSE 9101

CMD ["python", "/app/server.py"]
