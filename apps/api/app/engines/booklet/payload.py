"""The QR payload.

spec.md §1.1: the QR encodes `{booklet_uuid, page_no, page_total, exam_id}`,
and doing so makes page ordering, duplicate detection, missing-page detection
and script assembly trivial and error-free.

Deliberately *not* JSON. A compact fixed format keeps the QR to a low version,
which means larger modules at 26 mm and a much better chance of decoding from
a phone photograph taken in a badly lit exam hall. Robustness here is worth
more than readability — nothing human ever reads this string.

The payload carries no student identity. Booklets are anonymous by design
(spec.md §1.1); identity is resolved only at export, through a separate
mapping table.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Final

#: Bumping this is how a future layout change stays detectable. A scanner
#: reading an unknown version must refuse rather than guess, because guessing
#: means assembling a script from pages it does not understand.
PAYLOAD_VERSION: Final[str] = "MA1"

_SEPARATOR: Final[str] = ":"

#: uuid hex without dashes, so 32 chars each rather than 36.
_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^MA1:(?P<booklet>[0-9a-f]{32}):(?P<exam>[0-9a-f]{32}):(?P<page>\d+):(?P<total>\d+)$"
)


class InvalidPayloadError(ValueError):
    """The QR content is not a booklet payload this version understands."""


@dataclass(frozen=True, slots=True)
class BookletPayload:
    """What a single page's QR asserts about itself."""

    booklet_id: uuid.UUID
    exam_id: uuid.UUID
    page_no: int
    page_total: int

    def __post_init__(self) -> None:
        if self.page_total < 1:
            raise InvalidPayloadError("page_total must be at least 1")
        if not 1 <= self.page_no <= self.page_total:
            raise InvalidPayloadError(f"page_no {self.page_no} outside 1..{self.page_total}")

    def encode(self) -> str:
        return _SEPARATOR.join(
            (
                PAYLOAD_VERSION,
                self.booklet_id.hex,
                self.exam_id.hex,
                str(self.page_no),
                str(self.page_total),
            )
        )


def decode(raw: str) -> BookletPayload:
    """Parse a scanned payload, or raise.

    Strict by design. A malformed or unknown-version payload must stop the
    pipeline rather than produce a plausible-looking guess: a page assembled
    into the wrong script is a mark awarded to the wrong student, which is the
    worst failure this system can produce.
    """
    match = _PATTERN.match(raw.strip())
    if match is None:
        raise InvalidPayloadError(f"not a {PAYLOAD_VERSION} booklet payload: {raw[:64]!r}")

    return BookletPayload(
        booklet_id=uuid.UUID(hex=match["booklet"]),
        exam_id=uuid.UUID(hex=match["exam"]),
        page_no=int(match["page"]),
        page_total=int(match["total"]),
    )
