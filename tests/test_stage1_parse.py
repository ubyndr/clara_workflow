"""Unit tests for the stage-1 prototype parser.

Uses cached `robot diff --format markdown` fixtures under fixtures/stage1/ so
the test suite doesn't require ROBOT or a CL clone. Regenerate the fixtures by
re-running robot diff against the branches named in each `refs.txt`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clara_workflow.stage1 import (
    CONTENT_KINDS,
    DECOMPOSABLE_KINDS,
    decomposable_changes,
    parse_diff_markdown,
    reviewable_changes,
    summarise_by_term,
)


FIXTURES = Path(__file__).parent.parent / "fixtures" / "stage1"


def _load(slug: str) -> str:
    return (FIXTURES / slug / "diff.md").read_text()


# --- 2508: single-term NTR -------------------------------------------------

def test_2508_new_term_declared():
    by_term = summarise_by_term(parse_diff_markdown(_load("2508-multiciliated-ependymal-cell")))
    assert "CL:4052001" in by_term
    assert by_term["CL:4052001"]["is_new_term"] is True
    assert by_term["CL:4052001"]["is_obsoleted"] is False
    assert by_term["CL:4052001"]["is_reviewable"] is True
    assert by_term["CL:4052001"]["term_label"] == "multiciliated ependymal cell"


def test_2508_text_def_has_refs():
    changes = parse_diff_markdown(_load("2508-multiciliated-ependymal-cell"))
    defs = [c for c in changes if c.kind == "text_def" and c.side == "added"]
    assert len(defs) == 1
    assert defs[0].value.startswith("An ependymal cell that lines the lateral")
    assert set(defs[0].refs) == {"PMID:25045600", "PMID:28067220", "PMID:37008045"}


def test_2508_emits_relationships_and_parents():
    changes = parse_diff_markdown(_load("2508-multiciliated-ependymal-cell"))
    kinds = {c.kind for c in changes if c.side == "added"}
    assert "subclass" in kinds            # is_a parents
    assert "relationship" in kinds        # part of / has part some ...


# --- 2441: text-def revision -----------------------------------------------

def test_2441_paired_def_remove_and_add():
    """A def revision surfaces as one Removed + one Added text_def axiom."""
    changes = parse_diff_markdown(_load("2441-revise-epithelial-cell-of-uterus-defs"))
    defs = [c for c in changes if c.kind == "text_def" and c.term_id == "CL:0002149"]
    sides = {c.side for c in defs}
    assert sides == {"added", "removed"}
    added = next(c for c in defs if c.side == "added")
    removed = next(c for c in defs if c.side == "removed")
    assert "mesodermal origin" in added.value
    assert "mesodermal" not in removed.value   # removed def is the bare placeholder


# --- 2485: second NTR, different biology ----------------------------------

def test_2485_new_term():
    by_term = summarise_by_term(parse_diff_markdown(_load("2485-ntr-pancreatic-islet-capillary-endothelial-cell")))
    assert by_term["CL:4052014"]["is_new_term"] is True
    assert by_term["CL:4052014"]["term_label"] == "pancreatic islet capillary endothelial cell"


# --- 2480: new parent + revised children ----------------------------------

def test_2480_new_parent_plus_child_revisions():
    changes = parse_diff_markdown(_load("2480-text-and-log-def-syncytial-epithelial-cell"))
    by_term = summarise_by_term(changes)
    # New parent term introduced.
    assert by_term["CL:4052002"]["is_new_term"] is True
    assert by_term["CL:4052002"]["term_label"] == "syncytial cell"
    # Existing child has its def revised (not a new term).
    assert by_term["CL:0000420"]["is_new_term"] is False
    assert by_term["CL:0000420"]["is_reviewable"] is True


# --- 2471: merge / obsoletion ---------------------------------------------

def test_2471_obsoletion_detected():
    """The merge subject should be flagged obsoleted and excluded from review."""
    changes = parse_diff_markdown(_load("2471-juxtaglomerular-complex-cells-merge"))
    by_term = summarise_by_term(changes)
    assert "CL:1000618" in by_term
    assert by_term["CL:1000618"]["is_obsoleted"] is True
    assert by_term["CL:1000618"]["is_reviewable"] is False


def test_2471_obsoleted_term_dropped_from_reviewable():
    changes = parse_diff_markdown(_load("2471-juxtaglomerular-complex-cells-merge"))
    reviewed = reviewable_changes(changes)
    assert all(c.term_id != "CL:1000618" for c in reviewed), \
        "obsoleted term's changes must be excluded from reviewable output"


def test_2471_non_obsoleted_terms_still_reviewable():
    """Other terms in the merge PR should still be reviewed."""
    changes = parse_diff_markdown(_load("2471-juxtaglomerular-complex-cells-merge"))
    reviewed = reviewable_changes(changes)
    # kidney granular cell is adjacent to the merge but not deprecated.
    assert any(c.term_id == "CL:0000648" for c in reviewed)


# --- reviewable filter invariants -----------------------------------------

@pytest.mark.parametrize("slug", [
    "2508-multiciliated-ependymal-cell",
    "2441-revise-epithelial-cell-of-uterus-defs",
    "2485-ntr-pancreatic-islet-capillary-endothelial-cell",
    "2480-text-and-log-def-syncytial-epithelial-cell",
    "2471-juxtaglomerular-complex-cells-merge",
])
def test_reviewable_is_subset_of_all(slug):
    changes = parse_diff_markdown(_load(slug))
    reviewed = reviewable_changes(changes)
    # Strict subset on size, and each reviewed change is of a content kind.
    assert len(reviewed) <= len(changes)
    assert all(c.kind in CONTENT_KINDS for c in reviewed)


@pytest.mark.parametrize("slug", [
    "2508-multiciliated-ependymal-cell",
    "2441-revise-epithelial-cell-of-uterus-defs",
    "2485-ntr-pancreatic-islet-capillary-endothelial-cell",
    "2480-text-and-log-def-syncytial-epithelial-cell",
    "2471-juxtaglomerular-complex-cells-merge",
])
def test_decomposable_is_subset_of_reviewable(slug):
    """decomposable ⊆ reviewable, and contains only text_def / comment."""
    changes = parse_diff_markdown(_load(slug))
    reviewed = reviewable_changes(changes)
    decomp = decomposable_changes(changes)
    assert len(decomp) <= len(reviewed)
    assert all(c.kind in DECOMPOSABLE_KINDS for c in decomp)
    # Everything decomposable must also be in the reviewable list.
    rev_ids = {id(c) for c in reviewed}
    assert all(id(c) in rev_ids for c in decomp)


@pytest.mark.parametrize("slug", [
    "2508-multiciliated-ependymal-cell",
    "2441-revise-epithelial-cell-of-uterus-defs",
    "2485-ntr-pancreatic-islet-capillary-endothelial-cell",
    "2480-text-and-log-def-syncytial-epithelial-cell",
    "2471-juxtaglomerular-complex-cells-merge",
])
def test_no_unknown_changes(slug):
    """Every bullet in every fixture must be classified; unknowns flag a parser gap."""
    changes = parse_diff_markdown(_load(slug))
    unknown = [c for c in changes if c.kind == "unknown"]
    assert not unknown, f"unclassified bullets: {[c.raw for c in unknown[:3]]}"
