# Phase 1 stub: a tiny FastAPI app that mimics the MLflow models-serve
# contract (/health, /invocations). Phase 4 replaces the entry command
# with `mlflow models serve -m models:/stock-sentiment/Production`
# without touching the rest of the stack.

FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
        fastapi==0.109.2 \
        "uvicorn[standard]==0.27.1" \
        pydantic==2.6.1

COPY docker/model-server/stub_server.py /app/stub_server.py

EXPOSE 5001

CMD ["uvicorn", "stub_server:app", "--host", "0.0.0.0", "--port", "5001"]
