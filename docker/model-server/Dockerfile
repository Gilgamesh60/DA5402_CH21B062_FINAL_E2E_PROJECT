# Phase 5: real model server. Runs `mlflow models serve` loading the
# currently-Production pyfunc from the registry. The pyfunc pickles
# reference `ssa_model.pyfunc_wrapper.SentimentPipeline` and the saved
# vectorizer was pickled under `ssa_features`, so both packages are
# copied into the image and added to PYTHONPATH.

FROM python:3.11-slim

RUN pip install --no-cache-dir \
        mlflow==3.11.1 \
        scikit-learn==1.8.0 \
        pandas==2.2.3 \
        joblib==1.5.3 \
        pyarrow==16.1.0 \
        structlog==25.5.0 \
        pydantic==2.13.3

# Copy the Python packages needed to rehydrate the pyfunc
COPY src/ssa_model /app/ssa_model
COPY src/ssa_features /app/ssa_features
ENV PYTHONPATH=/app

EXPOSE 5001

ENV MLFLOW_TRACKING_URI=http://mlflow:5000

CMD ["sh", "-c", "mlflow models serve \
    -m models:/stock-sentiment/Production \
    --host 0.0.0.0 --port 5001 --no-conda"]
