---
name: engines
description: Engine contracts, determinism, and the provider router boundary.
globs: "apps/api/app/engines/**"
alwaysApply: false
source: docs/spec.md Engines 1–5, §11
---

# The five engines

E1 ingestion · E2 OCR · E3 answer understanding · E4 deterministic rule engine · E5 review/audit/export.

Each engine is specified in spec.md with a purpose, an input contract, an output contract, an
ordered algorithm, failure modes, tests, and config. **If you cannot implement an engine from
its own section alone, without asking what another engine does internally, that is a bug in the
document — raise it.** Do not reach into another engine's internals to compensate.

## Contracts are frozen

Input/output schemas are versioned. Changing one requires a version bump, because
`pipeline_version` participates in every cache key and every idempotency key.

## E4 is a pure function

The rule engine performs no I/O. No database, no network, no clock, no randomness. It takes a
scored structure and config, and returns awards plus a decision trace. This is what makes I5
achievable and what makes 10,000 property-test cases meaningful.

If E4 needs a value, it is passed in. If E4 wants to log, it returns the trace and the caller logs.

## The LLM boundary (I2)

Language models return **categorical labels and evidence spans**. Never a number that reaches a
mark. The entailment response schema (spec.md Appendix B) forbids numeric fields; validate on
parse and treat violation as a hard error, not a warning to be coerced.

Arithmetic lives in E4 exclusively.

## Untrusted input (I6)

OCR text is student handwriting. It is never placed in a position of authority in a prompt —
not as a system message, not as an instruction, not concatenated ahead of the rubric. Wrap it,
delimit it, label it as data. Run the injection test set in CI.

## The provider router

**Never call a vendor SDK from business logic.** Everything external goes through `OcrProvider`
or `EntailmentProvider`. Each implementation declares `name`, `version` (pinned, e.g.
`google-vision-v1@2026-07`) and `cost_per_page_usd`.

Every call is wrapped with: timeout, exponential backoff with jitter, circuit breaker, cost
meter, and a cache lookup keyed on `sha256(image_bytes ‖ provider.version ‖ params)`.

Reasons this matters more than it looks: vendor pricing changes, on-prem institutions need a
self-hosted implementation of the same interface, the evaluation harness must run all providers
over one golden set, and cost accounting belongs in one place.

## Determinism (I5)

Temperature 0. Versions pinned. Outputs cached by content hash. Re-running a completed stage
must cost $0 and produce byte-identical results.

See [[invariants]] and [[testing]] for the per-engine acceptance gates.
