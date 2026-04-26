FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
        fastapi==0.109.2 \
        "uvicorn[standard]==0.27.1" \
        httpx==0.26.0 \
        prometheus-client==0.19.0 \
        structlog==24.1.0 \
        pydantic==2.6.1 \
        pydantic-settings==2.1.0

COPY src/ssa_api /app/ssa_api

EXPOSE 8000

CMD ["uvicorn", "ssa_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
