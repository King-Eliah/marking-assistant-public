"""Perspective correction.

The claim is that four markers at known positions make rectification exact.
The way to test that is a round trip: distort a page by a known homography,
rectify it, and check the fiducials land back on their declared millimetre
positions. If they do, every other coordinate on the page does too — which is
what lets segmentation and the identity crop work by lookup.
"""

from __future__ import annotations

import glob
import os

import cv2
import numpy as np
import pytest

from app.engines.booklet.layout import (
    HEADER_BOTTOM_MM,
    IDENTITY_BOX_HEIGHT_MM,
    IDENTITY_BOX_WIDTH_MM,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    fiducial_centres_mm,
    identity_region_mm,
)
from app.engines.booklet.markers import detect
from app.engines.ingest.warp import (
    OUTPUT_DPI,
    WarpError,
    crop,
    measure_keystone,
    measure_skew,
    measure_source_dpi,
    rectify,
    redact,
    region_px,
)
from tests.test_booklet_fiducials import photograph, render_page


def rectified(dpi: float = 200, **distortion: float):
    page = render_page(dpi)
    shot = photograph(page, **distortion) if distortion else page
    return rectify(shot, detect(shot))


# --- the round trip --------------------------------------------------------


def test_a_flat_page_rectifies_to_the_page_rectangle() -> None:
    result = rectified()
    expected_w = int(round(PAGE_WIDTH_MM * OUTPUT_DPI / 25.4))
    expected_h = int(round(PAGE_HEIGHT_MM * OUTPUT_DPI / 25.4))
    assert result.size_px == (expected_w, expected_h)


@pytest.mark.parametrize("tilt", [0.0, 0.03, 0.06, 0.09])
def test_fiducials_land_on_their_declared_positions_after_warping(tilt: float) -> None:
    """The whole argument in one assertion.

    A photograph taken at an angle, rectified, must put each marker back at the
    millimetre position the layout declares. Everything downstream inherits
    this accuracy.
    """
    result = rectified(tilt=tilt) if tilt else rectified()
    found = detect(result.image)
    assert len(found) == 4, f"markers lost during warping at {tilt:.0%} tilt"

    px_per_mm = OUTPUT_DPI / 25.4
    height_px = result.image.shape[0]

    for marker_id, (cx_mm, cy_mm) in fiducial_centres_mm().items():
        centre = found[marker_id].mean(axis=0)
        expected_x = cx_mm * px_per_mm
        expected_y = height_px - cy_mm * px_per_mm
        # 2mm at 200 DPI is ~16px; well inside that is exact for our purposes
        assert abs(centre[0] - expected_x) < 12, (
            f"{marker_id} x off by {centre[0] - expected_x:.0f}px"
        )
        assert abs(centre[1] - expected_y) < 12, (
            f"{marker_id} y off by {centre[1] - expected_y:.0f}px"
        )


def test_rectifying_removes_skew() -> None:
    tilted = photograph(render_page(200), tilt=0.06)
    before = abs(measure_skew(detect(tilted)))
    after = abs(measure_skew(detect(rectify(tilted, detect(tilted)).image)))
    assert after < before
    assert after < 1.0


def test_rectifying_removes_perspective() -> None:
    tilted = photograph(render_page(200), tilt=0.08)
    before = measure_keystone(detect(tilted))
    after = measure_keystone(detect(rectify(tilted, detect(tilted)).image))
    assert abs(after - 1.0) < abs(before - 1.0)
    assert abs(after - 1.0) < 0.02


# --- refusing to guess -----------------------------------------------------


def test_three_markers_is_an_error_not_a_best_effort() -> None:
    """An affine transform from three points cannot represent perspective. The
    output would look correct and map onto the wrong coordinates."""
    page = render_page(200)
    found = detect(page)
    del found[0]

    with pytest.raises(WarpError, match="four corner markers"):
        rectify(page, found)


def test_the_error_explains_why_three_is_not_enough() -> None:
    page = render_page(200)
    found = detect(page)
    del found[2]
    with pytest.raises(WarpError, match="perspective"):
        rectify(page, found)


# --- measurements ----------------------------------------------------------


