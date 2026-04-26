#!/bin/sh
# Write /usr/share/nginx/html/config.js from runtime env vars so the
# frontend can discover service URLs without a rebuild. This is what
# makes the "configurable REST" requirement mechanical.

set -e

TARGET=/usr/share/nginx/html/config.js

cat > "$TARGET" <<EOF
window.SSA_CONFIG = {
  apiBaseUrl: "${VITE_API_BASE_URL:-/api}",
  mlflowUrl: "${MLFLOW_URL:-http://localhost:5000}",
  airflowUrl: "${AIRFLOW_URL:-http://localhost:8080}",
  grafanaUrl: "${GRAFANA_URL:-http://localhost:3001}",
  prometheusUrl: "${PROMETHEUS_URL:-http://localhost:9090}"
};
EOF

echo "[ssa-config] wrote $TARGET"
