"""Engine 1 end to end.

The property that matters most: a page that reaches a marker never carries an
identity region. That is checked here against the real photograph of page 1,
because a synthetic page proves the code path and only real paper proves the
coordinates.
"""

from __future__ import annotations

import glob
import os

import cv2
import numpy as np
import pytest

from app.core.states import ALLOWED, State
from app.engines.booklet.layout import HEADER_BOTTOM_MM, identity_region_mm
from app.engines.ingest.pipeline import IngestedPage, RejectedPage, ingest
from app.engines.ingest.warp import region_px
from tests.test_booklet_fiducials import photograph, render_page

REAL = sorted(glob.glob(os.path.expanduser("~/Desktop/booklet-test/*.jpg")))


def page_one() -> str | None:
    """The real photograph that shows page 1, which is the one with an
    identity box on it."""
    for path in REAL:
        gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
        from app.engines.booklet.markers import detect
        from app.engines.ingest.identify import identify
        from app.engines.ingest.warp import rectify

        try:
            found = detect(gray)
            if len(found) != 4:
                continue
            if identify(gray, rectify(gray, found).image).payload.page_no == 1:
                return path
        except Exception:
            continue
    return None


# --- rejections ------------------------------------------------------------


def test_a_blank_frame_is_rejected_for_missing_markers() -> None:
    blank = np.full((1200, 900), 255, dtype=np.uint8)
    result = ingest(blank)
    assert isinstance(result, RejectedPage)
    assert "corner markers" in result.reasons[0]


def test_a_rejection_moves_the_page_to_quality_rejected() -> None:
    result = ingest(np.full((1200, 900), 255, dtype=np.uint8))
    assert result.next_state is State.QUALITY_REJECTED


def test_quality_rejected_can_still_be_retaken() -> None:
    """The state machine has to allow a second attempt, or a rejected page is
    stranded and the script can never be completed."""
    assert State.PREPROCESSING in ALLOWED[State.QUALITY_REJECTED]


def test_a_page_with_markers_but_no_qr_is_refused() -> None:
    """Fiducials alone are not an identity. A page that cannot say which
    booklet it belongs to cannot be assembled into a script."""
    result = ingest(render_page(200))
    assert isinstance(result, RejectedPage)
    assert any("cannot be assigned" in r or "corner markers" in r for r in result.reasons)


# --- the real photographs --------------------------------------------------


@pytest.mark.skipif(not REAL, reason="the reference photographs are not on this machine")
@pytest.mark.parametrize("path", REAL)
def test_real_photographs_are_rejected_for_resolution_not_for_identity(path: str) -> None:
    """These decode correctly but sit below the resolution floor.

    That combination is the point: Engine 1 knows exactly which page it is
    looking at *and* still refuses it, so the rejection can name the page.
    """
    gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
    result = ingest(gray)

    assert isinstance(result, RejectedPage)
    assert result.quality is not None
    assert any("low-resolution" in r for r in result.reasons)
    # not refused for being unidentifiable
    assert not any("cannot be assigned" in r for r in result.reasons)


@pytest.mark.skipif(not REAL, reason="the reference photographs are not on this machine")
def test_a_real_page_one_has_its_identity_region_removed() -> None:
    """The claim anonymous marking rests on, checked on real paper.

    A synthetic page proves the code path. Only a photograph of the printed
    booklet proves the coordinates line up with where the box was actually
    printed.
    """
    path = page_one()
    if path is None:
        pytest.skip("none of the reference photographs is page 1")

    from app.engines.booklet.markers import detect
    from app.engines.ingest.warp import rectify

    gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
    warped = rectify(gray, detect(gray)).image

    rect = region_px(*identity_region_mm(HEADER_BOTTOM_MM))
    x, y, w, h = rect

    before = warped[y : y + h, x : x + w]
    from app.engines.ingest.warp import redact

    after = redact(warped, rect)[y : y + h, x : x + w]

    # the printed box has ink in it; after redaction the region is blank
    assert before.min() < 200, "expected the printed identity box to be visible"
    assert after.min() == 255, "the identity region was not fully removed"


# --- the successful path ---------------------------------------------------


def synthetic_capture(page_no: int = 1) -> np.ndarray:
    """A rendered booklet page with a real QR, photographed at an angle.

    Built at high DPI so it clears the quality gate — the reference
    photographs deliberately do not.
    """
    import io
    import uuid

    import qrcode

    from app.engines.booklet.layout import (
        CONTENT_MARGIN_MM,
        PAGE_HEIGHT_MM,
        QR_SIZE_MM,
    )
    from app.engines.booklet.payload import BookletPayload

    dpi = 260
    page = render_page(dpi)
    # Real paper photographs around 235-250, never at pure 255. Leaving the
    # synthetic page at 255 makes it 99% clipped, which the overexposure check
    # correctly refuses — the fixture would be testing an impossible image.
    page[page >= 255] = 246
    px_per_mm = dpi / 25.4

    payload = BookletPayload(
        booklet_id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        exam_id=uuid.UUID("66666666-7777-8888-9999-aaaaaaaaaaaa"),
        page_no=page_no,
        page_total=3,
    )
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(payload.encode())
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    symbol = cv2.imdecode(np.frombuffer(buf.getvalue(), np.uint8), cv2.IMREAD_GRAYSCALE)

    side = int(round(QR_SIZE_MM * px_per_mm))
    symbol = cv2.resize(symbol, (side, side), interpolation=cv2.INTER_NEAREST)

    x = int(round(CONTENT_MARGIN_MM * px_per_mm))
    y = page.shape[0] - int(round((PAGE_HEIGHT_MM - CONTENT_MARGIN_MM) * px_per_mm))
    page[y : y + side, x : x + side] = symbol
    return page


def test_a_good_capture_produces_an_ingested_page() -> None:
    result = ingest(synthetic_capture(page_no=2))
    assert isinstance(result, IngestedPage), getattr(result, "reasons", None)
    assert result.payload.page_no == 2
    assert result.next_state is State.OCR_RUNNING


def test_page_one_is_anonymised_and_later_pages_are_not() -> None:
    """Only page 1 carries an identity box, so only page 1 should be redacted.
    Redacting page 2 would destroy an answer for no reason."""
    first = ingest(synthetic_capture(page_no=1))
    later = ingest(synthetic_capture(page_no=2))

    assert isinstance(first, IngestedPage)
    assert isinstance(later, IngestedPage)
    assert first.identity_removed is True
    assert later.identity_removed is False


def test_an_ingested_page_moves_to_ocr() -> None:
    result = ingest(synthetic_capture())
    assert isinstance(result, IngestedPage)
    assert result.next_state in ALLOWED[State.PREPROCESSING]


def test_the_ingested_page_is_the_rectified_one() -> None:
    """Not the original photograph. Handing on the raw frame would defeat both
    the coordinate lookup and the redaction."""
    tilted = photograph(synthetic_capture(), tilt=0.04)
    result = ingest(tilted)
    assert isinstance(result, IngestedPage)
    assert result.image.shape != tilted.shape
    assert result.image.shape == (2339, 1654)
