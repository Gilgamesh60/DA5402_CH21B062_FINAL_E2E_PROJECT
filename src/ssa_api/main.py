"""FastAPI gateway — Phase 5 implementation of the LLD contract.

Routes implemented:
    /health, /ready, /metrics
    /model/info, /model/versions, /model/rollback
    /predict, /batch_predict
    /feedback

The gateway forwards inference requests to the MLflow-served model on
`model-server:5001`. It never loads model weights itself. This keeps
the three-container topology (frontend / api / model-server) clean and
satisfies the "MLflow API-ification" rubric item.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

import mlflow
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from mlflow.tracking import MlflowClient
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

from ssa_api.config import settings
from ssa_api.inference import (
    aggregate,
    predict_for_texts,
    summarise_class_counts,
)
from ssa_api.middleware import RequestContextMiddleware
from ssa_api.model_client import ModelClient
from ssa_api.repo import FeedbackRepo, PredictionRepo, RecordRepo
from ssa_api.schemas import (
    BatchItem,
    BatchPredictRequest,
    BatchPredictResponse,
    ErrorCode,
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    ModelInfo,
    ModelRef,
    NotReadyResponse,
    PredictRequest,
    PredictResponse,
    ReadyResponse,
    RollbackRequest,
    RollbackResponse,
    VersionsResponse,
    VersionSummary,
)

logger = structlog.get_logger()

# --- Business-level metrics ---------------------------------------------------
PREDICTIONS = Counter(
    "predictions_total",
    "Sentiment predictions emitted, by aggregated label",
    ["sentiment"],
)
MODEL_VERSION_GAUGE = Gauge(
    "model_version_info",
    "1 if this API is currently serving model `version` in `stage`",
    ["version", "stage"],
)
FEEDBACK_RECEIVED = Counter(
    "feedback_received_total",
    "Feedback events received by label",
    ["label"],
)


# --- App lifecycle ------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.model_client = ModelClient(settings.model_server_url)
    app.state.records = RecordRepo()
    app.state.feedback = FeedbackRepo(settings.postgres_dsn)
    app.state.predictions = PredictionRepo(settings.postgres_dsn)
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    app.state.mlflow = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
    logger.info(
        "api_started",
        model_server_url=settings.model_server_url,
        mlflow_uri=settings.mlflow_tracking_uri,
    )
    try:
        yield
    finally:
        await app.state.model_client.aclose()


app = FastAPI(
    title="Stock Sentiment API",
    version="0.5.0",
    description="Phase 5 gateway implementing the LLD contract.",
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)


# --- Global exception handling -----------------------------------------------
@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error="validation failed",
            code=ErrorCode.INVALID_TICKER,
            request_id=getattr(request.state, "request_id", "unknown"),
            details={"errors": exc.errors()},
        ).model_dump(mode="json"),
    )


@app.exception_handler(HTTPException)
async def _http_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = ErrorCode.INTERNAL
    if exc.status_code == 400:
        code = ErrorCode.INVALID_TICKER
    elif exc.status_code == 404:
        code = ErrorCode.NO_DATA
    elif exc.status_code == 503:
        code = ErrorCode.MODEL_UNAVAILABLE
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(exc.detail),
            code=code,
            request_id=getattr(request.state, "request_id", "unknown"),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal server error",
            code=ErrorCode.INTERNAL,
            request_id=getattr(request.state, "request_id", "unknown"),
        ).model_dump(mode="json"),
    )


# --- Dependencies -------------------------------------------------------------
def get_model_client(request: Request) -> ModelClient:
    return request.app.state.model_client


def get_records(request: Request) -> RecordRepo:
    return request.app.state.records


def get_feedback(request: Request) -> FeedbackRepo:
    return request.app.state.feedback


def get_predictions(request: Request) -> PredictionRepo:
    return request.app.state.predictions


def get_mlflow(request: Request) -> MlflowClient:
    return request.app.state.mlflow


# --- Helper: current Production version ---------------------------------------
_PROD_REF_CACHE: dict[str, tuple[float, ModelRef | None]] = {}
_PROD_REF_TTL_SECONDS = 5.0


def _current_production_ref(client: MlflowClient) -> ModelRef | None:
    """Look up (and briefly cache) the current Production model.

    Registry lookups are MLflow-bound; caching for 5 seconds keeps
    /predict p95 latency well under SLO without masking rollbacks.
    """
    cache_key = settings.registry_model_name
    now = time.time()
    cached = _PROD_REF_CACHE.get(cache_key)
    if cached and now - cached[0] < _PROD_REF_TTL_SECONDS:
        return cached[1]
    versions = client.get_latest_versions(name=cache_key, stages=["Production"])
    ref = None
    if versions:
        v = versions[0]
        ref = ModelRef(name=v.name, version=v.version, stage=v.current_stage)
    _PROD_REF_CACHE[cache_key] = (now, ref)
    return ref


# --- Probes -------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def _root() -> dict[str, str]:
    return {"service": "stock-sentiment-api", "version": app.version, "docs": "/docs"}


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="alive")


@app.get("/ready", responses={503: {"model": NotReadyResponse}})
async def ready(
    client: ModelClient = Depends(get_model_client),
    mlf: MlflowClient = Depends(get_mlflow),
):
    if not await client.health():
        return JSONResponse(
            status_code=503,
            content=NotReadyResponse(
                status="not_ready", reason="model_server_unreachable"
            ).model_dump(),
        )
    ref = _current_production_ref(mlf)
    if ref is None:
        return JSONResponse(
            status_code=503,
            content=NotReadyResponse(
                status="not_ready", reason="no_production_model"
            ).model_dump(),
        )
    MODEL_VERSION_GAUGE.labels(version=ref.version, stage=ref.stage).set(1)
    return ReadyResponse(status="ready", model=ref)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- Model introspection ------------------------------------------------------
@app.get("/model/info", response_model=ModelInfo)
async def model_info(mlf: MlflowClient = Depends(get_mlflow)) -> ModelInfo:
    ref = _current_production_ref(mlf)
    if ref is None:
        raise HTTPException(status_code=503, detail="no production model")
    # Pull run-level metadata for the viva
    mv = mlf.get_model_version(name=ref.name, version=ref.version)
    run = mlf.get_run(mv.run_id) if mv.run_id else None
    tags = run.data.tags if run else {}
    params = run.data.params if run else {}
    # Try both tag + param names for the DVC data hash (we stamp it via
    # the reproducibility context artifact which gets uploaded, but we
    # also now log it directly as a param so it's cheap to surface here).
    data_hash = (
        tags.get("dvc.data_hash")
        or params.get("dvc_data_hash")
        or params.get("data_hash")
    )
    return ModelInfo(
        name=ref.name,
        version=ref.version,
        stage=ref.stage,
        git_commit_sha=tags.get("git.commit_sha"),
        mlflow_run_id=mv.run_id,
        data_hash=data_hash,
        trained_at=datetime.fromtimestamp(mv.creation_timestamp / 1000)
        if mv.creation_timestamp
        else None,
    )


@app.get("/model/versions", response_model=VersionsResponse)
async def list_versions(mlf: MlflowClient = Depends(get_mlflow)) -> VersionsResponse:
    mvs = mlf.search_model_versions(f"name='{settings.registry_model_name}'")
    out: list[VersionSummary] = []
    for mv in sorted(mvs, key=lambda x: int(x.version), reverse=True):
        macro_f1 = None
        if mv.run_id:
            try:
                run = mlf.get_run(mv.run_id)
                macro_f1 = run.data.metrics.get("test_macro_f1") or run.data.metrics.get(
                    "val_macro_f1"
                )
            except Exception:
                pass
        out.append(
            VersionSummary(
                version=mv.version,
                stage=mv.current_stage,
                trained_at=datetime.fromtimestamp(mv.creation_timestamp / 1000)
                if mv.creation_timestamp
                else None,
                macro_f1=macro_f1,
            )
        )
    return VersionsResponse(versions=out)


@app.post("/model/rollback", response_model=RollbackResponse)
async def rollback(
    body: RollbackRequest,
    request: Request,
    mlf: MlflowClient = Depends(get_mlflow),
) -> RollbackResponse:
    # Restrict to local clients so random external callers can't flip prod.
    client_host = (request.client.host if request.client else "") or ""
    allowed = tuple(settings.rollback_allowed_prefixes.split(","))
    if not any(client_host.startswith(p) for p in allowed):
        raise HTTPException(status_code=403, detail="rollback restricted to local network")

    # Validate target exists
    try:
        mv = mlf.get_model_version(name=settings.registry_model_name, version=body.target_version)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"version {body.target_version} not found") from e

    previous = _current_production_ref(mlf)
    if previous and previous.version == body.target_version:
        raise HTTPException(status_code=409, detail="target is already Production")

    # Transition atomically
    new = mlf.transition_model_version_stage(
        name=settings.registry_model_name,
        version=body.target_version,
        stage="Production",
        archive_existing_versions=True,
    )
    logger.info(
        "rollback_triggered",
        previous=previous.version if previous else None,
        new=new.version,
    )
    # The model-server is restarted by operators or the CI rollback workflow;
    # the API doesn't have docker socket access, so we only flag the intent.
    return RollbackResponse(
        previous=previous or ModelRef(name=settings.registry_model_name, version="", stage=""),
        current=ModelRef(name=new.name, version=new.version, stage=new.current_stage),
        reload_triggered=False,
    )


# --- Predictions --------------------------------------------------------------
async def _predict_one(
    ticker: str,
    lookback_hours: int,
    include_explanations: bool,
    records: RecordRepo,
    client: ModelClient,
) -> tuple[PredictResponse | None, str | None]:
    rows = records.recent(ticker, lookback_hours)
    if not rows:
        return None, ErrorCode.NO_DATA.value
    texts = [r.get("text_clean") or r.get("text") or "" for r in rows]
    try:
        preds = await predict_for_texts(client, texts)
    except Exception as e:
        logger.warning("model_invocation_failed", error=str(e))
        return None, ErrorCode.MODEL_UNAVAILABLE.value
    sentiment, confidence, scores, explanations = aggregate(
        preds, rows, include_explanations=include_explanations
    )
    for lbl, n in summarise_class_counts(preds).items():
        PREDICTIONS.labels(sentiment=lbl).inc(n)

    return (
        PredictResponse(
            ticker=ticker,
            sentiment=sentiment,
            confidence=confidence,
            scores=scores,
            sample_size=len(rows),
            lookback_hours=lookback_hours,
            model=ModelRef(name="", version="", stage=""),  # filled in by caller
            explanations=explanations,
            request_id="",  # filled in by caller
            latency_ms=0,  # filled in by caller
        ),
        None,
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(
    body: PredictRequest,
    request: Request,
    records: RecordRepo = Depends(get_records),
    client: ModelClient = Depends(get_model_client),
    mlf: MlflowClient = Depends(get_mlflow),
    predictions_repo: PredictionRepo = Depends(get_predictions),
) -> PredictResponse:
    t0 = time.perf_counter()
    ref = _current_production_ref(mlf)
    if ref is None:
        raise HTTPException(status_code=503, detail="no production model")

    resp, err = await _predict_one(
        body.ticker, body.lookback_hours, body.include_explanations, records, client
    )
    if err == ErrorCode.NO_DATA.value:
        raise HTTPException(status_code=404, detail=f"no data for {body.ticker}")
    if err == ErrorCode.MODEL_UNAVAILABLE.value or resp is None:
        raise HTTPException(status_code=503, detail="model server unavailable")

    resp.model = ref
    resp.request_id = request.state.request_id
    resp.latency_ms = int((time.perf_counter() - t0) * 1000)

    # Log for feedback-join in Phase 9 retraining
    predictions_repo.insert(
        prediction_request_id=resp.request_id,
        ticker=resp.ticker,
        predicted_label=resp.sentiment.value,
        confidence=resp.confidence,
        model_version=ref.version,
        model_stage=ref.stage,
        sample_size=resp.sample_size,
        lookback_hours=resp.lookback_hours,
        latency_ms=resp.latency_ms,
    )
    return resp


@app.post("/batch_predict", response_model=BatchPredictResponse)
async def batch_predict(
    body: BatchPredictRequest,
    request: Request,
    records: RecordRepo = Depends(get_records),
    client: ModelClient = Depends(get_model_client),
    mlf: MlflowClient = Depends(get_mlflow),
) -> BatchPredictResponse:
    t0 = time.perf_counter()
    ref = _current_production_ref(mlf)
    if ref is None:
        raise HTTPException(status_code=503, detail="no production model")

    out: list[BatchItem] = []
    for ticker in body.tickers:
        resp, err = await _predict_one(ticker, body.lookback_hours, False, records, client)
        if resp is not None:
            out.append(
                BatchItem(
                    ticker=ticker,
                    sentiment=resp.sentiment,
                    confidence=resp.confidence,
                    scores=resp.scores,
                    sample_size=resp.sample_size,
                )
            )
        else:
            out.append(
                BatchItem(
                    ticker=ticker,
                    error={
                        "code": err or ErrorCode.INTERNAL.value,
                        "message": f"failed to predict for {ticker}",
                    },
                )
            )
    return BatchPredictResponse(
        results=out,
        model=ref,
        request_id=request.state.request_id,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )


# --- Feedback -----------------------------------------------------------------
@app.post("/feedback", status_code=202, response_model=FeedbackResponse)
async def feedback(
    body: FeedbackRequest,
    repo: FeedbackRepo = Depends(get_feedback),
) -> FeedbackResponse:
    # Look up the predicted label so real-world accuracy can be computed
    # without a follow-up join every time. Best-effort — if the lookup
    # fails (e.g. prediction came from before Phase 9), we still accept
    # the feedback and leave predicted_label NULL.
    predicted = None
    try:
        import psycopg2

        with psycopg2.connect(settings.postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT predicted_label FROM predictions WHERE prediction_request_id = %s",
                    (str(body.prediction_request_id),),
                )
                row = cur.fetchone()
                if row:
                    predicted = row[0]
    except Exception as e:
        logger.warning("feedback_join_failed", error=str(e))

    try:
        feedback_id = repo.insert(
            ticker=body.ticker,
            prediction_request_id=body.prediction_request_id,
            true_label=body.true_label.value,
            predicted_label=predicted,
            user_comment=body.user_comment,
        )
    except Exception as e:
        logger.warning("feedback_insert_failed", error=str(e))
        raise HTTPException(status_code=500, detail="failed to record feedback") from e
    FEEDBACK_RECEIVED.labels(label=body.true_label.value).inc()
    return FeedbackResponse(accepted=True, feedback_id=feedback_id)
