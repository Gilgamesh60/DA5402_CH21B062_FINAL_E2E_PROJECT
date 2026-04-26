"""Load feature params from the shared `params.yaml`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ssa_features.cleaning import CleaningConfig
from ssa_features.vectorizer import VectorizerConfig


@dataclass
class FeatureConfig:
    cleaning: CleaningConfig
    vectorizer: VectorizerConfig
    test_size: float = 0.2
    val_size: float = 0.1
    random_seed: int = 42

    @classmethod
    def from_file(cls, path: Path | str = "params.yaml") -> "FeatureConfig":
        with Path(path).open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh)
        feat = raw.get("features", {})
        train = raw.get("training", {})
        tc = feat.get("text_cleaning", {})
        vc = feat.get("vectorizer", {})
        return cls(
            cleaning=CleaningConfig(
                lowercase=bool(tc.get("lowercase", True)),
                remove_urls=bool(tc.get("remove_urls", True)),
                preserve_cashtags=bool(tc.get("preserve_cashtags", True)),
                remove_mentions=bool(tc.get("remove_mentions", True)),
            ),
            vectorizer=VectorizerConfig(
                max_features=int(vc.get("max_features", 20000)),
                ngram_range=tuple(vc.get("ngram_range", [1, 2])),
                min_df=int(vc.get("min_df", 2)),
                max_df=float(vc.get("max_df", 0.95)),
                sublinear_tf=bool(vc.get("sublinear_tf", True)),
            ),
            test_size=float(train.get("test_size", 0.2)),
            val_size=float(train.get("val_size", 0.1)),
            random_seed=int(train.get("random_seed", 42)),
        )
