# Task ledger

The tracking file for this project. **Read this first when the instruction is "continue".**

Sources: `spec.md` §12 (milestones M0–M10) and `frontend.md` §17 (screen phases 1–8),
resequenced for **one engineer working alone**. spec.md §12.1 assumes three developers with
contracts frozen at M1 to enable parallel work; solo, that coordination machinery is pure
overhead and the ordering logic inverts — optimise for **external lead time** and for
**killing the project early**, not for keeping three people unblocked.

Realistic effort: spec.md quotes 12–13 weeks for a team of three. Solo that is roughly
30 weeks equivalent. If a fixed deadline applies, cut stage 12 polish and the self-hosted OCR
provider first. **Never cut stage 4 (evaluation) or stage 13 (calibration)** — a system with
unmeasured accuracy is not defensible regardless of how well it demos.

---

## Current position

- [x] **Stage 0 — Scaffold** — complete except the CI push (no git remote yet)
- [ ] **Stage 1 — Platform spine** ← next, not started

Nothing in `apps/` contains product logic. The API has one `/healthz` endpoint; both
clients render a placeholder heading; `packages/ui` exports only `cn()`. There are no
models, no migrations, no screens, and no engines.

**Answer the three open questions at the foot of this file before starting stage 1** — the
`ALLOWED` table defects in particular, since stage 1 builds the state machine on top of them.

---

## Stage 0 — Scaffold

Toolchains only. Zero features.

- [x] Repository, `.gitignore`, `.gitattributes`, three specifications in `docs/`
- [x] `CLAUDE.md` with invariants, layout, and make targets
- [x] Six path-scoped rule files in `.claude/rules/`
- [x] This ledger
- [x] `apps/api` — FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Dramatiq, ruff, mypy
- [x] `apps/console` and `apps/capture` — Vite, React, TS strict, Tailwind, shadcn, design tokens
- [x] `packages/ui` — `cn()` only
- [x] `docker-compose.yml` — api, worker, postgres 16 + pgvector, redis, minio
- [x] `Makefile`, `.github/workflows/ci.yml`, `.env.example`

**Acceptance**
- [x] `make dev` brings the stack up and `/healthz` returns 200 — verified from the host, 5/5 containers healthy
- [x] `make test` passes — 2 pytest, 1 vitest console, 1 vitest capture
- [x] `make lint` passes — ruff check, ruff format --check, tsc ×2
- [x] `make typecheck` passes — mypy strict on 9 files, tsc ×3
- [ ] **CI green on a pushed branch — blocked: no git remote configured**

Eight commits on `chore/scaffold`. Everything above is done except the push.

---

## Stage 1 — Platform spine `M0`

The security substrate. Everything else assumes this is correct.

- [ ] Auth: JWT RS256, access + refresh, rotation
- [ ] RBAC: roles per `frontend.md` §7
- [ ] `tenant_id` on every table; Postgres RLS policies enabled
- [ ] Service-layer tenant scope check — the second independent layer
- [ ] Audit log with hash chain, verified on read
- [ ] Alembic migrations, `make migrate`

**Acceptance**
- [ ] A cross-tenant access attempt returns **404, not 403**, and appears in the audit log
- [ ] RLS and the service-layer guard are tested independently — each catches the leak alone
- [ ] Tampering with an audit row breaks chain verification

---

## Stage 2 — Booklet generator `slice of M2`

**Moved far forward from inside M2.** Small, and it gates everything physical. The golden set
is 200 photographed *booklet* pages, so booklets must exist before capture can start. Printing,
recruiting writers, and photographing carry multi-week lead time that no coding speed recovers.

- [ ] Server-side booklet PDF: 4 ArUco fiducials (12mm, corners)
- [ ] QR encoding `{booklet_uuid, page_no, page_total, exam_id}`
- [ ] Printed question boxes with declared max marks
- [ ] Anonymous booklet UUID — no student name on the page

**Acceptance**
- [ ] A generated booklet prints at A4 and its QR decodes from a phone photograph
- [ ] All four fiducials detect at 150 DPI under uneven lighting

---

## Stage 3 — Golden set acquisition `M1 data` — starts here, runs for weeks

**Start on day one of this stage and let it run in the background.** The risk register rates
"no lecturer will release real scripts" as *Critical* likelihood-medium and says explicitly:
ask on day one, not week eight. This is the only task where working harder does not help.

- [ ] Request real scripts from a lecturer; offer anonymisation
- [ ] Fallback: volunteers copy answers by hand onto generated booklets
- [ ] 200 photographed pages, varied handwriting and lighting
- [ ] 500 hand-transcribed lines (ground truth for CER/WER)
- [ ] 150 dual-marked answers (ground truth for QWK)
- [ ] Negation and paraphrase probe sets
- [ ] Prompt-injection test set

**Acceptance**
- [ ] The set is committed, versioned, and documented
- [ ] Licensing and consent for every real script is recorded

---

## Stage 4 — Evaluation harness `M1 code`

Built before the pipeline it measures. Non-negotiable.

- [ ] CER / WER scorers
- [ ] QWK scorer against dual-marked ground truth
- [ ] Per-provider comparison over one golden set
- [ ] `make evaluate`

**Acceptance**
- [ ] `make evaluate` prints CER, WER, and QWK against the golden set
- [ ] Re-running produces identical numbers

---

## Stage 5 — Engine 1, ingestion `rest of M2`

