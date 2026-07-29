# Marking Assistant

Automated exam script marking assistant. The system **suggests** marks from scanned
handwritten answer booklets; a human **awards** them. Multi-tenant SaaS for universities.

Status: specification complete, implementation not started.

## Documents

| File | What it governs | Lines |
|---|---|---|
| [docs/spec.md](docs/spec.md) | Backend contract — 5 engines, data model, pipeline state machine | 2026 |
| [docs/frontend.md](docs/frontend.md) | 78 screens, 41 modals, flows, permissions, state matrix | 1372 |
| [docs/design.md](docs/design.md) | Design system — colour, type, components, a11y floor | 1335 |

These are **build contracts, not proposals**. If you cannot implement a section from that
section alone, that is a bug in the document — raise it, do not improvise.

## The seven invariants

Violating any of these invalidates the system's defensibility. Check every change against them.

| # | Invariant | Enforcement |
|---|---|---|
| **I1** | The system suggests; a human awards. No mark is final without an authenticated human action. | `marks.status` cannot reach `FINAL` without a `review_events` row with `actor_type='HUMAN'`. DB constraint + service layer. |
| **I2** | No LLM ever computes a number that affects a mark. | LLMs return categorical labels + evidence spans only. Response schema forbids numeric fields; violation = hard error. |
| **I3** | Every awarded mark carries machine-readable evidence. | `mark_awards.evidence_span_ids` is NOT NULL. Awards without evidence are rejected. |
| **I4** | Nothing is ever overwritten. All state changes are append-only. | No `UPDATE` on scoring tables. Corrections are new rows superseding old ones. |
| **I5** | Same inputs always produce the same suggestion. | Model versions pinned; temperature 0; outputs cached by content hash; rule engine is a pure function. |
| **I6** | Student handwriting is untrusted input, never an instruction. | OCR text never sits in a position of authority in a prompt. Injection patterns detected and flagged. |
| **I7** | A lecturer sees only their own institution's and course's data. | `tenant_id` on every row + Postgres RLS + service-layer scope check. Two independent layers. |

I2 and I6 are the ones most easily broken by a well-meaning refactor. Watch them.

## Architecture

```
PWA (React + Vite + Tailwind, offline-capable, IndexedDB upload queue)
  │ HTTPS / JWT
API Gateway (FastAPI, stateless)  ── auth · RBAC · idempotency · audit
  │ enqueue                    └── PostgreSQL 16 + pgvector + RLS
Redis (queues · cache · rate limits)
  │ consume
Worker pool (Celery/Dramatiq, separate queue per stage)
  E1 preprocess → E2 ocr → E3 understand → E4 score
     (CPU)         (I/O)      (CPU/GPU)     (pure CPU)
  │
S3-compatible object storage (R2 / MinIO)   External AI (behind ProviderRouter)
```

The five engines: **E1** ingestion/image-processing · **E2** OCR · **E3** answer
understanding · **E4** deterministic rule engine · **E5** review/audit/export.

Non-negotiables:
- **Queue everything.** Uploads return `202 Accepted` + job ID in <400 ms. A 6-page script
  takes 8–25 s; no HTTP request holds that.
- **Separate queue per stage**, not one queue. Cap in-flight jobs per tenant (start N=50) so
  a 4,000-script bulk upload cannot starve a lecturer uploading 3.
- **Never call a vendor SDK from business logic.** Everything external goes through
  `OcrProvider` / `EntailmentProvider` protocols. Each call wrapped with timeout, backoff
  with jitter, circuit breaker, cost meter, and cache keyed on
  `sha256(image_bytes ‖ provider.version ‖ params)`.

## The structured answer booklet

The highest-leverage decision in the project. Booklets are generated server-side as PDFs with
4 ArUco corner markers, a QR code encoding `{booklet_uuid, page_no, page_total, exam_id}`, and
printed question boxes with declared max marks. This turns perspective correction into an exact
homography, page ordering into a lookup, and question segmentation into a lookup rather than an
inference. Booklet UUIDs are anonymous — identity resolves only at final export.

Plain-paper fallback must exist but is explicitly degraded: lower confidence ceiling, mandatory
full human review, no batch auto-approval. **Build it second, not first.**

