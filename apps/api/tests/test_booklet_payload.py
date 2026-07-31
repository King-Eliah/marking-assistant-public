"""The QR payload.

A page assembled into the wrong script is a mark awarded to the wrong student,
so decoding is strict: anything not exactly right is refused rather than
interpreted generously.
"""

from __future__ import annotations

import uuid

import pytest

from app.engines.booklet.payload import (
    PAYLOAD_VERSION,
    BookletPayload,
    InvalidPayloadError,
    decode,
)

BOOKLET = uuid.uuid4()
EXAM = uuid.uuid4()


def test_round_trip() -> None:
    original = BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=2, page_total=8)
    assert decode(original.encode()) == original


def test_encoding_is_deterministic() -> None:
    a = BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=1, page_total=4)
    b = BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=1, page_total=4)
    assert a.encode() == b.encode()


def test_the_payload_stays_short() -> None:
    """Length drives QR version, which drives module size at a fixed 26 mm.

    A larger version means smaller modules and a materially worse chance of
    decoding from a phone photo in bad light.
    """
    payload = BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=12, page_total=99)
    assert len(payload.encode()) <= 80


def test_no_student_identity_is_encodable() -> None:
    """Booklets are anonymous by design — the payload has nowhere to put a name."""
    fields = BookletPayload.__dataclass_fields__
    assert set(fields) == {"booklet_id", "exam_id", "page_no", "page_total"}


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not a payload",
        "MA1:short:short:1:2",
        f"MA0:{BOOKLET.hex}:{EXAM.hex}:1:2",  # unknown version
        f"MA1:{BOOKLET.hex}:{EXAM.hex}:1",  # truncated
        f"MA1:{BOOKLET.hex}:{EXAM.hex}:1:2:extra",
        f"MA1:{BOOKLET.hex.upper()}:{EXAM.hex}:1:2",  # wrong case
        f"MA1:{BOOKLET.hex}:{EXAM.hex}:x:2",
    ],
)
def test_malformed_payloads_are_refused(raw: str) -> None:
    with pytest.raises(InvalidPayloadError):
        decode(raw)


def test_an_unknown_version_is_refused_rather_than_guessed() -> None:
    """A scanner meeting a future layout must stop, not assemble pages it does
    not understand."""
    with pytest.raises(InvalidPayloadError, match=PAYLOAD_VERSION):
        decode(f"MA9:{BOOKLET.hex}:{EXAM.hex}:1:2")


@pytest.mark.parametrize(("page_no", "page_total"), [(0, 4), (5, 4), (-1, 4), (1, 0)])
def test_impossible_page_numbers_are_rejected_at_construction(
    page_no: int, page_total: int
) -> None:
    """Catching this at construction means an impossible QR is never printed."""
    with pytest.raises(InvalidPayloadError):
        BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=page_no, page_total=page_total)


def test_surrounding_whitespace_is_tolerated() -> None:
    """Some scanners append a newline; that is not a corrupt payload."""
    payload = BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=1, page_total=1)
    assert decode(f"  {payload.encode()}\n") == payload
