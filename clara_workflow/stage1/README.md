# Stage 1 — what is checked?

Stage 1 extracts the list of changes in a PR that need reference justification.
Not every diff is a content change. This document records the rules the parser
applies so reviewers know what will (and won't) be surfaced to stages 2/3.

## Two review paths

Reviewable changes split into two groups by how they're checked:

- **Decomposable** (`text_def`, `comment`) — prose that must be broken into
  atomic assertions before each can be checked against the refs. The
  verify-change agent skill handles these.
- **Atomic** (`synonym_*`, `subclass`, `relationship`, `equivalent_class`) —
  each change is already a single claim; no decomposition step. Checked
  directly against refs (skill TBD).

`decomposable_changes()` returns only the first group; `reviewable_changes()`
returns both.

## Reviewed changes (must be justified by refs)

Any of the following, on either side (`added` or `removed`):

| `kind`              | Path          | Predicate                                 | Why reviewed |
|---------------------|---------------|-------------------------------------------|---|
| `text_def`          | decomposable  | `IAO:0000115` (definition)                | Core content claim; prose needs atomic split. |
| `comment`           | decomposable  | `rdfs:comment`                            | Often carries evidence claims in CL extended defs. |
| `synonym_exact`     | atomic        | `oboInOwl:hasExactSynonym`                | Name assertion; may introduce a contested label. |
| `synonym_broad`     | atomic        | `oboInOwl:hasBroadSynonym`                | As above; broader scope than exact. |
| `synonym_narrow`    | atomic        | `oboInOwl:hasNarrowSynonym`               | As above; narrower scope. |
| `synonym_related`   | atomic        | `oboInOwl:hasRelatedSynonym`              | As above; related-but-not-equal. |
| `subclass`          | atomic        | `rdfs:subClassOf` (named class target)    | `is_a` placement must be justified. |
| `relationship`      | atomic        | `rdfs:subClassOf` (existential restriction) | `part_of some ...`, `has_part some ...`, etc. |
| `equivalent_class`  | atomic        | `owl:equivalentClass`                     | Logical-def changes. |

Each of these carries its own `hasDbXref` list in the parser output; stage 2/3
check that list when deciding whether the change is justified.

## Not reviewed (kept in output for traceability, but skipped by `reviewable_changes()`)

| `kind`               | Why ignored |
|----------------------|---|
| `class_declaration`  | The fact that an IRI is a class is not a content claim. A new term's actual content flows through its `text_def` / synonym / `subclass` / `relationship` axioms, which are reviewed individually. |
| `label`              | `rdfs:label` is a naming choice, not an evidence claim. |
| `deprecated`         | Obsoletion is a bookkeeping act, not a content claim. |
| `annotation` (generic) | Covers contributor, date, creator, editor_note, term_tracker_item, term_replaced_by — all housekeeping. |
| `unknown`            | Bullet shape the parser couldn't classify. Surfaced in output so they show up loudly; extend the parser when one appears. |

## Obsoleted terms

If a term gains `owl:deprecated true` **or** `IAO:0100001` (term replaced by)
as an added axiom, the term is treated as obsoleted:

- `is_obsoleted: true` on the term-level summary.
- **All** its changes are dropped by `reviewable_changes()`, including the
  ones whose kinds would otherwise be reviewable.
- Rationale: the term is being removed from the active ontology, so asking
  "is the removal of this text def justified by a reference?" is not the
  question the workflow exists to answer.

Merge PRs often deprecate a term and move its content onto a replacement
term. The replacement term's content changes (if any) are still reviewable
in the normal way — it's only the *obsoleted* term that's skipped.

## What is *not* yet decided

- Pass/fail vs. advisory: all output is currently advisory. No GH Action gate.
- Whether to review `rdfs:label` edits when the new label changes meaning
  (e.g. "X cell" → "X cell of Y"). Currently ignored; may need revisiting.
- Scope of "relationship" — right now any existential restriction counts.
  Some relations (`has_part some ...`, `capable_of some ...`) carry more
  biological claim than others (`in taxon some ...`). Not yet split.
