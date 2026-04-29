# Agent instructions — CLARA assertion verification

You are verifying the factual claims in an ontology term's definition against
its cited references. Work one term at a time.

## Input

A cell ontology term id (e.g. `CL_4033094`). Load the term's entry from
`agentic-pipeline-testdata/data/cells_data.json`. You will use:

- `name`
- `definition` — the prose whose claims must be verified
- `references` — comma-separated list of `PMID:...` and/or `doi:/...` ids

Ignore `relations` for now (handled by classification checks, not this
workflow). Ignore the PDFs under `agentic-pipeline-testdata/data/reference/`
— retrieve sources yourself via the tools below.

## Stage A — Decompose into atomic assertions

Break the `definition` into atomic, independently verifiable claims. Aim for
claims that a single sentence from a paper could confirm or refute.

Tag every assertion with a `category`:

- **`core`** — a claim whose subject is the cell type itself (identity,
  location, markers, function, behaviour, developmental origin, disease
  association). These are the assertions that matter for term-level
  pass/fail.
- **`background`** — a definitional categorisation of a molecule / process /
  class mentioned in the definition, where the subject is not the cell type.
  Examples: "Wnt2 is a canonical Wnt ligand", "Grem1 is a BMP inhibitor",
  "T-bet is a transcription factor". Rule of thumb: if the assertion's
  grammatical subject is a molecule, gene, process, or external concept
  rather than the cell, it's `background`.

Keep `background` assertions in the output — we test and warn on them so a
hallucinated parenthetical surfaces — but they never cause a term to fail.

Guidance:

- One fact per assertion. Split conjunctions ("secretes X, Y, and Z" → three
  assertions), split clauses that bundle identity + location + function.
- Preserve the cell-type subject in every `core` assertion so it stands
  alone.
- Strip hedges ("crucial for", "key") but keep the factual core.
- Do not invent claims the definition does not make.
- Skip pure taxonomy claims already stated in `relations` unless the
  definition adds content beyond the is-a link.

Emit a numbered list of assertions (with category) before moving to Stage B.

## Stage B — Verify each assertion (snippet-first)

For each assertion:

1. Build a short query capturing the key entities + claim (cell type + marker
   / location / function). Avoid quoting the whole sentence.
2. Call `mcp__Asta_semanticscholar__snippet_search` with:
   - `query`: the query from step 1.
   - `paper_ids`: the term's references, converted to comma-separated Asta
     ids (`PMID:12345`, `DOI:10.xxxx/yyy` — uppercase the prefix, strip any
     leading slash on `doi:/...`). **Always set `paper_ids`.** Never make an
     unfiltered call.
   - `limit`: 10 is usually enough.
3. **Log the call.** Append one JSON line to
   `runs/{cell_id}/tool_calls.jsonl`:

   ```json
   {"tool":"snippet_search","assertion_id":1,"query":"<query>","paper_ids":"DOI:...,PMID:...","returned_paper_ids":["DOI:...","CorpusId:..."],"n_hits":7,"n_leaked":0}
   ```

   `returned_paper_ids` is the deduplicated list of paper ids across the
   snippet hits (use whichever id form the response gives — DOI, PMID, or
   CorpusId). `n_leaked` counts hits whose paper id is not in the requested
   set.
4. **Filter the results.** Drop any snippet whose paper id does not match one
   of the requested `paper_ids` (by DOI, PMID, or corpusId cross-reference).
   Leaked snippets are logged but never used as evidence.
5. Decide:
   - **pass** — a (non-leaked) snippet explicitly supports the assertion.
   - **fail** — a (non-leaked) snippet explicitly contradicts it.
   - **uncertain** — no snippet directly addresses the assertion.
6. Any-reference-supports rule: if a single reference yields `pass`, the
   assertion is `pass`. Do not require corroboration across references.
7. Record the verdict, the supporting snippet text (quoted, trimmed), and
   which paper it came from.

## Stage C — Full-text fallback

Trigger only for `core` assertions still `fail` or `uncertain` after Stage B.
`background` assertions stay at their Stage B verdict — no fallback.

Group the unresolved `core` assertions by reference paper. For each reference
that has unresolved assertions:

1. Call `mcp__artl-mcp__get_europepmc_full_text` with that paper's id. Log
   the call to `tool_calls.jsonl` the same way (tool: `get_full_text`,
   identifier, `available: true|false`).
2. With the full text in context, re-evaluate **all** of that paper's
   unresolved `core` assertions in one pass. This amortises the full-text
   load — it is the experimental variable we are measuring.
3. Update each assertion's verdict and cite the supporting passage.

If full text is unavailable for a paper, leave those assertions at their
Stage B verdict and note `full_text_available: false` on the call log and the
assertion.

## Output

### `runs/{cell_id}/verdicts.json`

```json
{
  "cell_id": "CL_4033094",
  "name": "...",
  "definition": "...",
  "references": ["PMID:...", "DOI:..."],
  "assertions": [
    {
      "id": 1,
      "text": "...",
      "category": "core",
      "snippet_stage": {
        "verdict": "pass|fail|uncertain",
        "evidence": "...",
        "source": "DOI:...",
        "note": null
      },
      "full_text_stage": null,
      "final_verdict": "pass|fail|uncertain",
      "warn_background": false
    }
  ],
  "summary": {
    "total": 0,
    "total_core": 0,
    "total_background": 0,
    "core_pass_snippet": 0,
    "core_pass_full_text": 0,
    "core_fail": 0,
    "core_uncertain": 0,
    "background_pass": 0,
    "background_warn": 0
  }
}
```

- `final_verdict` is derived: it is `full_text_stage.verdict` if that stage
  ran, else `snippet_stage.verdict`.
- `warn_background` is `true` iff `category == "background"` and
  `final_verdict` is `fail` or `uncertain`.
- For term-level pass/fail, only `core` assertions count. Background
  warnings surface in the summary but do not flag the term.

### `runs/{cell_id}/tool_calls.jsonl`

One JSON object per line, one line per tool invocation. Both Stage B snippet
searches and Stage C full-text fetches are logged.

### `runs/{cell_id}/report.md`

Short human-readable summary: term, definition, the assertion list with
category, final verdict, and a trimmed evidence quote. Scannable. Listed
explicitly as a required output.

## Context efficiency

- Do not re-load full text you already have in context.
- When you load full text, validate every outstanding `core` assertion for
  that paper at once.
- Do not copy snippets or full text into files beyond the quoted evidence in
  `verdicts.json` and `report.md`.

## What not to do

- Do not mark an assertion `pass` on the strength of background knowledge.
  Evidence must come from the cited references.
- Do not fabricate snippet text or paper ids.
- Do not make `snippet_search` calls without `paper_ids` set.
- Do not use leaked snippets (paper not in the requested set) as evidence.
- Do not edit `cells_data.json` or `test_set.yaml`.
