FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
        fastapi==0.119.0 \
        "uvicorn[standard]==0.37.0" \
        httpx==0.28.1 \
        prometheus-client==0.22.0 \
        structlog==25.5.0 \
        pydantic==2.13.3 \
        pydantic-settings==2.12.0 \
        mlflow-skinny==3.11.1 \
        psycopg2-binary==2.9.10 \
        pandas==2.2.3 \
        pyarrow==16.1.0

COPY src/ssa_api /app/ssa_api

EXPOSE 8000

CMD ["uvicorn", "ssa_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
