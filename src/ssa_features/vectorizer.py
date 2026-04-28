"""Sklearn-compatible feature builder.

Wraps TF-IDF in a class that:
- Stamps the feature package version onto every saved artifact,
- Records vocabulary size + top-terms metadata for the viva,
- Serialises to a single `.joblib` file training loads.

If the team swaps TF-IDF for embeddings later, only this module changes;
the train + serve contracts stay intact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from ssa_features import __version__
from ssa_features.cleaning import CleaningConfig, clean_text


@dataclass
class VectorizerConfig:
    max_features: int = 20000
    ngram_range: tuple[int, int] = (1, 2)
    min_df: int = 2
    max_df: float = 0.95
    sublinear_tf: bool = True


class TextFeaturizer:
    """Clean + vectorize. The only thing training needs.

    Attributes populated after `fit`:
        vectorizer_: fitted TfidfVectorizer
        vocab_size_: int
        feature_package_version_: str
    """

    def __init__(
        self,
        cleaning: CleaningConfig | None = None,
        vectorizer: VectorizerConfig | None = None,
    ) -> None:
        self.cleaning = cleaning or CleaningConfig()
        self.vconfig = vectorizer or VectorizerConfig()
        self.vectorizer_: TfidfVectorizer | None = None
        self.vocab_size_: int = 0
        self.feature_package_version_: str = __version__

    def _clean_many(self, texts: list[str]) -> list[str]:
        return [clean_text(t, self.cleaning) for t in texts]

    def fit(self, texts: list[str]) -> "TextFeaturizer":
        cleaned = self._clean_many(texts)
        self.vectorizer_ = TfidfVectorizer(
            max_features=self.vconfig.max_features,
            ngram_range=tuple(self.vconfig.ngram_range),
            min_df=self.vconfig.min_df,
            max_df=self.vconfig.max_df,
            sublinear_tf=self.vconfig.sublinear_tf,
        )
        self.vectorizer_.fit(cleaned)
        self.vocab_size_ = len(self.vectorizer_.vocabulary_)
        return self

    def transform(self, texts: list[str]) -> csr_matrix:
        if self.vectorizer_ is None:
            raise RuntimeError("TextFeaturizer.transform called before fit")
        return self.vectorizer_.transform(self._clean_many(texts))

    def fit_transform(self, texts: list[str]) -> csr_matrix:
        self.fit(texts)
        return self.transform(texts)

    def feature_names(self) -> np.ndarray:
        if self.vectorizer_ is None:
            raise RuntimeError("feature_names called before fit")
        return self.vectorizer_.get_feature_names_out()

    # ---------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------
    def save(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, p)

    @classmethod
    def load(cls, path: Path | str) -> "TextFeaturizer":
        obj = joblib.load(Path(path))
        if not isinstance(obj, cls):
            raise TypeError(f"expected {cls.__name__}, got {type(obj).__name__}")
        return obj

    # ---------------------------------------------------------------
    # Introspection — used by training to log to MLflow
    # ---------------------------------------------------------------
    def metadata(self) -> dict[str, Any]:
        return {
            "feature_package_version": self.feature_package_version_,
            "vocab_size": self.vocab_size_,
            "vectorizer": {
                "max_features": self.vconfig.max_features,
                "ngram_range": list(self.vconfig.ngram_range),
                "min_df": self.vconfig.min_df,
                "max_df": self.vconfig.max_df,
                "sublinear_tf": self.vconfig.sublinear_tf,
            },
            "cleaning": {
                "lowercase": self.cleaning.lowercase,
                "remove_urls": self.cleaning.remove_urls,
                "preserve_cashtags": self.cleaning.preserve_cashtags,
                "remove_mentions": self.cleaning.remove_mentions,
                "normalize_unicode": self.cleaning.normalize_unicode,
                "collapse_whitespace": self.cleaning.collapse_whitespace,
            },
        }
