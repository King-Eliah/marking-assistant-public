"""Routing every OCR call — spec.md §2.4.

One place where timeout, retry with jitter, circuit breaking, cost metering
and caching happen. Providers stay thin transport; policy lives here, so a
second provider cannot implement any of it differently by accident.

The cache is the load-bearing part. Keyed on
`sha256(image_bytes ‖ provider.version ‖ params)`, it makes re-running a page
free — which is what lets the evaluation harness iterate without spending, and
what makes a full reprocess after a model upgrade predictable rather than
frightening (I5).
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Protocol

from app.engines.ocr.contracts import OcrHints, OcrResult
from app.engines.ocr.provider import OcrProvider, ProviderError, ProviderRefusedError

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """The provider is failing and calls are being withheld.

    Better than continuing to try: a provider in a bad state fails slowly,
    so hammering it converts one broken exam into a queue-wide stall while
    still being billed for every attempt.
    """


class OcrCache(Protocol):
    """Content-addressed store for provider results."""

    def get(self, key: str) -> OcrResult | None: ...
    def put(self, key: str, result: OcrResult) -> None: ...


class InMemoryCache:
    """Process-local cache. Real deployments back this with Redis.

    Adequate for tests and for a single worker, and deliberately simple: the
    interface is what matters, since the router must not care where results
    are kept.
    """

    def __init__(self) -> None:
        self._entries: dict[str, OcrResult] = {}

    def get(self, key: str) -> OcrResult | None:
        return self._entries.get(key)

    def put(self, key: str, result: OcrResult) -> None:
        self._entries[key] = result

    def __len__(self) -> int:
        return len(self._entries)


def cache_key(image: bytes, provider: OcrProvider, hints: OcrHints) -> str:
    """`sha256(image ‖ provider.version ‖ params)`.

    The version is included so a provider upgrade invalidates its own history
    rather than serving results from a model that is no longer in use. The
    hints that change the *output* are included; the ones that only change
    routing are not, because two calls differing only in `max_tier2_lines` want
    the same Tier-1 answer.
    """
    digest = hashlib.sha256()
    digest.update(image)
    digest.update(b"\x1f")
    digest.update(provider.version.encode("utf-8"))
    digest.update(b"\x1f")
    digest.update(hints.language.encode("utf-8"))
    digest.update(b"\x1f")
    # Sorted, so a caller listing the same lexicon in a different order still
    # hits the cache rather than paying twice for one answer.
    digest.update("\x1e".join(sorted(hints.rubric_lexicon)).encode("utf-8"))
    return digest.hexdigest()


@dataclass
class CircuitBreaker:
    """Stops calling a provider that is consistently failing.

    Counts consecutive failures only. An intermittent error rate is normal and
    should not trip anything; a provider that has failed five times in a row is
    down, and the sixth call will fail too.
    """

    threshold: int = 5
    reset_after_seconds: float = 30.0
    _failures: int = field(default=0, init=False)
    _opened_at: float | None = field(default=None, init=False)

    def before_call(self, now: float | None = None) -> None:
        if self._opened_at is None:
            return
        # `now if now is not None`, never `now or`: a timestamp of 0.0 is
        # falsy and would silently fall through to the real clock.
        elapsed = (now if now is not None else time.monotonic()) - self._opened_at
        if elapsed < self.reset_after_seconds:
            raise CircuitOpenError(
                f"provider has failed {self._failures} times consecutively; "
                f"retrying in {self.reset_after_seconds - elapsed:.0f}s"
            )
        # Half-open: allow one probe through. A success closes it, a failure
        # re-opens it for another full interval.
        self._opened_at = None

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self, now: float | None = None) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = now if now is not None else time.monotonic()

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None


@dataclass
class CostMeter:
    """Running spend, per tenant.

    Enforced *before* the provider call, never after. A cap checked afterwards
    reports the overspend it failed to prevent.
    """

    cap_usd: float
    spent_usd: float = 0.0

    def check(self, amount: float) -> None:
        if self.spent_usd + amount > self.cap_usd:
            raise CostCapExceededError(
                f"this call would spend ${self.spent_usd + amount:.4f} against a "
                f"${self.cap_usd:.2f} cap"
            )

    def record(self, amount: float) -> None:
        self.spent_usd += amount

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cap_usd - self.spent_usd)


class CostCapExceededError(Exception):
    """The tenant's spending cap would be breached by this call."""


class OcrRouter:
    """The only supported way to reach an OCR provider."""

    def __init__(
        self,
        provider: OcrProvider,
        *,
        cache: OcrCache | None = None,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.5,
        breaker: CircuitBreaker | None = None,
        meter: CostMeter | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.provider = provider
        self.cache = cache if cache is not None else InMemoryCache()
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.breaker = breaker or CircuitBreaker()
        self.meter = meter
        self._sleep = sleep

    def _backoff(self, attempt: int) -> float:
        """Exponential with full jitter.

        Jitter is not decoration: without it, every worker that failed together
        retries together, and a provider recovering from a blip is immediately
        knocked over again by a synchronised thundering herd.
        """
        ceiling = self.base_backoff_seconds * (2**attempt)
        return random.uniform(0, ceiling)

    def recognise(self, image: bytes, hints: OcrHints) -> OcrResult:
        """Read one page, with everything policy-shaped applied around it."""
        key = cache_key(image, self.provider, hints)

        cached = self.cache.get(key)
        if cached is not None:
            # Cost is zeroed on the way out. Returning the original price would
            # make a re-run look like new spend and corrupt the cost report.
            return replace(cached, cost_usd=0.0, from_cache=True)

        if self.meter is not None:
            self.meter.check(self.provider.cost_per_page_usd)

        self.breaker.before_call()

        last_error: ProviderError | None = None
        for attempt in range(self.max_retries):
            try:
                result = self.provider.recognise(image, hints)
            except ProviderRefusedError:
                # Not retryable. The same request produces the same refusal and
                # spends money each time.
                self.breaker.record_failure()
                raise
            except ProviderError as exc:
                last_error = exc
                self.breaker.record_failure()
                if attempt < self.max_retries - 1:
                    self._sleep(self._backoff(attempt))
                continue

            self.breaker.record_success()
            if self.meter is not None:
                self.meter.record(result.cost_usd)
            self.cache.put(key, result)
            return result

        assert last_error is not None
        raise last_error