- [ ] Fiducial detection and homography warp
- [ ] Deskew, denoise, normalise to `WORK_LONG_EDGE`
- [ ] Quality gate with computable thresholds
- [ ] Client-side pre-flight
- [ ] Plain-paper fallback — **second, explicitly degraded**

**Acceptance**
- [ ] ≥95% of golden photographs produce correct warps
- [ ] Every rejection message tells the user what to do differently

---

## Stage 6 — Engine 2, OCR `M3 + M4`

- [ ] Tier 1: primary provider, line reconstruction, per-line confidence, raw archival
- [ ] Content-hash cache
- [ ] Tier 2: cascade, arbiter, reconciliation
- [ ] Strikethrough rule
- [ ] Human transcription UI — minimal, functional
- [ ] `NEEDS_TRANSCRIPTION` path end to end

**Acceptance**
- [ ] CER ≤ 8% Tier 1, ≤ 6% with Tier 2
- [ ] Tier-2 trigger rate lands 10–30%
- [ ] Re-running a completed page costs $0

---

## Stage 7 — Engine 3, answer understanding `M5`

Largest engine. 2 weeks for a team; budget more.

- [ ] Segmentation against printed question boxes
- [ ] Embeddings, reranking, Hungarian assignment
- [ ] NLI + LLM entailment behind `EntailmentProvider`
- [ ] Response schema enforcement — **numeric fields rejected at parse (I2)**
- [ ] Injection detection on OCR text (I6)

**Acceptance**
- [ ] Negation set ≥95% `CONTRADICTED` with **zero** `ENTAILED` — a hard zero
- [ ] Paraphrase recall ≥ 0.85
- [ ] No LLM response containing a number ever reaches scoring

---

## Stage 8 — Engine 4, rule engine `M6`

Smallest engine, strictest gate. The cheapest possible proof that the scoring half is sound.

- [ ] Pure function: no database, no network, no clock, no randomness
- [ ] YAML rule configuration
- [ ] Decision traces
- [ ] Evaluation order exactly as spec.md §4.3

**Acceptance**
- [ ] 10,000 property-test cases pass
- [ ] 60 golden fixtures match exactly
- [ ] A test asserts no I/O imports reach the module

---

## Stage 9 — Throwaway review harness

**Not in either source document.** Deliberately ugly, explicitly disposable. Alone, you need to
see suggestions and evidence before building 78 screens on top of them, and before calibration
can be judged by eye.

- [ ] Render a script, its suggestions, and evidence spans
- [ ] No design system, no polish, delete at stage 12

**Acceptance**
- [ ] A full script's suggestions are inspectable end to end

---

## Stage 10 — Console shell and authoring `FE 1–2`

First real UI. Desktop ≥1280 only.

- [ ] Auth screens A1–A4, home C1
- [ ] Sidebar + top bar, design tokens, `packages/ui` primitives
- [ ] Courses D1–D2, exams E1–E3, questions and rubric F1–F4
- [ ] Rubric linter (Appendix C) blocking freeze

**Acceptance**
- [ ] A lecturer creates an exam and freezes a rubric
- [ ] The linter blocks a non-atomic marking point

---

## Stage 11 — Capture PWA and intake `FE 3`

Mobile only, offline first.

- [ ] Booklet registration G1–G3
- [ ] Camera capture H1–H5, on-device quality pre-check
- [ ] IndexedDB upload queue surviving connection loss and process death
- [ ] Processing view I1

**Acceptance**
- [ ] 300 scripts captured and uploaded
- [ ] Airplane mode mid-batch loses nothing

---

## Stage 12 — Review workspace `M7 / FE 4` — **this is the product**

Everything before is setup; everything after is around it.

- [ ] Marking queue J1, review workspace J2–J4
- [ ] Evidence highlighting with tints, badges, dash patterns
- [ ] Full keyboard flow
- [ ] Audit view, appeal bundle
- [ ] Delete the stage 9 harness

**Acceptance**
- [ ] A marker clears 20 scripts in under 15 minutes **without touching a mouse**
- [ ] No bare number appears anywhere in the UI
- [ ] Nothing the system generates renders red

---

## Stage 13 — Calibration and shadow run `M8`

- [ ] Fit thresholds on real data
- [ ] Process one real exam in shadow mode
- [ ] Produce the §8.4 QWK comparison table

**Acceptance**
- [ ] The comparison table exists with real numbers, not projections

---

## Stage 14 — Close-out `FE 5`

- [ ] Results K1, K4, K5; export; single-script report
- [ ] Finalisation with sample-audit enforcement — forced review of a random 10% above 50 scripts
- [ ] Identity resolution at export only

**Acceptance**
- [ ] Results finalise and export with per-mark attribution

---

## Stage 15 — Hardening and pilot `M9 + M10`

- [ ] Rate limits, per-tenant cost caps, DLQ triage
- [ ] Backup restore drill
- [ ] Dependency scan, penetration checklist
- [ ] One real course, lecturer in the loop

**Acceptance**
- [ ] Restore from backup into a clean environment succeeds
- [ ] The injection test set changes no marks
- [ ] **The lecturer chooses to use it again**

---

## Deferred to v2

Diagrams · graphs · sketches · mathematical derivations · code answers · hand-drawn tables ·
non-English answers · MCQ (use OMR) · multi-marker moderation beyond the basics · SIS integration.

## Open questions

- [ ] Deadline? Determines what gets cut from stages 12 and 14.
- [ ] Which institution is the pilot, and is the golden-set request already in flight?
- [ ] Resolve the `ALLOWED` table defects noted in `.claude/rules/api.md` before stage 1.
