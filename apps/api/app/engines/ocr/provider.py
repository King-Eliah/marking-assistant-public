"""The OCR provider boundary — spec.md §2.4.

**Never call a vendor SDK from business logic.** Everything external goes
through this interface, for reasons that matter more than they look:

- vendor pricing and availability change, and swapping should be one config line
- an on-prem institution needs a self-hosted implementation of the same shape
- the evaluation harness must run every provider over one golden set
- cost accounting and rate limiting belong in one place, not scattered

`version` is pinned and participates in every cache key, so upgrading a
provider invalidates its cached results rather than silently mixing outputs
from two different models in one exam (I5).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.engines.ocr.contracts import OcrHints, OcrResult


class ProviderError(Exception):
    """The provider could not answer. Retryable unless stated otherwise."""


class ProviderTimeoutError(ProviderError):
    """No answer within the deadline."""


class ProviderRefusedError(ProviderError):
    """The provider answered, and the answer was a refusal.

    Distinct from a timeout because it is *not* retryable: sending the same
    request again produces the same refusal and spends money doing it.
    """


@runtime_checkable
class OcrProvider(Protocol):
    """One OCR engine.

    Implementations are thin. Anything that is policy rather than transport —
    retry, caching, cost limits, tier decisions — lives in the router, so that
    a second provider cannot accidentally implement it differently.
    """

    @property
    def name(self) -> str:
        """Stable identifier, e.g. `google_vision`."""
        ...

    @property
    def version(self) -> str:
        """Pinned version, e.g. `google-vision-v1@2026-07`.

        Part of every cache key. Changing it must be a deliberate act with a
        cache invalidation behind it.
        """
        ...

    @property
    def cost_per_page_usd(self) -> float:
        """Published price for one page. Used for budgeting and the cost meter,
        never for choosing a provider mid-exam — a script marked partly by one
        engine and partly by another is not defensible."""
        ...

    def recognise(self, image: bytes, hints: OcrHints) -> OcrResult:
        """Read one page. Raises `ProviderError` on failure."""
        ...
