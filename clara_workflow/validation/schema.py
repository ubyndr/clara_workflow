"""Input schemas for the validation module.

Kept as column-name constants plus a Verdict enum so callers can build
DataFrames directly (from CSV, JSONL, or in-memory) without having to
instantiate row objects. The real CLARA export schema will replace the
placeholder field set below once it lands.
"""

from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


VERDICTS: tuple[str, ...] = tuple(v.value for v in Verdict)


GOLD_COLUMNS = {
    "term_id": "term_id",
    "assertion_id": "assertion_id",
    "assertion_text": "assertion_text",
    "gold_verdict": "gold_verdict",
}

PRED_COLUMNS = {
    "term_id": "term_id",
    "assertion_id": "assertion_id",
    "verdict": "verdict",
    "category": "category",
    "evidence_quote": "evidence_quote",
    "evidence_source": "evidence_source",
    "cost_usd": "cost_usd",
    "latency_ms": "latency_ms",
}


class Category(str, Enum):
    CORE = "core"
    BACKGROUND = "background"


CATEGORIES: tuple[str, ...] = tuple(c.value for c in Category)


REQUIRED_GOLD = ("term_id", "assertion_id", "gold_verdict")
REQUIRED_PRED = ("term_id", "assertion_id", "verdict")
