---
name: testing
description: Test gates, the golden set, and what "done" means for each engine.
globs: "**/tests/**,**/test_*.py,**/*.test.ts,**/*.test.tsx,**/conftest.py"
alwaysApply: false
source: docs/spec.md §12, per-engine Tests subsections
---

# Tests define "done"

Every engine section in spec.md ends with a **Tests** subsection. Those tests are the
definition of done for that engine. Implement them as written; do not substitute your own
judgement of what constitutes adequate coverage, and do not weaken a threshold to make a build
go green.

## The binary acceptance gates

"Mostly working" is not a state. Each milestone has one test that passes or does not.

| Milestone | Gate |
|---|---|
| M0 Foundations | A cross-tenant access attempt returns 404 **and** appears in the audit log |
| M1 Evaluation harness | `make evaluate` prints CER/WER/QWK against the golden set |
| M2 Engine 1 | ≥95% of golden photographs produce correct warps; every rejection message is actionable |
| M3 Engine 2 T1 | CER ≤ 8%; re-running costs $0 |
| M4 Engine 2 T2 | CER ≤ 6%; Tier-2 trigger rate 10–30% |
| M5 Engine 3 | Negation set ≥95% `CONTRADICTED` with **zero** `ENTAILED`; paraphrase recall ≥0.85 |
| M6 Engine 4 | 10,000 property-test cases pass; 60 golden fixtures match; no I/O in the module |
| M7 Engine 5 | A marker clears 20 scripts in under 15 minutes without a mouse |
| M8 Calibration | The QWK comparison table of §8.4 is produced with real numbers |
| M9 Hardening | Restore from backup into a clean environment succeeds; injection test set changes no marks |
| M10 Pilot | The lecturer chooses to use it again |

**Zero `ENTAILED` on the negation set is a hard zero.** A single false entailment on a negated
answer means the system awarded a mark for the opposite of the correct answer. That is the worst
failure this product can produce.

## The golden set is not optional

M1 exists before the pipeline for a reason: a system with unmeasured accuracy is not defensible
regardless of how well it demos. If the schedule slips, cut M7 polish and the self-hosted OCR
provider. **Never cut M1 or M8.**

## Always in CI

- The injection test set (I6) — student text must never change a mark.
- Cross-tenant isolation (I7) — both the RLS layer and the service layer, tested independently.
- Determinism (I5) — the same input twice produces byte-identical output.
- E4 purity (I2) — assert no I/O imports reach the rule engine module.

## Style

pytest for backend, vitest for clients. Property-based tests for E4. Fixtures over mocks where a
real object is cheap. A test that mocks the thing it is testing is not a test.

Lint and typecheck are gates, not suggestions: ruff and mypy on the backend, tsc strict on the
clients. CI fails the build on any of them. See [[invariants]].
