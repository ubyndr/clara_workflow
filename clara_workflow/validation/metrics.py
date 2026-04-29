"""Per-assertion and term-level metrics against the CLARA gold standard.

Verdicts are kept three-way (pass / fail / uncertain). Callers that need
a binary comparison against a binary CLARA export should collapse
`uncertain` before calling in — doing it here would hide the choice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sklearn.metrics import (
    cohen_kappa_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from clara_workflow.validation.schema import VERDICTS


@dataclass
class AssertionMetrics:
    n: int
    n_scored: int
    accuracy: float
    cohen_kappa: float
    per_class: pd.DataFrame
    confusion: pd.DataFrame
    coverage: dict[str, int] = field(default_factory=dict)
    cost_usd_total: float | None = None
    latency_ms_mean: float | None = None


@dataclass
class TermMetrics:
    per_term: pd.DataFrame
    term_flag_agreement: float
    failed_assertion_jaccard_mean: float


def _scored_rows(joined: pd.DataFrame) -> pd.DataFrame:
    return joined[joined["_merge"] == "both"].copy()


def _coverage(joined: pd.DataFrame) -> dict[str, int]:
    counts = joined["_merge"].value_counts().to_dict()
    return {
        "matched": int(counts.get("both", 0)),
        "gold_only": int(counts.get("left_only", 0)),
        "pred_only": int(counts.get("right_only", 0)),
    }


def assertion_level(joined: pd.DataFrame) -> AssertionMetrics:
    coverage = _coverage(joined)
    scored = _scored_rows(joined)
    n_scored = len(scored)

    if n_scored == 0:
        empty = pd.DataFrame(index=list(VERDICTS))
        return AssertionMetrics(
            n=len(joined),
            n_scored=0,
            accuracy=float("nan"),
            cohen_kappa=float("nan"),
            per_class=empty,
            confusion=pd.DataFrame(index=list(VERDICTS), columns=list(VERDICTS)),
            coverage=coverage,
        )

    y_true = scored["gold_verdict"].astype(str).to_numpy()
    y_pred = scored["verdict"].astype(str).to_numpy()
    labels = list(VERDICTS)

    accuracy = float((y_true == y_pred).mean())
    kappa = float(cohen_kappa_score(y_true, y_pred, labels=labels))

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_class = pd.DataFrame(
        {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        },
        index=labels,
    )

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    confusion = pd.DataFrame(cm, index=labels, columns=labels)
    confusion.index.name = "gold"
    confusion.columns.name = "pred"

    cost_total: float | None = None
    latency_mean: float | None = None
    if "cost_usd" in scored.columns:
        cost_total = float(scored["cost_usd"].sum(skipna=True))
    if "latency_ms" in scored.columns:
        latency_mean = float(scored["latency_ms"].mean(skipna=True))

    return AssertionMetrics(
        n=len(joined),
        n_scored=n_scored,
        accuracy=accuracy,
        cohen_kappa=kappa,
        per_class=per_class,
        confusion=confusion,
        coverage=coverage,
        cost_usd_total=cost_total,
        latency_ms_mean=latency_mean,
    )


def _term_row(group: pd.DataFrame) -> dict[str, Any]:
    gold_failed = set(group.loc[group["gold_verdict"] == "fail", "assertion_id"])
    pred_failed = set(group.loc[group["verdict"] == "fail", "assertion_id"])
    union = gold_failed | pred_failed
    jaccard = len(gold_failed & pred_failed) / len(union) if union else 1.0
    return {
        "n_assertions": len(group),
        "gold_flagged": bool(gold_failed),
        "pred_flagged": bool(pred_failed),
        "failed_assertion_jaccard": jaccard,
        "accuracy": float((group["gold_verdict"] == group["verdict"]).mean()),
    }


def term_level(joined: pd.DataFrame, core_only: bool = True) -> TermMetrics:
    scored = _scored_rows(joined)
    if core_only and "category" in scored.columns:
        scored = scored[scored["category"] == "core"]
    if scored.empty:
        return TermMetrics(
            per_term=pd.DataFrame(),
            term_flag_agreement=float("nan"),
            failed_assertion_jaccard_mean=float("nan"),
        )

    rows = {
        term_id: _term_row(group)
        for term_id, group in scored.groupby("term_id", sort=True)
    }
    per_term = pd.DataFrame.from_dict(rows, orient="index")
    per_term.index.name = "term_id"

    flag_agreement = float(
        (per_term["gold_flagged"] == per_term["pred_flagged"]).mean()
    )
    jaccard_mean = float(per_term["failed_assertion_jaccard"].mean())
    return TermMetrics(
        per_term=per_term,
        term_flag_agreement=flag_agreement,
        failed_assertion_jaccard_mean=jaccard_mean,
    )
