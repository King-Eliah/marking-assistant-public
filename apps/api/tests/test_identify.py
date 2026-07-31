"""Reading a page's identity, including against the real photographs.

These two files closed the stage 2 gate: a booklet printed on a real printer,
photographed on a real phone, whose QR decodes back to exactly the UUIDs the
generator wrote. Both needed rectification first — neither decoded raw — which
is why `identify` takes both images and prefers the flattened one.
"""

from __future__ import annotations

import glob
import os
import uuid

import cv2
import numpy as np
import pytest

from app.engines.booklet.markers import detect
from app.engines.booklet.payload import BookletPayload
from app.engines.ingest.identify import (
    PageIdentity,
    UnidentifiablePageError,
    identify,
)
from app.engines.ingest.warp import rectify

REAL = sorted(glob.glob(os.path.expanduser("~/Desktop/booklet-test/*.jpg")))

#: What the sample booklet was generated with.
SAMPLE_BOOKLET = uuid.UUID("11111111-2222-3333-4444-555555555555")
SAMPLE_EXAM = uuid.UUID("66666666-7777-8888-9999-aaaaaaaaaaaa")


def blank(size: int = 400) -> np.ndarray:
    return np.full((size, size), 255, dtype=np.uint8)


# --- refusing to guess -----------------------------------------------------


def test_a_page_with_no_qr_is_refused() -> None:
    """No safe fallback exists. Assigning the page to a neighbouring booklet
    would produce a plausible script holding another student's answers."""
    with pytest.raises(UnidentifiablePageError, match="cannot be assigned"):
        identify(blank(), blank())


def test_the_refusal_says_both_attempts_failed() -> None:
    with pytest.raises(UnidentifiablePageError, match="before or after"):
        identify(blank(), blank())


def test_a_foreign_qr_is_not_treated_as_a_booklet() -> None:
    """A sticker, a form, another system's label. Reads fine, means nothing
    here, and must not be interpreted generously."""
    import qrcode

    img = qrcode.make("https://example.com/not-a-booklet")
    arr = np.array(img.convert("L"), dtype=np.uint8)
    arr = cv2.resize(arr, (400, 400), interpolation=cv2.INTER_NEAREST)

    with pytest.raises(UnidentifiablePageError):
        identify(arr, arr)


def test_two_different_readings_are_refused_rather_than_picked_between() -> None:
    """If raw and rectified disagree, one is wrong and there is no way to know
    which. Choosing either risks filing the page under the wrong booklet."""
    import io

    import qrcode

    def render(page_no: int) -> np.ndarray:
        payload = BookletPayload(
            booklet_id=SAMPLE_BOOKLET, exam_id=SAMPLE_EXAM, page_no=page_no, page_total=3
        )
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(payload.encode())
        qr.make(fit=True)
        buf = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
        return cv2.imdecode(np.frombuffer(buf.getvalue(), np.uint8), cv2.IMREAD_GRAYSCALE)

    with pytest.raises(UnidentifiablePageError, match="Refusing to choose"):
        identify(render(1), render(2))


# --- the real photographs --------------------------------------------------


@pytest.mark.skipif(not REAL, reason="the reference photographs are not on this machine")
@pytest.mark.parametrize("path", REAL)
def test_a_real_photograph_identifies_its_page(path: str) -> None:
    """The stage 2 acceptance gate, on paper.

    A printed booklet, photographed by hand, decoding back to the exact UUIDs
    the generator wrote.
    """
    gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
    found = detect(gray)
    assert len(found) == 4, "all four fiducials must be found first"

    result = identify(gray, rectify(gray, found).image)

    assert isinstance(result, PageIdentity)
    assert result.payload.booklet_id == SAMPLE_BOOKLET
    assert result.payload.exam_id == SAMPLE_EXAM
    assert 1 <= result.payload.page_no <= result.payload.page_total


@pytest.mark.skipif(not REAL, reason="the reference photographs are not on this machine")
def test_the_real_photographs_needed_rectifying_first() -> None:
    """Why `identify` takes both images and prefers the flattened one.

    Neither of these decoded raw. Both decoded once the perspective was
    removed, at 79 and 86 DPI — resolutions where the raw image simply does
    not give the decoder enough to work with.
    """
    needed_rectifying = 0
    for path in REAL:
        gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
        result = identify(gray, rectify(gray, detect(gray)).image)
        if not result.decoded_before_rectifying:
            needed_rectifying += 1

    assert needed_rectifying == len(REAL)


@pytest.mark.skipif(len(REAL) < 2, reason="need both reference photographs")
def test_the_two_real_pages_are_distinct_pages_of_one_booklet() -> None:
    """Page ordering and missing-page detection both rest on this."""
    pages = []
    for path in REAL:
        gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
        pages.append(identify(gray, rectify(gray, detect(gray)).image).payload)

    assert len({p.booklet_id for p in pages}) == 1, "same booklet"
    assert len({p.page_no for p in pages}) == len(pages), "different pages"
    assert len({p.page_total for p in pages}) == 1, "agreeing on the total"
