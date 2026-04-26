FROM python:3.11-slim

RUN pip install --no-cache-dir \
        mlflow==3.11.1 \
        psycopg2-binary==2.9.9 \
        boto3==1.34.42

EXPOSE 5000

# --serve-artifacts + --artifacts-destination makes the tracking server
# proxy artifact writes over HTTP. Clients get `mlflow-artifacts:/` URIs
# and upload via the server instead of trying to write to its filesystem
# directly. The default-artifact-root is set to the proxy URI so NEW
# experiments inherit the proxy path automatically.
ENTRYPOINT ["sh", "-c", "mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} \
    --artifacts-destination ${MLFLOW_DEFAULT_ARTIFACT_ROOT} \
    --default-artifact-root mlflow-artifacts:/ \
    --serve-artifacts"]
