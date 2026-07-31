"""Fiducial detection, tested against synthesised photographs.

The claim spec.md §1.1 makes is that four known markers turn perspective
correction into an exact homography. That claim is only worth anything if the
markers survive being photographed, so these tests build a page at real print
DPI, distort it the way a hand-held phone would, and require all four to come
back.

Testing the generator against its own detector is the point: a booklet whose
markers this project cannot read is useless regardless of how correct the PDF
looks.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.engines.booklet.layout import (
    FIDUCIAL_IDS,
    FIDUCIAL_SIZE_MM,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    expected_dpi,
    fiducial_centres_mm,
    fiducial_origins_mm,
)
from app.engines.booklet.markers import detect, marker_bitmap


def render_page(dpi: float) -> np.ndarray:
    """A white A4 page with the four corner fiducials, at a given DPI.

    Stands in for a flat scan. `photograph()` then degrades it.
    """
    px_per_mm = dpi / 25.4
    width = int(round(PAGE_WIDTH_MM * px_per_mm))
    height = int(round(PAGE_HEIGHT_MM * px_per_mm))
    page = np.full((height, width), 255, dtype=np.uint8)

    side = int(round(FIDUCIAL_SIZE_MM * px_per_mm))

    for marker_id, (x_mm, y_mm) in fiducial_origins_mm().items():
        raw = np.frombuffer(marker_bitmap(marker_id), dtype=np.uint8)
        marker = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
        marker = cv2.resize(marker, (side, side), interpolation=cv2.INTER_NEAREST)

        x = int(round(x_mm * px_per_mm))
        # PDF origin is bottom-left; image origin is top-left.
        y = height - int(round(y_mm * px_per_mm)) - side
        page[y : y + side, x : x + side] = marker

    return page


def photograph(page: np.ndarray, *, tilt: float = 0.0, blur: int = 0, dim: float = 1.0):
    """Degrade a flat page the way a hand-held camera would.

    `tilt` is the corner displacement as a fraction of page width — a phone
    held by one hand over a desk is routinely 3-8%.
    """
    height, width = page.shape[:2]
    shift = width * tilt

    source = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    target = np.float32(
        [
            [shift, shift * 0.5],
            [width - shift * 0.5, 0],
            [width, height - shift],
            [shift * 0.7, height],
        ]
    )
    warped = cv2.warpPerspective(
        page,
        cv2.getPerspectiveTransform(source, target),
        (width, height),
        borderValue=255,
    )

    if blur:
        warped = cv2.GaussianBlur(warped, (blur | 1, blur | 1), 0)
    if dim != 1.0:
        warped = np.clip(warped.astype(np.float32) * dim, 0, 255).astype(np.uint8)
    return warped


# ---------------------------------------------------------------------------


def test_all_four_markers_are_found_on_a_flat_page() -> None:
    found = detect(render_page(150))
    assert set(found) == set(FIDUCIAL_IDS)


def test_each_corner_has_a_distinct_id() -> None:
    """Orientation is read from *which* ids appear, so they cannot collide.

    With distinct ids a page photographed upside down still resolves; with
    duplicates it would need guessing from geometry.
    """
    assert len(set(FIDUCIAL_IDS)) == 4


def test_markers_land_at_their_declared_positions() -> None:
    """The generator and `layout` must agree, or the homography maps onto the
    wrong coordinates while looking perfectly valid."""
    dpi = 150
    px_per_mm = dpi / 25.4
    page = render_page(dpi)
    height = page.shape[0]

    found = detect(page)
    for marker_id, (cx_mm, cy_mm) in fiducial_centres_mm().items():
        centre = found[marker_id].mean(axis=0)
        expected_x = cx_mm * px_per_mm
        expected_y = height - cy_mm * px_per_mm
        assert abs(centre[0] - expected_x) < 3, marker_id
        assert abs(centre[1] - expected_y) < 3, marker_id


@pytest.mark.parametrize("dpi", [100, 150, 200, 300])
def test_detection_holds_across_realistic_capture_resolutions(dpi: int) -> None:
    assert set(detect(render_page(dpi))) == set(FIDUCIAL_IDS)


@pytest.mark.parametrize("tilt", [0.02, 0.05, 0.08])
def test_detection_survives_a_hand_held_angle(tilt: float) -> None:
    found = detect(photograph(render_page(200), tilt=tilt))
    assert set(found) == set(FIDUCIAL_IDS), f"lost markers at {tilt:.0%} tilt"


def test_detection_survives_mild_blur_and_poor_light() -> None:
    """An exam hall is not a photography studio."""
    found = detect(photograph(render_page(200), tilt=0.04, blur=3, dim=0.65))
    assert set(found) == set(FIDUCIAL_IDS)


def test_a_page_with_a_missing_corner_is_detectably_incomplete() -> None:
    """A folded or clipped corner must be visible as missing rather than
    silently producing a three-point homography."""
    page = render_page(150)
    page[:200, :200] = 255  # obliterate the top-left marker

    found = detect(page)
    assert len(found) == 3
    assert set(FIDUCIAL_IDS) - set(found)


def test_a_blank_page_yields_no_markers() -> None:
    blank = np.full((1754, 1240), 255, dtype=np.uint8)
    assert detect(blank) == {}


def test_expected_dpi_is_computable_from_the_known_page_width() -> None:
    """This is what buys real thresholds instead of magic pixel counts."""
    assert round(expected_dpi(1240)) == 150
    assert round(expected_dpi(2480)) == 300
