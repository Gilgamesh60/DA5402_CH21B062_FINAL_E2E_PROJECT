"""MLflow pyfunc wrapper for the bundled (vectorizer, classifier) pair.

Serving `mlflow models serve` with this wrapper means `/invocations`
accepts raw text. That keeps the API gateway thin: it only forwards
strings — it never needs to know about sparse matrices or vectorizers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import mlflow.pyfunc
import pandas as pd


class SentimentPipeline(mlflow.pyfunc.PythonModel):
    """Loads the joblib bundle and exposes a text→(label, scores) interface."""

    def load_context(self, context: Any) -> None:
        bundle_path = context.artifacts["bundle"]
        bundle = joblib.load(bundle_path)
        self._vectorizer = bundle["vectorizer"]
        self._classifier = bundle["classifier"]
        self._classes = list(self._classifier.classes_)

    def predict(
        self,
        context: Any,
        model_input: Any,
        params: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        texts = self._coerce_to_texts(model_input)
        X = self._vectorizer.transform(texts)
        labels = self._classifier.predict(X).tolist()
        probas = self._classifier.predict_proba(X).tolist()
        out: list[dict[str, Any]] = []
        for label, p in zip(labels, probas):
            scores = {cls: round(float(prob), 6) for cls, prob in zip(self._classes, p)}
            out.append(
                {
                    "sentiment": label,
                    "confidence": round(float(max(p)), 6),
                    "scores": scores,
                }
            )
        return out

    @staticmethod
    def _coerce_to_texts(model_input: Any) -> list[str]:
        # MLflow's scoring server wraps the request into a pandas DataFrame.
        # Each cell can be a raw str or a numpy scalar/array of length 1.
        import numpy as np

        def _to_str(v: Any) -> str:
            if isinstance(v, np.ndarray):
                # Single-element array — extract scalar
                if v.ndim == 0 or v.size == 1:
                    return str(v.item())
                return " ".join(str(x) for x in v.tolist())
            return str(v)

        if isinstance(model_input, pd.DataFrame):
            col = "text" if "text" in model_input.columns else model_input.columns[0]
            return [_to_str(v) for v in model_input[col].tolist()]
        if isinstance(model_input, list):
            if model_input and isinstance(model_input[0], dict):
                return [_to_str(d.get("text", "")) for d in model_input]
            return [_to_str(x) for x in model_input]
        if isinstance(model_input, dict):
            if "inputs" in model_input:
                return SentimentPipeline._coerce_to_texts(model_input["inputs"])
            if "text" in model_input:
                val = model_input["text"]
                if isinstance(val, list):
                    return [_to_str(x) for x in val]
                return [_to_str(val)]
        return [_to_str(model_input)]


def log_pyfunc_model(
    bundle_path: Path | str,
    artifact_name: str = "pyfunc_model",
    registered_model_name: str | None = None,
) -> str:
    """Log the pyfunc to the active MLflow run. Returns the model URI."""
    kwargs = dict(
        name=artifact_name,
        python_model=SentimentPipeline(),
        artifacts={"bundle": str(bundle_path)},
    )
    if registered_model_name:
        kwargs["registered_model_name"] = registered_model_name
    info = mlflow.pyfunc.log_model(**kwargs)
    return info.model_uri
