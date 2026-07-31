"""The OCR router.

Two properties carry the weight: a re-run costs nothing (I5, and what makes
the evaluation harness affordable to iterate on), and a failing provider is
stopped rather than hammered.

The provider here is a fake that counts its calls. That is the point of the
interface — the router's behaviour is testable without a network, an API key,
or a cent of spend.
"""

from __future__ import annotations

import uuid

import pytest

from app.engines.ocr.contracts import BBox, LineSource, OcrHints, OcrLine, OcrResult
from app.engines.ocr.provider import ProviderError, ProviderRefusedError, ProviderTimeoutError
from app.engines.ocr.router import (
    CircuitBreaker,
    CircuitOpenError,
    CostCapExceededError,
    CostMeter,
    InMemoryCache,
    OcrRouter,
    cache_key,
)

PAGE = uuid.uuid4()


class FakeProvider:
    """Counts calls and can be told to fail."""

    def __init__(self, *, fail_times: int = 0, error: type[Exception] = ProviderTimeoutError):
        self.calls = 0
        self.fail_times = fail_times
        self.error = error

    name = "fake"
    version = "fake-v1@2026-07"
    cost_per_page_usd = 0.0015

    def recognise(self, image: bytes, hints: OcrHints) -> OcrResult:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.error("induced failure")
        return OcrResult(
            page_id=PAGE,
            lines=(
                OcrLine(
                    line_index=0,
                    text="Deadlock occurs when four conditions hold.",
                    confidence=0.94,
                    bbox=BBox(10, 10, 500, 40),
                    source=LineSource.TIER1,
                ),
            ),
            page_confidence=0.94,
            cost_usd=self.cost_per_page_usd,
            providers_used=(self.version,),
        )


def router(**kwargs: object) -> tuple[OcrRouter, FakeProvider]:
    provider = kwargs.pop("provider", None) or FakeProvider()
    kwargs.setdefault("sleep", lambda _: None)  # no real waiting in tests
    return OcrRouter(provider, **kwargs), provider  # type: ignore[arg-type]


HINTS = OcrHints(rubric_lexicon=("deadlock", "mutual exclusion"))


# --- caching, which is what makes re-runs free -----------------------------


def test_a_second_read_of_the_same_page_does_not_call_the_provider() -> None:
    r, provider = router()
    r.recognise(b"page-bytes", HINTS)
    r.recognise(b"page-bytes", HINTS)
    assert provider.calls == 1


def test_a_cached_result_reports_zero_cost() -> None:
    """spec.md §2.3: re-running costs $0. Returning the original price would
    make a re-run look like new spend and corrupt every cost report."""
    r, _ = router()
    first = r.recognise(b"page-bytes", HINTS)
    second = r.recognise(b"page-bytes", HINTS)

    assert first.cost_usd > 0
    assert second.cost_usd == 0.0
    assert second.from_cache is True
    assert first.from_cache is False


def test_a_cached_result_is_otherwise_identical() -> None:
    r, _ = router()
    first = r.recognise(b"page-bytes", HINTS)
    second = r.recognise(b"page-bytes", HINTS)
    assert second.lines == first.lines
    assert second.page_confidence == first.page_confidence


def test_a_different_page_is_a_different_call() -> None:
    r, provider = router()
    r.recognise(b"page-one", HINTS)
    r.recognise(b"page-two", HINTS)
    assert provider.calls == 2


# --- the cache key ---------------------------------------------------------


def test_the_key_covers_the_image() -> None:
    p = FakeProvider()
    assert cache_key(b"a", p, HINTS) != cache_key(b"b", p, HINTS)


def test_the_key_covers_the_provider_version() -> None:
    """A provider upgrade must invalidate its own history, or one exam gets
    marked partly by two different models."""
    old, new = FakeProvider(), FakeProvider()
    new.version = "fake-v2@2026-08"  # type: ignore[misc]
    assert cache_key(b"page", old, HINTS) != cache_key(b"page", new, HINTS)


def test_lexicon_order_does_not_change_the_key() -> None:
    """Otherwise the same request phrased differently pays twice for one
    answer."""
    p = FakeProvider()
    a = OcrHints(rubric_lexicon=("deadlock", "starvation"))
    b = OcrHints(rubric_lexicon=("starvation", "deadlock"))
    assert cache_key(b"page", p, a) == cache_key(b"page", p, b)


def test_routing_only_hints_do_not_change_the_key() -> None:
    """`max_tier2_lines_per_page` changes what the router does with the answer,
    not what the answer is."""
    p = FakeProvider()
    a = OcrHints(max_tier2_lines_per_page=10)
    b = OcrHints(max_tier2_lines_per_page=30)
    assert cache_key(b"page", p, a) == cache_key(b"page", p, b)


