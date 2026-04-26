FROM python:3.10-slim

RUN pip install --no-cache-dir \
        mlflow==2.10.2 \
        psycopg2-binary==2.9.9 \
        boto3==1.34.42

EXPOSE 5000

ENTRYPOINT ["sh", "-c", "mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} \
    --default-artifact-root ${MLFLOW_DEFAULT_ARTIFACT_ROOT} \
    --serve-artifacts"]
