# Roadmap

Planned experiments for the agentic CLARA replication. Each experiment is scoped so it can be run against the existing CLARA gold-standard test set and scored directly.

## Prerequisites

- [ ] Import the prior CLARA test set (terms + references + per-assertion scores).
- [ ] Confirm full text is retrievable for every reference in the set.
- [ ] Agree on a scoring harness that matches the CLARA rubric closely enough to compare runs.
- [ ] Stand up the three stage-1 / stage-2 / stage-3 agents as separable components so backends can be swapped per stage.

## Stage 1 — Term extraction

- [ ] Define the input contract (term IRI / ID) and output schema (definition, refs, classification, relationships).
- [ ] Implement a single extractor that reads from the source ontology and emits the canonical structure.

## Stage 2 — Atomic assertion decomposition

- [ ] Collect a small set of worked examples of "atomic" assertions to include in the prompt.
- [ ] Leave the atomicity judgement to the agent; do not hard-code rules.
- [ ] Spot-check decomposition quality against a handful of hand-decomposed terms before running at scale.

## Stage 3 — Assertion checking (the experiments)

### Experiment 1 — Asta snippet search, with full-text fallback

First pass:

- [ ] For each atomic assertion, run Asta snippet search against the provided references.
- [ ] Record pass / fail / uncertain per assertion.

Fallback for failures:

- [ ] For every assertion that fails the snippet pass, re-run against full text.
- [ ] Titrate batching — start with one assertion per call, then group assertions per reference, then per term, and measure accuracy + cost at each step.

Outputs:

- [ ] Per-assertion verdicts aligned to the CLARA gold standard.
- [ ] Accuracy, precision, recall vs. CLARA scores.
- [ ] Cost / latency per stage, broken out by snippet-only vs. full-text fallback.

### Experiment 2 — Local PaperQA2 baseline *(candidate)*

- [ ] Run the same assertions through local PaperQA2 over the reference PDFs.
- [ ] Compare head-to-head with Experiment 1 on the same gold set.

### Experiment 3 — Full text only *(candidate)*

- [ ] Skip snippet search; go straight to full text with whatever batching came out best in Experiment 1.
- [ ] Useful as an upper-bound reference run.

## Evaluation

- [ ] Per-assertion agreement with CLARA scores.
- [ ] Term-level agreement (does the agent flag the same problem terms CLARA did?).
- [ ] Failure mode analysis — which assertions are we getting wrong, and is it a retrieval failure or a reasoning failure?

## Open questions

- How strict should the atomicity examples be before they start biasing the agent?
- Is Asta's coverage of the reference set good enough to make snippet-first the default, or does full-text-first win once cost is ignored?
- Where should disagreement with CLARA be trusted over the gold standard (i.e., CLARA was wrong)?
