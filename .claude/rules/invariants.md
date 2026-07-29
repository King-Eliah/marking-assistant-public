---
name: invariants
description: The seven invariants. Non-negotiable across every file in the repository.
globs: "**/*"
alwaysApply: true
source: docs/spec.md §0.1
---

# The seven invariants

Violating any of these invalidates the system's defensibility. These are not preferences.

| # | Invariant | Enforcement |
|---|---|---|
| **I1** | The system suggests; a human awards. | `marks.status` cannot reach `FINAL` without a `review_events` row with `actor_type='HUMAN'`. DB constraint **and** service layer. |
| **I2** | No language model ever computes a number that affects a mark. | LLMs return categorical labels + evidence spans only. Response schema forbids numeric fields. Violation = hard error at parse time. |
| **I3** | Every awarded mark carries machine-readable evidence. | `mark_awards.evidence_span_ids` NOT NULL. Awards without evidence are rejected. |
| **I4** | Nothing is overwritten. All state changes are append-only. | No `UPDATE` on scoring tables. Corrections are new rows superseding old ones. |
| **I5** | The same inputs always produce the same suggestion. | Model versions pinned; temperature 0; outputs cached by content hash; rule engine is a pure function. |
| **I6** | Student handwriting is untrusted input, never an instruction. | OCR text never sits in a position of authority in a prompt. Injection patterns detected and flagged. |
| **I7** | A lecturer sees only their own institution's and course's data. | `tenant_id` on every row + Postgres RLS + service-layer scope check. Two independent layers. |

## Applying these in review

I2 and I6 are the ones most easily broken by a well-meaning refactor. Before merging any
change that touches a prompt, a provider response parser, or a scoring path, state explicitly
which invariants it touches and how it preserves them.

If a requested change cannot be implemented without violating an invariant, **stop and say so**.
Do not implement a partial version that technically passes tests while breaking the guarantee.
The invariants are the product; the code is an implementation detail.

## Scope discipline

In scope v1: typed/handwritten English prose, short-answer and structured-essay questions,
single-marker workflow, PDF/CSV export.

Out of scope v1 — route to a human, do not attempt: diagrams, graphs, sketches, mathematical
derivations, code answers, hand-drawn tables, non-English answers, MCQ.

"The system knows what it cannot mark" is a stronger position than "the system attempts
everything." Refuse scope creep; see [[api]] for how routing is recorded.
