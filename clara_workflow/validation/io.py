"""Stub loaders for gold-standard and prediction tables.

Accepts CSV or JSONL (one record per line). The real CLARA export
schema is not yet fixed — these loaders exist so the metrics layer can
be driven from a DataFrame today and repointed at the real format with
a small adapter later.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from clara_workflow.validation.schema import (
    REQUIRED_GOLD,
    REQUIRED_PRED,
    VERDICTS,
)


def _read(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    return pd.read_csv(path)


def _check(df: pd.DataFrame, required: tuple[str, ...], label: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def load_gold(path: str | Path) -> pd.DataFrame:
    df = _read(path)
    _check(df, REQUIRED_GOLD, "gold")
    bad = set(df["gold_verdict"].unique()) - set(VERDICTS)
    if bad:
        raise ValueError(f"gold_verdict has unknown values: {bad}")
    return df


def load_predictions(path: str | Path) -> pd.DataFrame:
    df = _read(path)
    _check(df, REQUIRED_PRED, "predictions")
    bad = set(df["verdict"].unique()) - set(VERDICTS)
    if bad:
        raise ValueError(f"verdict has unknown values: {bad}")
    return df


def join(gold: pd.DataFrame, preds: pd.DataFrame) -> pd.DataFrame:
    """Inner-join on (term_id, assertion_id).

    Rows missing from either side are reported via the `_merge` column so
    callers can audit coverage before scoring.
    """
    merged = gold.merge(
        preds,
        on=["term_id", "assertion_id"],
        how="outer",
        indicator=True,
    )
    return merged
