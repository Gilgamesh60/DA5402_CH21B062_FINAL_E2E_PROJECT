# Pipeline performance

Throughput & latency measurements for the data engineering pipeline. Required by the rubric (Data Engineering rubric item: "What is the throughput and speed of the data engineering pipeline?") and displayed on the frontend pipeline-viz screen in Phase 7.

## Seed run (300 records, local, Colima aarch64, Python 3.14)

| Stage | Records | Duration | Throughput |
|---|---|---|---|
| ingest | 300 | 0.05–0.08 s | ~5800 rec/s |
| validate | 300 in / 300 out | <0.05 s | ~6000 rec/s |
| eda_baselines | 300 | <0.1 s | — |

Recorded in `artifacts/ingestion_report.json` at every run. DVC also tracks this as a metric so `dvc metrics show` surfaces it.

## Live runs

Populated in Phase 9 once NewsAPI + Reddit adapters are configured. Expected order-of-magnitude:
- NewsAPI: 50–100 articles / API call, rate-limited ~100 calls/day on free tier
- Reddit: 100 posts / subreddit / call, PRAW-managed rate limiting

## Bottlenecks

At seed scale, pandas `to_parquet` dominates. At live scale, HTTP latency from the external APIs will dominate — the pipeline is I/O-bound, not CPU-bound.

## Scaling levers

- Parallelise source fetches with `concurrent.futures.ThreadPoolExecutor` (HTTP I/O is trivially parallel)
- Switch ingestion output to partitioned parquet by date
- Move heavy feature computation from the ingestion DAG to a separate feature DAG (already the design)

None are needed at current scale.
