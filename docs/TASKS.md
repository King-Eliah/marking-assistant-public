# Task ledger

The tracking file for this project. **Read this first when the instruction is "continue".**

**Deadline: 2–3 weeks from 2026-07-29.** Target ship date **2026-08-19**.

Sources: `spec.md` §12 (M0–M10) and `frontend.md` §17 (phases 1–8), resequenced for one engineer
against a three-week clock. spec.md budgets 12–13 weeks for a team of three; that plan is not
reachable and is not being attempted.

## What this deadline buys, and what it does not

**In:** every `[MVP]` screen (26 of 78, already marked in frontend.md), all five engines, the
evaluation harness, real accuracy numbers, and a working end-to-end path from printed booklet to
exported mark.

**Out, explicitly:** M8 calibration on a real exam · M9 hardening · M10 pilot · the 52 non-MVP
screens · analytics · moderation · integrity review · admin beyond user management · SIS export.

**Therefore:** at ship this is defensible for a viva and usable for a demo. It is **not** safe for
marking exams that count toward a real degree — thresholds will still be Appendix A defaults
rather than values fitted to data. Say so plainly in the write-up. That honesty is the strongest
position available and it is also simply true.

---

## Current position

- [x] **Stage 0 — Scaffold** — complete, 10 commits, CI blocked on `workflow` token scope
- [ ] **Stage 1 — Platform spine** ← in progress

Nothing in `apps/` contains product logic yet.

---

## Running in parallel — start today, not in week two

- [ ] **Golden set.** Print ~40 booklets, recruit 3–4 people to hand-copy answers, photograph
      them. Target 100 pages, 250 transcribed lines, 60 dual-marked answers. Scaled down from
      spec.md's 200/500/150 to fit the clock. **Every accuracy number in week 3 depends on this
      existing by end of week 1.**
- [ ] **Provider billing.** Google Vision and Gemini keys, payment verified. Risk register rates
      this Medium/High. If it fails on day 6 it costs a third of the remaining time.
- [ ] `gh auth refresh -h github.com -s workflow`, so CI can run.

---

## Week 1 — the spine and the vision half

### Stage 1 — Platform spine `M0`
- [ ] Auth: JWT RS256, access + refresh
- [ ] Two roles only: `LECTURER`, `ADMIN`. Full RBAC is out.
- [ ] `tenant_id` on every table; Postgres RLS policies
- [ ] Service-layer scope check — the second independent layer
- [ ] Audit log with hash chain, verified on read
- [ ] `transition()` implementing the corrected `ALLOWED` table (spec.md §4 v1.1)

**Gate:** cross-tenant access returns 404, appears in the audit log; every illegal state
transition is rejected with an error, not a silent no-op.

### Stage 2 — Booklet generator
- [ ] A4 PDF: 4 ArUco fiducials, QR `{booklet_uuid, page_no, page_total, exam_id}`, question
      boxes with declared max marks, anonymous UUID

**Gate:** a printed booklet's QR decodes from a phone photo; all four fiducials detect at 150 DPI.

### Stage 3 — Engine 1, ingestion
- [ ] Fiducial detection, homography warp, deskew, normalise to `WORK_LONG_EDGE`
- [ ] Quality gate with actionable rejection messages
- [ ] Plain-paper fallback **cut** — booklets only

**Gate:** ≥95% of golden photographs warp correctly.

---

## Week 2 — the understanding half and the product

### Stage 4 — Engine 2, OCR
- [ ] Tier 1: primary provider, line reconstruction, per-line confidence, raw archival
- [ ] Content-hash cache — re-running must cost $0
- [ ] Tier 2 arbitration **only if week 1 finished early**
- [ ] Human transcription screen (MVP `/transcribe/:scriptId`)

**Gate:** CER ≤ 8% Tier 1 on the golden set.

### Stage 5 — Engine 3, answer understanding
- [ ] Segmentation by printed question box — a lookup, not an inference
- [ ] Embeddings + entailment behind `EntailmentProvider`
- [ ] Response schema enforcement: **numeric fields rejected at parse (I2)**
- [ ] Injection detection on OCR text (I6)
- [ ] Reranking and Hungarian assignment **cut unless time allows**

**Gate:** negation set ≥95% `CONTRADICTED` with **zero** `ENTAILED`. Hard zero, non-negotiable.

### Stage 6 — Engine 4, rule engine
- [ ] Pure function: no database, no network, no clock, no randomness
- [ ] YAML config, decision traces, evaluation order per spec.md §4.3

**Gate:** 10,000 property-test cases pass; a test asserts no I/O imports reach the module.

### Stage 7 — Review workspace `this is the product`
- [ ] `/exams/:id/marking` queue and `/exams/:id/marking/:scriptId` workspace
- [ ] Evidence highlighting: tints, letter badges, dash patterns, stable assignment
- [ ] Full keyboard flow

**Gate:** clear 20 scripts in under 15 minutes without a mouse · no bare numbers anywhere ·
nothing the system generates renders red.

---

## Week 3 — measure, complete the MVP, write up

### Stage 8 — Evaluation harness
- [ ] CER / WER / QWK scorers, `make evaluate`

**Gate:** `make evaluate` prints real numbers against the golden set. Re-running gives identical
results.

### Stage 9 — Remaining MVP screens
- [ ] Auth A1–A4, home C1, courses D1–D2, exams E1–E3, questions/rubric F1–F4
- [ ] Rubric linter (Appendix C) blocking freeze
- [ ] Capture H1–H5 with IndexedDB offline queue, processing I1
- [ ] Results K1, K5, CSV/PDF export with per-mark attribution

**Gate:** a lecturer creates an exam, prints booklets, captures 20 scripts, marks them, exports.

### Stage 10 — Write-up
- [ ] Accuracy numbers with honest error bars
- [ ] Known limitations, explicitly including uncalibrated thresholds
- [ ] Which invariants are enforced where, and how each is tested

---

## Deferred — name these as deferred, not missing

M8 calibration · M9 hardening · M10 pilot · 52 non-MVP screens · Tier-2 OCR if cut · reranking if
cut · plain-paper fallback · diagrams, graphs, maths, code answers, hand-drawn tables,
non-English, MCQ · moderation · integrity · analytics · SIS integration.

## Open questions

- [ ] Does the week-3 deliverable need a live demo, or only the written artefact?
- [ ] Who are the 3–4 people writing the golden set, and when?
