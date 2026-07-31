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

- [x] **Stage 0 — Scaffold** — complete
- [x] **Stage 1 — Platform spine** — complete, isolation gate closed end to end
- [x] **Stage 2 — Booklet generator** — complete, **gate closed on real printed paper**
- [x] **Stage 3 — Engine 1, ingestion** — complete, validated on real photographs
- [ ] **Stage 4 — Engine 2, OCR** ← next

36 commits. **512 backend tests, 6 frontend**, ruff and mypy clean.

Built so far: pipeline state machine, tenancy models, RLS + app role + audit immutability,
service-layer guard, hash-chained audit writer, argon2id + RS256 auth, `GET`/`LIST /courses`,
booklet generator with issue and download endpoints, encrypted student identity map, the
capture quality gate, homography rectification, page identification, and Engine 1 assembled
end to end. Console shell with sign-in and an empty home.

**CI is suspended at the GitHub account level** — an unpaid $6.64 Copilot invoice puts the
account in billing failure, which stops Actions on every repo. Not a workflow defect: a
seven-line probe workflow failed identically, as does GitHub's own dependabot job. `make ci`
runs the same gates locally in the meantime.

---

## Running in parallel — start today, not in week two

- [ ] **Golden set.** Print ~40 booklets, recruit 3–4 people to hand-copy answers, photograph
      them. Target 100 pages, 250 transcribed lines, 60 dual-marked answers. Scaled down from
      spec.md's 200/500/150 to fit the clock. **Every accuracy number in week 3 depends on this
      existing by end of week 1.**

      **Capture requirement, measured:** the page must span ~80% of the frame, or the camera
      must be set above 4 MP. The reference photographs came in at 47–93 DPI against a 120 DPI
      floor, entirely because the page filled only 55–61% of the frame at 2 MP. A whole golden
      set captured that way would be unusable, so check the first few through the quality gate
      before photographing three hundred.
- [ ] **Provider billing.** Google Vision and Gemini keys, payment verified. Risk register rates
      this Medium/High. If it fails on day 6 it costs a third of the remaining time. **The same
      declining card already broke GitHub Actions — resolve the card, not just the invoice.**
- [x] `gh auth refresh -h github.com -s workflow` — done; 25 commits pushed
- [ ] **Settle the $6.64 GitHub invoice** to restore CI, and set a $0 Copilot budget at
      https://github.com/settings/billing/budgets to stop it recurring.
- [ ] **Delete `marking-assistant-public`** — it existed only to test a CI theory that turned
      out to be wrong, and it is world-readable.

---

## Week 1 — the spine and the vision half

### Stage 1 — Platform spine `M0` — **complete**
- [x] Auth: JWT RS256, access + refresh, argon2id passwords
- [x] Two roles only: `LECTURER`, `ADMIN`. Full RBAC is out.
- [x] `tenant_id` on every table; Postgres RLS policies + `marking_app` role
- [x] Service-layer scope check — the second independent layer
- [x] Audit log with hash chain, verified on read, immutable at the database
- [x] `transition()` implementing the corrected `ALLOWED` table (spec.md §4 v1.1)

**Gate — passed.** Cross-tenant `GET /courses/{id}` returns 404, is indistinguishable from a
missing row, and appears in the caller's audit chain, which still verifies afterwards. All 240
undeclared state transitions raise.

**Three defects found and fixed while proving it** — each worth knowing about, because each
looked correct until tested:

1. **RLS was inert.** The app connected as the migration owner, a superuser, which bypasses RLS
   entirely. Policies existed, every query succeeded, and the only symptom was a listing
   endpoint returning another institution's rows. `assert_rls_applies()` now refuses to start
   as any role with `SUPERUSER` or `BYPASSRLS`.
2. **A malformed IP could suppress an audit row.** `audit_log.ip` is `INET`; an unparseable
   value aborted the whole append. Behind a proxy that value is attacker-controlled. The field
   is discarded now — losing a column beats losing the row.
3. **`TRUNCATE` bypassed audit immutability.** A `FOR EACH ROW` trigger does not fire on
   `TRUNCATE`, so the entire log was wipeable in one statement. Statement-level trigger added.

### Stage 2 — Booklet generator — **complete**
- [x] A4 PDF: 4 ArUco fiducials, QR `{booklet_uuid, page_no, page_total, exam_id}`, question
      boxes with declared max marks, anonymous UUID
- [x] Answer box heights derived from marks; leftover page space shared by marks
- [x] Index-number region on page 1, cropped before marking
- [x] `POST /exams/{id}/booklets`, `GET /booklets/{id}.pdf`, listing

**Gate — passed on real paper.** A booklet printed on a real printer and photographed on a
phone: all four fiducials found on every one of six photographs, and the QR decoded back to
exactly the UUIDs the generator wrote. Those photographs are in the test suite.

### Stage 3 — Engine 1, ingestion — **complete**
- [x] Fiducial detection, homography rectification, deskew
- [x] Quality gate with actionable rejection messages
- [x] Page identification from the rectified QR
- [x] Identity-region redaction by coordinate
- [x] `ingest()` assembling the whole engine
- [x] Plain-paper fallback **cut** — booklets only

**Gate:** deferred to the golden set. The ≥95% warp figure needs golden photographs to measure
against; rectification is validated on the reference photographs in the meantime.

**What the real paper taught us**, all of it now encoded in thresholds rather than guesses:

- **The QR needs 120 DPI, not 90.** Sweeping a real photograph through scale decoded at 79, 63
  and 48 DPI but failed at 71, 56 and 40 — non-monotonic, because the module grid sometimes
  aligns with the pixel grid. Below ~100 DPI success is luck, so the gate sits where decoding
  is *reliable*.
- **Rectify before decoding.** A page failed to decode raw and succeeded once flattened.
  Perspective correction is worth real resolution to the decoder.
- **Fiducials are far more robust than the QR.** 12mm 4x4 markers were found at 47 DPI — a
  third of the intended resolution — while the QR needed nearly three times that.
- **Overexposure cannot be judged by mean brightness.** A booklet page is mostly white paper:
  a lightly-written page measures 250 and a blown-out one 252. Clipping fraction is the honest
  signal.

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
