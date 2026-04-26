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
#
# --allowed-hosts includes the compose service name so containers on the
# internal network can reach MLflow without tripping the DNS-rebinding
# defense in 3.x. Host-level clients use `localhost` which is default-allowed.
ENTRYPOINT ["sh", "-c", "mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} \
    --artifacts-destination ${MLFLOW_DEFAULT_ARTIFACT_ROOT} \
    --default-artifact-root mlflow-artifacts:/ \
    --allowed-hosts localhost,127.0.0.1,mlflow,mlflow:5000,*:5000,10.*,192.168.*,172.16.*,172.17.*,172.18.*,172.19.*,172.20.*,172.21.*,172.22.*,172.23.*,172.24.*,172.25.*,172.26.*,172.27.*,172.28.*,172.29.*,172.30.*,172.31.* \
    --serve-artifacts"]
