"""Feature pipeline entry point.

Reads validated records, produces a stratified train/val/test split,
fits the TextFeaturizer on train only, transforms all three splits,
and writes everything to `data/processed/`.

Outputs (all DVC-tracked):
    data/processed/train.parquet  -- cleaned text + label + ticker + timestamp
    data/processed/val.parquet
    data/processed/test.parquet
    artifacts/vectorizer.joblib   -- fitted TextFeaturizer
    artifacts/feature_report.json -- vocab size, split sizes, feature version
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog
from sklearn.model_selection import train_test_split

from ssa_features import __version__
from ssa_features.cleaning import clean_text
from ssa_features.config import FeatureConfig
from ssa_features.vectorizer import TextFeaturizer

logger = structlog.get_logger()

PROCESSED_DIR = Path("data/processed")
VECTORIZER_OUT = Path("artifacts/vectorizer.joblib")
REPORT_OUT = Path("artifacts/feature_report.json")


def _split(df: pd.DataFrame, cfg: FeatureConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Stratified 3-way split on label.

    With tiny classes the stratifier throws, so fall back to non-stratified.
    """
    strat = df["label"] if "label" in df and df["label"].nunique() > 1 else None
    train_df, temp = train_test_split(
        df,
        test_size=cfg.test_size + cfg.val_size,
        random_state=cfg.random_seed,
        stratify=strat,
    )
    # Proportion of val within the held-out block
    rel_val = cfg.val_size / max(cfg.val_size + cfg.test_size, 1e-9)
    strat2 = temp["label"] if "label" in temp and temp["label"].nunique() > 1 else None
    val_df, test_df = train_test_split(
        temp,
        test_size=1 - rel_val,
        random_state=cfg.random_seed,
        stratify=strat2,
    )
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


def run(
    input_path: Path | str = "data/interim/validated.parquet",
    output_dir: Path | str = PROCESSED_DIR,
    vectorizer_path: Path | str = VECTORIZER_OUT,
    report_path: Path | str = REPORT_OUT,
    config_path: Path | str = "params.yaml",
) -> dict:
    cfg = FeatureConfig.from_file(config_path)
    df = pd.read_parquet(input_path)
    if df.empty:
        raise RuntimeError("features called on empty dataframe")
    if "label" not in df.columns or df["label"].isna().all():
        raise RuntimeError("labelled data required for supervised feature pipeline")

    # Only keep labelled rows for the initial supervised pipeline
    labelled = df[df["label"].notna()].reset_index(drop=True)
    logger.info("feature_input", total=len(df), labelled=len(labelled))

    train_df, val_df, test_df = _split(labelled, cfg)

    # Clean text up-front so the persisted splits carry the exact text
    # the vectorizer was fitted against. Avoids clean-at-serve-time drift.
    for part in (train_df, val_df, test_df):
        part["text_clean"] = part["text"].astype(str).map(
            lambda t: clean_text(t, cfg.cleaning)
        )

    # Fit on train only — no leakage
    featurizer = TextFeaturizer(cleaning=cfg.cleaning, vectorizer=cfg.vectorizer)
    featurizer.fit(train_df["text"].tolist())

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    keep_cols = ["id", "ticker", "timestamp", "label", "text", "text_clean"]
    train_df[keep_cols].to_parquet(output_dir / "train.parquet", index=False)
    val_df[keep_cols].to_parquet(output_dir / "val.parquet", index=False)
    test_df[keep_cols].to_parquet(output_dir / "test.parquet", index=False)

    featurizer.save(vectorizer_path)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feature_package_version": __version__,
        "splits": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
        },
        "class_balance": {
            part_name: (
                df_part["label"].value_counts(normalize=True).round(4).to_dict()
                if "label" in df_part
                else {}
            )
            for part_name, df_part in [
                ("train", train_df),
                ("val", val_df),
                ("test", test_df),
            ]
        },
        "featurizer": featurizer.metadata(),
        "top_terms_sample": featurizer.feature_names()[:20].tolist(),
        "config": {
            "test_size": cfg.test_size,
            "val_size": cfg.val_size,
            "random_seed": cfg.random_seed,
            "cleaning": asdict(cfg.cleaning),
        },
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info(
        "features_done",
        vocab_size=featurizer.vocab_size_,
        train=len(train_df),
        val=len(val_df),
        test=len(test_df),
    )
    return report


def _cli() -> None:
    p = argparse.ArgumentParser(description="Run the feature pipeline.")
    p.add_argument("--input", default="data/interim/validated.parquet")
    p.add_argument("--output-dir", default=str(PROCESSED_DIR))
    p.add_argument("--vectorizer", default=str(VECTORIZER_OUT))
    p.add_argument("--report", default=str(REPORT_OUT))
    p.add_argument("--config", default="params.yaml")
    args = p.parse_args()
    run(args.input, args.output_dir, args.vectorizer, args.report, args.config)


if __name__ == "__main__":
    _cli()
