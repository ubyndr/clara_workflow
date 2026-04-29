# CLARA GitHub Action

Template workflow that runs stage-1 CLARA review on a PR in an ontology repo
(e.g. `cell-ontology`). Copy [clara-review.yml](clara-review.yml) to
`.github/workflows/clara-review.yml` in the target repo and adjust two things:

1. **Edit file path** — the `--edit-file` arg in the "Run stage-1 extractor"
   step. Default is `src/ontology/cl-edit.owl` (CL convention).
2. **Install source** — the `pip install` line points at
   `Cellular-Semantics/clara_workflow@main`. Replace with your fork / pin to a
   commit once you want reproducibility.

## Triggers

- **Slash-command** — comment `/clara` on any PR.
- **Manual** — *Actions → CLARA review → Run workflow*, supply a PR number.

The `issue_comment` event always runs the workflow version from the default
branch, not the PR branch, so merging this file to `main` in the ontology repo
is the activation step.

## Output

- Summary comment posted back on the PR (term count, change count, new-term flag per term).
- `changes.json` uploaded as an artifact — full per-axiom change list with dbxref
  justifications attached, ready for downstream stages.

## Scope

Stage 1 only — advisory output, never fails the PR. Stage-2 (atomic assertion
decomposition) and stage-3 (reference checking) are not wired up yet; once they
are, the same workflow can gate comments on their verdicts.