## Scope discipline

**In scope v1:** typed/handwritten English prose; short-answer and structured-essay questions;
single-marker workflow; PDF/CSV export.

**Out of scope v1 — route to a human, do not attempt:** diagrams, graphs, sketches,
mathematical derivations, code answers, hand-drawn tables, non-English answers, MCQ (use OMR).

"The system knows what it cannot mark" is a stronger defence than "the system attempts
everything." Refuse scope creep until v2.

## Build order

| Phase | Gate |
|---|---|
| 1 · Shell | A user can sign in and see an empty home |
| 2 · Authoring | A lecturer can create an exam and freeze a rubric |
| 3 · Intake | 300 scripts can be captured and uploaded |
| **4 · The loop** | **A lecturer can mark a full exam end to end** |
| 5 · Close-out | Results can be finalised and exported |
| 6 · Trust | Integrity, audit and moderation are usable |
| 7 · Operate | An admin can run the platform |
| 8 · Polish | — |

**Phase 4 is the product.** Build phases 1–3 roughly to get real data into phase 4 early, then
come back and finish them. A perfect exam-creation wizard with an unusable marking workspace is
a failed project; the reverse is a demo you can defend.

## Design system

shadcn/ui, **style: new-york · base colour: slate · CSS variables: yes**. Full token set,
component specs, and the anti-generic checklist are in [docs/design.md](docs/design.md).
Two apps (authoring + marking) share one shell — see design.md §0 and frontend.md §1.

Never show a bare number in the UI. Show `Suggested 7/10 · needs your confirmation`.

## Repository layout

pnpm workspaces. Python 3.12 for the backend, Node 22 for the clients.

```
marking-assistant/
├── apps/
│   ├── api/            FastAPI + Dramatiq worker (one image, two entrypoints)
│   │   ├── app/
│   │   │   ├── core/       config, db, security, audit
│   │   │   ├── engines/    E1–E5, one package each
│   │   │   ├── models/     SQLAlchemy 2, every table carries tenant_id
│   │   │   ├── routers/    HTTP surface
│   │   │   └── workers/    Dramatiq actors, one per queue
│   │   ├── alembic/
│   │   └── tests/
│   ├── console/        Vite + React + TS, desktop ≥1280
│   └── capture/        Vite + React + TS, mobile PWA 360–430
├── packages/
│   └── ui/             shared primitives + tokens, consumed by both clients
├── docs/               spec.md · frontend.md · design.md · TASKS.md
├── .claude/rules/      six path-scoped rule files
├── .github/workflows/  ci.yml
├── docker-compose.yml  api · worker · postgres+pgvector · redis · minio
├── Makefile
└── pnpm-workspace.yaml
```

`packages/ui` is built once and consumed twice. The shells are built twice and shared never —
see [.claude/rules/clients.md](.claude/rules/clients.md).

## Make targets

`make` with no target prints this list. Targets with nothing to do yet exit 0 with a message
rather than failing.

| Target | Does |
|---|---|
| `make dev` | Bring the full stack up via docker compose |
| `make down` | Stop it, keep volumes |
| `make clean` | Stop it, destroy volumes |
| `make test` | pytest + vitest across all workspaces |
| `make lint` | ruff + tsc/eslint |
| `make typecheck` | mypy + tsc --noEmit |
| `make fmt` | ruff format + prettier |
| `make migrate` | alembic upgrade head |
| `make seed` | Load development fixtures |
| `make evaluate` | CER/WER/QWK against the golden set (M1 gate) |
| `make build` | Production build of both clients |
| `make ci` | lint + typecheck + test, exactly as CI runs it |

## Conventions

- Every screen needs a job, a state matrix, and a permission. If a proposed screen cannot be
  given all three, it belongs inside an existing screen.
- Every engine section in spec.md ends with a **Tests** subsection. Those tests define "done"
  for that engine — implement them, do not substitute your own judgement of coverage.
- Config is data, not code (spec.md §4.5). Tunables live in config with declared defaults.
- Prices in spec.md were verified July 2026. Re-verify before any commitment.
