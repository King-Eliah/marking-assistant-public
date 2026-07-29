---
name: api
description: Backend service rules — tenancy, persistence, state machine, idempotency, audit.
globs: "apps/api/**"
alwaysApply: false
source: docs/spec.md §2, §3, §4, §7
---

# API and persistence

FastAPI on Python 3.12. SQLAlchemy 2 (typed, `Mapped[...]`), Alembic, Pydantic v2, Dramatiq.

## Tenancy — two independent layers

Every table carries `tenant_id UUID NOT NULL`. Isolation is enforced twice:

1. **Postgres Row-Level Security** — the policy, not the query, is the guarantee.
2. **Service-layer scope check** — explicit and unit-testable.

A bug in one layer must not leak data. Never disable RLS "just for this query". Cross-tenant
access returns **404, not 403** — a 403 confirms the resource exists.

Rejected alternatives, do not revisit: schema-per-tenant, database-per-tenant.

## The state machine

Every script and page stores its state. **Never infer state.** All transitions go through a
single `transition()` function and nowhere else. The `ALLOWED` map in spec.md §4 is the only
source of truth for legal moves.

Three defects in the original table were corrected in spec.md v1.1. The resolutions are binding:

- `QUALITY_REJECTED → {PREPROCESSING, FAILED}`. A retake supplies a new image for the same page
  slot and re-enters preprocessing.
- `FAILED` is **terminal for the attempt**. Triage creates a new attempt; it never revives a dead
  one. This is what keeps I4 and the `(script_id, stage, pipeline_version)` idempotency key intact.
- Only `MACHINE_STATES` can reach `FAILED` — it means a worker exhausted its retries, and the
  human states have no worker. A human state is left only by a human action.
- The canonical name is `NEEDS_TRANSCRIPTION`. Never `NEEDS_TRANSCRIPT`.

`transition()` must reject any move not in `ALLOWED`, and the rejection is an error, not a
silent no-op. Unit-test every illegal edge, not just the legal ones.

## Append-only (I4)

No `UPDATE` on scoring tables. A correction inserts a new row that supersedes its predecessor.
If you find yourself writing `UPDATE mark_awards`, the design is wrong.

## Idempotency

Every worker task is keyed `(script_id, stage, pipeline_version)`. Re-running a completed stage
is a no-op returning the cached result. This is what makes retries safe and what makes a full
reprocess after a model upgrade cheap.

## Queues

Separate queue per stage, never one queue: `q.preprocess`, `q.ocr`, `q.understand`, `q.score`,
`q.export`, `q.dlq`. Cap in-flight jobs per tenant (`TENANT_MAX_INFLIGHT_JOBS`, default 50) so a
4,000-script bulk upload cannot starve a lecturer uploading three.

Uploads return `202 Accepted` with a job id in under 400 ms. No HTTP request holds a pipeline run.

## Audit

Hash-chained audit log. Every state change and every human action appends. The chain is verified
on read; a broken chain is an incident, not a warning.

See [[invariants]] for I1/I4/I7 and [[engines]] for the provider boundary.
