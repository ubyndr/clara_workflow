---
name: verify-change
description: Review a Cell Ontology definition or comment change against its attached PMID/DOI references. Decomposes the prose into atomic assertions and scores each one pass/fail/uncertain with an evidence quote.
---

# verify-change

PROTOTYPE. Agentic replacement for the prior programmatic CLARA workflow —
one skill end-to-end: decompose + check. Split into stage-2 and stage-3
skills only when a stage-3 retrieval experiment (PaperQA2 vs. Asta vs.
full-text) needs to hold decomposition fixed.

## When to use

Invoke when checking a single decomposable change (`kind: text_def` or
`comment`) produced by stage-1 extraction. Every other content kind
(`synonym_*`, `subclass`, `relationship`, `equivalent_class`) is already
atomic — don't route those through this skill.

## Input

One reviewable change, as emitted by `clara_workflow.stage1` into the
`decomposable` array of [fixtures/stage1/<pr>/parsed.json](../../fixtures/stage1/).
Relevant fields on each record:

- `term_id`, `term_label`
- `side` — `added` or `removed`; `added` is the claim to justify, `removed`
  needs no justification and can be skipped
- `kind` — `text_def` or `comment`
- `value` — the prose to decompose
- `refs` — list of `PMID:…` / `DOI:…` identifiers attached to this axiom;
  these are the **only** references in scope for verification

You may also be invoked with a path to `parsed.json` and optionally a
`term_id` filter — in that case, process every `decomposable` change
matching the filter.

## Process

For each `added` decomposable change:

1. **Decompose** `value` into atomic assertions.
   - An atomic assertion is one scientific claim that can be independently
     true or false.
   - Markers, anatomical locations, functions, developmental origins, and
     morphological properties are each separate assertions.
   - Do not over-decompose: "expresses CD56 in humans" is one assertion,
     not two (marker + species).
   - Do not under-decompose: "expresses T-bet, CD11c, CD11b" is three
     assertions (one per marker).

2. **For each assertion, check each reference in `refs`.**
   - Fetch the reference content (PubMed abstract via EFetch for PMIDs,
     resolver for DOIs, full-text when accessible).
   - Verdict:
     - `pass` — at least one reference contains a quote that directly
       supports the assertion
     - `fail` — at least one reference directly contradicts it AND none
       support it
     - `uncertain` — neither supported nor contradicted in any reference
       (most common outcome for indirect claims or when only abstracts
       are available)

3. **Record the evidence.**
   - On `pass` / `fail`, quote the exact supporting / contradicting
     sentence and record the source (the `PMID:…` or `DOI:…` it came
     from).
   - On `uncertain`, leave `evidence_quote` empty and record the source
     you searched.

## Output

Write `runs/<term_id>/verdicts.json` (create parent dirs as needed), using
the column set from [clara_workflow/validation/schema.py](../../clara_workflow/validation/schema.py):

```json
{
  "term_id": "CL:4052001",
  "change_kind": "text_def",
  "change_side": "added",
  "change_value": "An ependymal cell that lines the lateral, third, and fourth ventricles of the brain ...",
  "refs_in_scope": ["PMID:25045600", "PMID:28067220", "PMID:37008045"],
  "assertions": [
    {
      "assertion_id": "a1",
      "assertion_text": "Multiciliated ependymal cells line the lateral, third, and fourth ventricles of the brain.",
      "verdict": "pass",
      "evidence_quote": "Multiciliated ependymal cells form a cuboidal epithelium lining the lateral, third, and fourth ventricles ...",
      "evidence_source": "PMID:25045600"
    },
    {
      "assertion_id": "a2",
      "assertion_text": "Ependymal cilia beat in a coordinated manner to facilitate CSF movement.",
      "verdict": "uncertain",
      "evidence_quote": "",
      "evidence_source": "PMID:28067220"
    }
  ]
}
```

The validation module consumes flattened `(term_id, assertion_id, verdict,
evidence_quote, evidence_source)` rows — see
[PRED_COLUMNS](../../clara_workflow/validation/schema.py). Keep the JSON
structure above; a helper can flatten it into the DataFrame schema later.

## Rules and guardrails

- **Refs are scoped to the axiom.** Do not pull in references from other
  axioms on the same term. A claim only gets verified against the refs
  attached to *its own* axiom.
- **Removed sides need no work.** If `side == "removed"`, record that the
  change is a removal and move on — stage-1 surfaces removals for
  traceability, not for justification.
- **Uncertain is a real verdict, not a cop-out.** If an abstract doesn't
  mention the claim and full text isn't accessible, `uncertain` is
  correct. Don't guess `pass` from adjacent text.
- **One source per verdict.** If multiple refs support the same assertion,
  pick the strongest quote and record that one source. The workflow will
  score per-assertion, not per-source.
- **No invented refs.** Never cite a PMID/DOI that isn't in the input
  `refs` list. If none of the input refs support the claim, the verdict
  is `uncertain` (or `fail` if contradicted).

## Known gaps

- No cost/latency tracking yet — `PRED_COLUMNS` has `cost_usd` and
  `latency_ms` fields that this skill doesn't populate.
- Full-text access is inconsistent (paywalls, partial retrieval). The
  `agentic-pipeline-testdata` repo has PDFs for the gold-set terms; no
  equivalent resource exists for arbitrary CL PR refs.
- No retrieval-backend split — this skill does its own fetching. When
  stage-3 experiments begin (PaperQA2 / Asta / full-text), we'll split
  decomposition off as a separate skill and parameterise the checker.