def test_source_dpi_reports_the_original_not_the_output() -> None:
    """A 100 DPI photograph warped to 200 DPI is still a 100 DPI photograph.
    Reporting the output would tell the quality gate what it wants to hear."""
    page = render_page(100)
    result = rectify(page, detect(page))
    assert 95 <= result.source_dpi <= 105
    assert result.dpi == OUTPUT_DPI


def test_source_dpi_matches_a_hand_measurement() -> None:
    page = render_page(150)
    assert 145 <= measure_source_dpi(detect(page)) <= 155


# --- regions ---------------------------------------------------------------


def test_a_layout_region_maps_into_the_page() -> None:
    x, y, w, h = region_px(*identity_region_mm(HEADER_BOTTOM_MM))
    page_w = int(round(PAGE_WIDTH_MM * OUTPUT_DPI / 25.4))
    page_h = int(round(PAGE_HEIGHT_MM * OUTPUT_DPI / 25.4))

    assert x >= 0 and x + w <= page_w
    assert y >= 0 and y + h <= page_h
    assert w == pytest.approx(IDENTITY_BOX_WIDTH_MM * OUTPUT_DPI / 25.4, abs=1)
    assert h == pytest.approx(IDENTITY_BOX_HEIGHT_MM * OUTPUT_DPI / 25.4, abs=1)


def test_cropping_returns_the_requested_size() -> None:
    result = rectified()
    rect = region_px(*identity_region_mm(HEADER_BOTTOM_MM))
    patch = crop(result.image, rect)
    assert patch.shape[1] == rect[2]
    assert patch.shape[0] == rect[3]


def test_a_region_off_the_page_is_refused() -> None:
    result = rectified()
    with pytest.raises(WarpError, match="outside the page"):
        crop(result.image, (99_999, 99_999, 10, 10))


# --- redaction, which is what makes marking anonymous ----------------------


def test_redaction_blanks_the_identity_region() -> None:
    result = rectified()
    rect = region_px(*identity_region_mm(HEADER_BOTTOM_MM))
    cleaned = redact(result.image, rect)

    x, y, w, h = rect
    assert cleaned[y : y + h, x : x + w].min() == 255


def test_redaction_leaves_the_original_untouched() -> None:
    """Returns a copy deliberately. Mutating in place would let a caller hand
    on the same array it was told to sanitise — the one mistake that defeats
    anonymous marking entirely."""
    result = rectified()
    rect = region_px(*identity_region_mm(HEADER_BOTTOM_MM))
    before = result.image.copy()

    redact(result.image, rect)
    assert np.array_equal(result.image, before)


def test_redaction_does_not_touch_the_answer_area() -> None:
    """Too large a redaction destroys handwriting instead of protecting it."""
    result = rectified()
    rect = region_px(*identity_region_mm(HEADER_BOTTOM_MM))
    cleaned = redact(result.image, rect)

    below = rect[1] + rect[3] + 40
    assert not np.array_equal(cleaned[below:, :], np.full_like(cleaned[below:, :], 255)), (
        "everything below the identity box was wiped"
    )


# --- against the real photographs ------------------------------------------

REAL = sorted(
    glob.glob(os.path.expanduser("~/Downloads/Telegram Desktop/photo_2026-07-31_14-45-*.jpg"))
)


@pytest.mark.skipif(not REAL, reason="the reference photographs are not on this machine")
@pytest.mark.parametrize("path", REAL)
def test_real_photographs_rectify(path: str) -> None:
    """Printed on a real printer, photographed on a real phone, at an ordinary
    hand-held angle. All four markers were found on every one of these."""
    gray = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
    found = detect(gray)
    assert len(found) == 4

    result = rectify(gray, found)
    assert result.size_px == (1654, 2339)
    # measured 0.849-0.865 on these, a normal hand-held angle
    assert 0.80 < result.keystone < 0.95
    assert abs(result.skew_degrees) < 5

    # and the markers come back square afterwards
    after = detect(result.image)
    assert len(after) == 4
    assert abs(measure_skew(after)) < 1.5
    assert abs(measure_keystone(after) - 1.0) < 0.05