def test_the_key_is_deterministic_across_calls() -> None:
    p = FakeProvider()
    assert cache_key(b"page", p, HINTS) == cache_key(b"page", p, HINTS)


# --- retry -----------------------------------------------------------------


def test_a_transient_failure_is_retried() -> None:
    r, provider = router(provider=FakeProvider(fail_times=2))
    result = r.recognise(b"page", HINTS)
    assert provider.calls == 3
    assert result.page_confidence > 0


def test_retries_are_bounded() -> None:
    r, provider = router(provider=FakeProvider(fail_times=99), max_retries=3)
    with pytest.raises(ProviderError):
        r.recognise(b"page", HINTS)
    assert provider.calls == 3


def test_a_refusal_is_not_retried() -> None:
    """Retrying a refusal produces the same refusal and pays for it each time."""
    r, provider = router(provider=FakeProvider(fail_times=99, error=ProviderRefusedError))
    with pytest.raises(ProviderRefusedError):
        r.recognise(b"page", HINTS)
    assert provider.calls == 1


def test_backoff_is_jittered() -> None:
    """Without jitter every worker that failed together retries together, and
    a provider recovering from a blip is knocked over again immediately."""
    r, _ = router()
    delays = {r._backoff(2) for _ in range(50)}
    assert len(delays) > 40, "backoff appears to be constant"


def test_backoff_grows_with_attempts() -> None:
    r, _ = router()
    early = max(r._backoff(0) for _ in range(200))
    late = max(r._backoff(4) for _ in range(200))
    assert late > early


# --- circuit breaker -------------------------------------------------------


def test_the_circuit_opens_after_consecutive_failures() -> None:
    breaker = CircuitBreaker(threshold=3)
    for _ in range(3):
        breaker.record_failure(now=100.0)
    assert breaker.is_open

    with pytest.raises(CircuitOpenError):
        breaker.before_call(now=100.0)


def test_an_intermittent_error_rate_does_not_trip_it() -> None:
    """Only *consecutive* failures count. Occasional errors are normal and
    should not withhold every subsequent call."""
    breaker = CircuitBreaker(threshold=3)
    for _ in range(10):
        breaker.record_failure()
        breaker.record_success()
    assert not breaker.is_open


def test_the_circuit_half_opens_after_its_interval() -> None:
    breaker = CircuitBreaker(threshold=2, reset_after_seconds=30.0)
    breaker.record_failure(now=0.0)
    breaker.record_failure(now=0.0)

    with pytest.raises(CircuitOpenError):
        breaker.before_call(now=10.0)

    breaker.before_call(now=31.0)  # one probe allowed through


def test_the_open_circuit_says_when_it_will_retry() -> None:
    breaker = CircuitBreaker(threshold=1, reset_after_seconds=30.0)
    breaker.record_failure(now=0.0)
    with pytest.raises(CircuitOpenError, match="retrying in"):
        breaker.before_call(now=5.0)


# --- cost ------------------------------------------------------------------


def test_the_cap_is_checked_before_spending() -> None:
    """A cap checked afterwards reports the overspend it failed to prevent."""
    meter = CostMeter(cap_usd=0.001)  # less than one page
    r, provider = router(meter=meter)

    with pytest.raises(CostCapExceededError):
        r.recognise(b"page", HINTS)
    assert provider.calls == 0, "the provider was called despite the cap"


def test_spend_accumulates() -> None:
    meter = CostMeter(cap_usd=1.0)
    r, _ = router(meter=meter)
    r.recognise(b"page-one", HINTS)
    r.recognise(b"page-two", HINTS)
    assert meter.spent_usd == pytest.approx(0.003)


def test_a_cache_hit_does_not_consume_budget() -> None:
    """The whole point of the cache: reprocessing an exam after a model change
    must not re-spend the original budget."""
    meter = CostMeter(cap_usd=1.0)
    r, _ = router(meter=meter)
    r.recognise(b"page", HINTS)
    before = meter.spent_usd
    r.recognise(b"page", HINTS)
    assert meter.spent_usd == before


def test_remaining_budget_never_goes_negative() -> None:
    meter = CostMeter(cap_usd=0.002, spent_usd=0.005)
    assert meter.remaining_usd == 0.0


# --- the cache itself ------------------------------------------------------


def test_the_cache_is_a_plain_mapping() -> None:
    cache = InMemoryCache()
    assert cache.get("missing") is None
    assert len(cache) == 0
