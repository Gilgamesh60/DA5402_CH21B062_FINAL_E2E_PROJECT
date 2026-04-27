#!/bin/bash
# Capture CLI proofs for the walkthrough doc. Writes each command's output
# as a separate text file that the walkthrough embeds as code blocks.

set -e

OUT=docs/screenshots/cli
mkdir -p "$OUT"

echo "Capturing CLI proofs…"

# docker ps
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" > "$OUT/docker_ps.txt"
echo "  ✓ docker_ps.txt"

# git log
git -P log --oneline -n 15 > "$OUT/git_log.txt"
echo "  ✓ git_log.txt"

# dvc DAG
source .venv/bin/activate
dvc dag --outs > "$OUT/dvc_dag_outs.txt" 2>&1 || true
dvc dag > "$OUT/dvc_dag.txt" 2>&1 || true
echo "  ✓ dvc_dag.txt"

# dvc metrics
dvc metrics show > "$OUT/dvc_metrics.txt" 2>&1 || true
echo "  ✓ dvc_metrics.txt"

# git lfs tracked patterns
git lfs track > "$OUT/git_lfs.txt" 2>&1 || true
echo "  ✓ git_lfs.txt"

# Prediction via API
curl -sS -m 10 -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}' \
  | python3 -m json.tool > "$OUT/api_predict.txt" 2>&1
echo "  ✓ api_predict.txt"

# Model info
curl -sS -m 5 http://localhost:8000/model/info \
  | python3 -m json.tool > "$OUT/api_model_info.txt" 2>&1
echo "  ✓ api_model_info.txt"

# Registry versions
curl -sS -m 5 http://localhost:8000/model/versions \
  | python3 -m json.tool > "$OUT/api_model_versions.txt" 2>&1
echo "  ✓ api_model_versions.txt"

# Prometheus metrics head
curl -sS -m 5 http://localhost:8000/metrics \
  | grep -E "^(http_requests_total|predictions_total|model_version_info|feedback_received_total|feature_drift|drift_detected)" \
  | head -20 > "$OUT/prometheus_metrics.txt" 2>&1 || true
echo "  ✓ prometheus_metrics.txt"

# Prometheus targets
curl -sS -m 5 'http://localhost:9090/api/v1/targets?state=active' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f\"{t['labels']['job']:15} {t['scrapeUrl']:50} {t['health']}\") for t in d['data']['activeTargets']]" \
  > "$OUT/prometheus_targets.txt" 2>&1
echo "  ✓ prometheus_targets.txt"

# Feedback row
docker exec stock-sentiment-mlops-postgres-1 \
  psql -U mlops -d mlops -c "SELECT ticker, true_label, predicted_label FROM feedback ORDER BY received_at DESC LIMIT 5;" \
  > "$OUT/postgres_feedback.txt" 2>&1
echo "  ✓ postgres_feedback.txt"

# Test report summary
head -40 docs/test-report.md > "$OUT/test_report_head.txt"
echo "  ✓ test_report_head.txt"

echo ""
echo "done — CLI proofs in $OUT/"
