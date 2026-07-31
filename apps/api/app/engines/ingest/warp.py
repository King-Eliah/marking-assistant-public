"""Perspective correction from the four fiducials — Engine 1, spec.md §1.3.

This is the payoff for the structured booklet. Four markers at known
millimetre positions give four exact point correspondences, so correcting a
hand-held photograph is a solved homography rather than a guessed contour.
Deskew comes free: the same transform that removes perspective also removes
rotation.

Everything downstream depends on this being exact. After warping, a question
box is not "somewhere around here" — it is at a computable rectangle, which is
what turns segmentation into a lookup and lets the identity region be cropped
by coordinate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

import cv2
import numpy as np

from app.engines.booklet.layout import (
    FIDUCIAL_IDS,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    fiducial_centres_mm,
)

#: Narrowed to the numeric dtypes OpenCV accepts, rather than Any: the
#: cv2 stubs reject a fully generic ndarray, and widening it here would
#: only move the error to the call site.
ImageArray = np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]]

#: Resolution of the warped output. 200 DPI is comfortably above the quality
#: gate's floor and keeps a full page near 1654x2339 — enough for OCR without
#: making every stored page needlessly large.
OUTPUT_DPI: Final[float] = 200.0


class WarpError(Exception):
    """The page could not be rectified.

    Raised rather than returning a best-effort image: a page warped from
    incomplete information looks entirely correct and maps onto the wrong
    coordinates, which would attribute handwriting to the wrong question.
    """


@dataclass(frozen=True, slots=True)
class WarpResult:
    """A rectified page and what was measured getting there."""

    image: ImageArray
    dpi: float
    source_dpi: float
    skew_degrees: float
    keystone: float

    @property
    def size_px(self) -> tuple[int, int]:
        return self.image.shape[1], self.image.shape[0]


def _page_size_px(dpi: float) -> tuple[int, int]:
    px_per_mm = dpi / 25.4
    return (
        int(round(PAGE_WIDTH_MM * px_per_mm)),
        int(round(PAGE_HEIGHT_MM * px_per_mm)),
    )


def measure_skew(corners: dict[int, ImageArray]) -> float:
    """Rotation of the page's top edge, in degrees."""
    top_left = corners[FIDUCIAL_IDS[0]].mean(axis=0)
    top_right = corners[FIDUCIAL_IDS[1]].mean(axis=0)
    dx, dy = top_right - top_left
    return math.degrees(math.atan2(float(dy), float(dx)))


def measure_keystone(corners: dict[int, ImageArray]) -> float:
    """How square the page looks, as top edge over bottom edge.

    1.0 is flat-on. Below 1.0 means the top of the page is further from the
    camera, which is what a phone held over a desk produces.
    """
    centres = {i: corners[i].mean(axis=0) for i in FIDUCIAL_IDS}
    top = float(np.linalg.norm(centres[FIDUCIAL_IDS[1]] - centres[FIDUCIAL_IDS[0]]))
    bottom = float(np.linalg.norm(centres[FIDUCIAL_IDS[2]] - centres[FIDUCIAL_IDS[3]]))
    if bottom == 0:
        raise WarpError("the two bottom markers are at the same point")
    return top / bottom


def measure_source_dpi(corners: dict[int, ImageArray]) -> float:
    """Effective DPI of the original photograph.

    Taken across the top edge, whose true length in millimetres is known from
    the layout. This is the number the quality gate judges.
    """
    centres_mm = fiducial_centres_mm()
    top_left, top_right = FIDUCIAL_IDS[0], FIDUCIAL_IDS[1]

    span_px = float(
        np.linalg.norm(corners[top_right].mean(axis=0) - corners[top_left].mean(axis=0))
    )
    span_mm = float(
        np.linalg.norm(np.array(centres_mm[top_right]) - np.array(centres_mm[top_left]))
    )
    return span_px / (span_mm / 25.4)


def rectify(
    image: ImageArray, corners: dict[int, ImageArray], *, dpi: float = OUTPUT_DPI
) -> WarpResult:
    """Flatten a photographed page onto the known page rectangle.

    Requires all four markers. Three would define an affine transform, which
    cannot represent perspective — the result would look plausible and be
    wrong, so the missing marker is an error rather than something to work
    around.
    """
    missing = [i for i in FIDUCIAL_IDS if i not in corners]
    if missing:
        raise WarpError(
            f"need all four corner markers, missing {missing}. "
            f"A three-point transform cannot represent perspective."
        )

    source_dpi = measure_source_dpi(corners)
    skew = measure_skew(corners)
    keystone = measure_keystone(corners)

    centres_mm = fiducial_centres_mm()
    px_per_mm = dpi / 25.4

    source = np.array([corners[i].mean(axis=0) for i in FIDUCIAL_IDS], dtype=np.float32)
    # Millimetres to output pixels. The y axis flips: the layout measures from
    # the page's bottom-left, images from the top-left.
    target = np.array(
        [
            [
                centres_mm[i][0] * px_per_mm,
                (PAGE_HEIGHT_MM - centres_mm[i][1]) * px_per_mm,
            ]
            for i in FIDUCIAL_IDS
        ],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(source, target)
    width, height = _page_size_px(dpi)

    warped = cv2.warpPerspective(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255.0, 255.0, 255.0, 255.0),
    )

    return WarpResult(
        image=warped,
        dpi=dpi,
        source_dpi=source_dpi,
        skew_degrees=skew,
        keystone=keystone,
    )


def region_px(
    x_mm: float, y_mm: float, width_mm: float, height_mm: float, *, dpi: float = OUTPUT_DPI
) -> tuple[int, int, int, int]:
    """A layout rectangle as pixels in a rectified page, top-left origin.

    Valid only against the output of `rectify`, which is why both live here.
    """
    px_per_mm = dpi / 25.4
    return (
        int(round(x_mm * px_per_mm)),
        int(round((PAGE_HEIGHT_MM - y_mm - height_mm) * px_per_mm)),
        int(round(width_mm * px_per_mm)),
        int(round(height_mm * px_per_mm)),
    )


def crop(image: ImageArray, rect: tuple[int, int, int, int]) -> ImageArray:
    """Extract a rectangle, clamped to the image bounds."""
    x, y, w, h = rect
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(image.shape[1], x + w), min(image.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        raise WarpError(f"region {rect} lies outside the page")
    return image[y0:y1, x0:x1]


def redact(image: ImageArray, rect: tuple[int, int, int, int]) -> ImageArray:
    """Return a copy with a rectangle painted out.

    Used to remove the identity region before a page reaches a marker. Returns
    a copy rather than mutating, so the caller cannot accidentally hand on the
    original — the one mistake here would defeat anonymous marking entirely.
    """
    x, y, w, h = rect
    out = image.copy()
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(out.shape[1], x + w), min(out.shape[0], y + h)
    out[y0:y1, x0:x1] = 255
    return out
