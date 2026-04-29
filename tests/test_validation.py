import pandas as pd
import pytest

from clara_workflow.validation import (
    assertion_level,
    join,
    term_level,
)
from clara_workflow.validation.io import load_gold, load_predictions


@pytest.fixture
def gold() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"term_id": "T1", "assertion_id": "A1", "assertion_text": "x", "gold_verdict": "pass"},
            {"term_id": "T1", "assertion_id": "A2", "assertion_text": "y", "gold_verdict": "fail"},
            {"term_id": "T2", "assertion_id": "A1", "assertion_text": "z", "gold_verdict": "pass"},
            {"term_id": "T2", "assertion_id": "A2", "assertion_text": "w", "gold_verdict": "fail"},
        ]
    )


@pytest.fixture
def preds() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"term_id": "T1", "assertion_id": "A1", "verdict": "pass", "evidence_quote": "...", "cost_usd": 0.01, "latency_ms": 120},
            {"term_id": "T1", "assertion_id": "A2", "verdict": "fail", "evidence_quote": "...", "cost_usd": 0.02, "latency_ms": 240},
            {"term_id": "T2", "assertion_id": "A1", "verdict": "uncertain", "evidence_quote": "", "cost_usd": 0.01, "latency_ms": 100},
            {"term_id": "T2", "assertion_id": "A2", "verdict": "pass", "evidence_quote": "...", "cost_usd": 0.02, "latency_ms": 200},
        ]
    )


def test_assertion_level(gold, preds):
    m = assertion_level(join(gold, preds))
    assert m.n_scored == 4
    assert m.accuracy == 0.5
    assert m.confusion.loc["pass", "pass"] == 1
    assert m.confusion.loc["fail", "pass"] == 1
    assert m.confusion.loc["pass", "uncertain"] == 1
    assert m.cost_usd_total == pytest.approx(0.06)
    assert m.latency_ms_mean == pytest.approx(165.0)
    assert m.coverage == {"matched": 4, "gold_only": 0, "pred_only": 0}


def test_term_level(gold, preds):
    tm = term_level(join(gold, preds))
    assert set(tm.per_term.index) == {"T1", "T2"}
    assert tm.per_term.loc["T1", "accuracy"] == 1.0
    assert tm.per_term.loc["T2", "accuracy"] == 0.0
    assert tm.per_term.loc["T1", "failed_assertion_jaccard"] == 1.0
    assert tm.per_term.loc["T2", "failed_assertion_jaccard"] == 0.0
    assert tm.term_flag_agreement == 0.5


def test_coverage_reports_missing_rows(gold, preds):
    partial = preds.iloc[:3].copy()
    extra = pd.concat(
        [partial, pd.DataFrame([{"term_id": "T9", "assertion_id": "A1", "verdict": "pass"}])],
        ignore_index=True,
    )
    m = assertion_level(join(gold, extra))
    assert m.coverage == {"matched": 3, "gold_only": 1, "pred_only": 1}


def test_loaders_reject_unknown_verdicts(tmp_path):
    bad = tmp_path / "g.csv"
    bad.write_text("term_id,assertion_id,gold_verdict\nT1,A1,maybe\n")
    with pytest.raises(ValueError):
        load_gold(bad)

    bad2 = tmp_path / "p.csv"
    bad2.write_text("term_id,assertion_id,verdict\nT1,A1,dunno\n")
    with pytest.raises(ValueError):
        load_predictions(bad2)
