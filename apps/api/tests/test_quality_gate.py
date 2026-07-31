"""The capture quality gate.

The resolution threshold is the interesting one, because it came from a real
failure rather than from a guess. Three photographs of a printed booklet were
recompressed to 720x1280 in transit — about 50 DPI. All four fiducials still
detected; the QR was unreadable. Sweeping the decoder found the cliff between
75 and 90 DPI, and the gate sits at 120 with margin.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.engines.booklet.layout import PAGE_WIDTH_MM
from app.engines.ingest.quality import (
    MIN_DPI_HARD,
    MIN_DPI_REJECT,
    MIN_DPI_WARN,
    Verdict,
    assess,
    measure_brightness,
    measure_dpi,
    measure_sharpness,
    recommended_capture_pixels,
)


def sharp_page(size: int = 900) -> np.ndarray:
    """A high-contrast synthetic page — plenty of edges, so clearly in focus."""
    page = np.full((size, size), 245, dtype=np.uint8)
    for y in range(40, size - 40, 30):
        page[y : y + 3, 40 : size - 40] = 20
    return page


def good(**overrides: object) -> dict[str, object]:
    args: dict[str, object] = {
        "image": sharp_page(),
        "dpi": 200.0,
        "skew_degrees": 1.0,
        "keystone": 0.95,
        "fiducials_found": 4,
    }
    args.update(overrides)
    return args


# --- resolution ------------------------------------------------------------


def test_a_good_capture_is_accepted() -> None:
    assert assess(**good()).verdict is Verdict.ACCEPT  # type: ignore[arg-type]


def test_the_recompressed_photograph_is_rejected() -> None:
    """The exact case that produced these thresholds: ~50 DPI, fiducials fine,
    QR unreadable. Accepting it would send an unidentifiable page down the
    pipeline."""
    report = assess(**good(dpi=50.0))  # type: ignore[arg-type]
    assert report.verdict is Verdict.REJECT
    assert any("low-resolution" in r for r in report.reasons)


def test_the_rejection_says_what_to_do_about_it() -> None:
    """A capture app showing "quality check failed" gets the same bad photo
    again. The message has to name the fix."""
    report = assess(**good(dpi=50.0))  # type: ignore[arg-type]
    text = " ".join(report.reasons).lower()
    assert "move closer" in text
    assert "shrinking" in text  # the actual cause, in plain words


def test_the_reject_threshold_sits_above_the_measured_cliff() -> None:
    """MIN_DPI_HARD is where the QR provably stops decoding. The gate must sit
    above it, not on it, because a real photograph also carries blur."""
    assert MIN_DPI_REJECT > MIN_DPI_HARD
    assert MIN_DPI_WARN > MIN_DPI_REJECT


@pytest.mark.parametrize(
    ("dpi", "expected"),
    [
        (50.0, Verdict.REJECT),
        (90.0, Verdict.REJECT),  # decodable in the lab, no margin in the field
        (119.0, Verdict.REJECT),
        (130.0, Verdict.WARN),
        (200.0, Verdict.ACCEPT),
    ],
)
def test_resolution_bands(dpi: float, expected: Verdict) -> None:
    assert assess(**good(dpi=dpi)).verdict is expected  # type: ignore[arg-type]


def test_the_recommended_capture_size_clears_the_gate() -> None:
    px = recommended_capture_pixels()
    assert measure_dpi(px, PAGE_WIDTH_MM) >= MIN_DPI_WARN


# --- the other measures ----------------------------------------------------


def test_a_missing_fiducial_is_a_rejection() -> None:
    """Three points cannot define the homography, and a page warped from a
    guess looks correct while mapping onto the wrong coordinates."""
    report = assess(**good(fiducials_found=3))  # type: ignore[arg-type]
    assert report.verdict is Verdict.REJECT
    assert any("corner markers" in r for r in report.reasons)


def test_a_blurred_page_is_rejected() -> None:
    blurred = cv2.GaussianBlur(sharp_page(), (31, 31), 0)
    report = assess(**good(image=blurred))  # type: ignore[arg-type]
    assert report.verdict is Verdict.REJECT
    assert any("blur" in r.lower() for r in report.reasons)


def test_a_dark_page_is_rejected_with_a_usable_reason() -> None:
    dark = (sharp_page().astype(np.float32) * 0.10).astype(np.uint8)
    report = assess(**good(image=dark))  # type: ignore[arg-type]
    assert report.verdict is Verdict.REJECT
    assert any("shadow" in r.lower() for r in report.reasons)


def test_a_blown_out_page_is_rejected() -> None:
    bright = np.full((900, 900), 250, dtype=np.uint8)
    report = assess(**good(image=bright))  # type: ignore[arg-type]
    assert report.verdict is Verdict.REJECT


def test_a_hand_held_angle_only_warns() -> None:
    """The real photographs measured 0.85-0.87 keystone. That is normal and
    the homography corrects it exactly — rejecting it would make the system
    unusable in practice."""
    assert assess(**good(keystone=0.86)).verdict is Verdict.ACCEPT  # type: ignore[arg-type]


def test_a_steep_angle_warns_rather_than_rejects() -> None:
    report = assess(**good(keystone=0.55))  # type: ignore[arg-type]
    assert report.verdict is Verdict.WARN
    assert report.accepted


def test_a_rotated_page_warns() -> None:
    report = assess(**good(skew_degrees=25.0))  # type: ignore[arg-type]
    assert report.verdict is Verdict.WARN


def test_warnings_do_not_block_the_pipeline() -> None:
    """A warned page is still processed. Only a rejection stops it, because a
    retake costs the person holding the phone another trip to the script."""
    assert assess(**good(dpi=130.0)).accepted  # type: ignore[arg-type]
    assert not assess(**good(dpi=50.0)).accepted  # type: ignore[arg-type]


def test_the_worst_problem_is_reported_even_when_several_exist() -> None:
    dark_blurred = cv2.GaussianBlur(
        (sharp_page().astype(np.float32) * 0.1).astype(np.uint8), (31, 31), 0
    )
    report = assess(**good(image=dark_blurred, dpi=50.0, fiducials_found=2))  # type: ignore[arg-type]
    assert report.verdict is Verdict.REJECT
    assert len(report.reasons) >= 3  # every fault named, not just the first


# --- the measurements themselves -------------------------------------------


def test_dpi_is_measured_from_a_known_physical_distance() -> None:
    """1240 px across a 210mm page is 150 DPI. Computable only because the
    booklet fixes the page size."""
    assert round(measure_dpi(1240, PAGE_WIDTH_MM)) == 150


def test_a_zero_span_is_refused_rather_than_dividing_by_zero() -> None:
    with pytest.raises(ValueError, match="positive"):
        measure_dpi(1000, 0)


def test_sharpness_separates_focused_from_blurred() -> None:
    assert measure_sharpness(sharp_page()) > measure_sharpness(
        cv2.GaussianBlur(sharp_page(), (31, 31), 0)
    )


def test_brightness_tracks_exposure() -> None:
    assert measure_brightness(np.full((10, 10), 200, np.uint8)) == pytest.approx(200)
