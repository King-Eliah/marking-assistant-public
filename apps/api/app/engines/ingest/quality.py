"""The capture quality gate — Engine 1, spec.md §1.4.

Every threshold here is derived from a measurement, not chosen. That is the
whole point of the structured booklet: because the page is a known 210mm wide,
a photograph's effective DPI is computable, and "is this sharp enough" becomes
a real question with a real answer instead of a magic pixel count that means
something different on every camera.

The resolution floor came from a real failure. Three photographs of a printed
booklet arrived at 720x1280 after a messaging app recompressed them — about
50 DPI across the page. All four fiducials still detected, because they are
12mm and only 4x4 bits. The QR did not decode at all: 41 modules across 26mm
left roughly 1.2 pixels per module.

Two things were then learned from real photographs, both of which shaped the
numbers below.

**Rectify before decoding.** A page at 79 DPI failed to decode raw and
succeeded once rectified. Removing the perspective distortion is worth real
resolution to the decoder, so the pipeline runs `rectify` first and reads the
QR from the flattened page.

**The margin is not decoration.** Sweeping one real photograph down through
scale decoded at 79, 63 and 48 DPI but failed at 71, 56 and 40 — non-monotonic,
because at some scales the QR's module grid happens to align with the pixel
grid and at others it does not. Below roughly 100 DPI, success is alignment
luck rather than capability. The gate therefore sits at 120: the point where
decoding is reliable, not the lowest point where it has ever been observed to
work.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

import cv2
import numpy as np

from app.engines.booklet.layout import PAGE_WIDTH_MM

ImageArray = np.ndarray[Any, np.dtype[Any]]

#: The lowest resolution at which a QR has ever been observed to decode here,
#: on a rectified page. Not a threshold — a floor below which it is hopeless.
#: Between this and MIN_DPI_REJECT, decoding happens or does not depending on
#: how the module grid falls against the pixel grid.
MIN_DPI_HARD: Final[float] = 90.0

#: The gate's actual floor. 120 DPI is 3 pixels per QR module: enough that
#: decoding does not depend on lucky alignment, with room for the blur and
#: noise a real photograph carries.
MIN_DPI_REJECT: Final[float] = 120.0

#: Below this it will probably work but is worth warning about.
MIN_DPI_WARN: Final[float] = 150.0

#: Variance of Laplacian, the standard sharpness proxy. Scale-dependent, so it
#: is only meaningful alongside a known DPI — which is exactly what the booklet
#: geometry provides.
MIN_SHARPNESS_REJECT: Final[float] = 80.0
MIN_SHARPNESS_WARN: Final[float] = 150.0

#: Page tilt in the image plane. Beyond this the warp still works but the
#: photograph is awkward enough that a retake is quicker than the correction.
MAX_SKEW_DEGREES: Final[float] = 12.0

#: Perspective, as the ratio of the top edge to the bottom edge between
#: fiducial centres. 1.0 is flat-on. Their test photographs measured 0.85-0.87,
#: which is a normal hand-held angle and comfortably inside this.
MAX_KEYSTONE: Final[float] = 0.70

#: Mean luminance, for the too-dark case only. Underexposure genuinely loses
#: pencil strokes while leaving the high-contrast fiducials readable, so this
#: catches something detection does not.
MIN_BRIGHTNESS: Final[float] = 40.0

#: Overexposure is measured as clipping, not as a high mean.
#:
#: A booklet page is mostly white paper, so mean luminance cannot separate a
#: lightly-written page from a blown-out one — measured at 250 and 252
#: respectively, both of which a mean-based threshold would reject. Since short
#: answers are common, that would refuse exactly the pages most likely to be
#: correct.
#:
#: Clipped pixels are the honest signal: paper photographs around 230-250 and
#: only reaches 255 when detail has actually been lost. The reference
#: photographs clip 0.0% of their pixels.
MAX_CLIPPED_FRACTION: Final[float] = 0.25


class Verdict(StrEnum):
    ACCEPT = "ACCEPT"
    WARN = "WARN"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class QualityReport:
    """What the gate measured, and what it decided.

    Every rejection carries a message written for the person holding the
    phone. "Quality check failed" tells them nothing they can act on; "move
    closer, the page needs to fill more of the frame" gets a usable photograph
    on the second attempt.
    """

    verdict: Verdict
    dpi: float
    sharpness: float
    skew_degrees: float
    keystone: float
    brightness: float
    clipped_fraction: float
    fiducials_found: int
    reasons: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.verdict is not Verdict.REJECT


def measure_dpi(fiducial_span_px: float, fiducial_span_mm: float) -> float:
    """Effective DPI from a known physical distance.

    Measured between fiducial centres rather than from the image width,
    because the page rarely fills the frame — using the frame would report the
    camera's resolution instead of the page's.
    """
    if fiducial_span_mm <= 0:
        raise ValueError("fiducial span must be positive")
    return fiducial_span_px / (fiducial_span_mm / 25.4)


def measure_sharpness(image: ImageArray) -> float:
    """Variance of the Laplacian. Higher is sharper."""
    return float(cv2.Laplacian(image, cv2.CV_64F).var())


def measure_brightness(image: ImageArray) -> float:
    return float(np.mean(image))


def measure_clipping(image: ImageArray) -> float:
    """Fraction of pixels at pure white.

    The overexposure signal. Unlike mean luminance this does not penalise a
    page for being mostly paper, which every booklet page is.
    """
    return float(np.count_nonzero(image >= 255) / image.size)


def assess(
    *,
    image: ImageArray,
    dpi: float,
    skew_degrees: float,
    keystone: float,
    fiducials_found: int,
) -> QualityReport:
    """Judge one captured page.

    Fails closed: anything not measurable is a rejection, never an assumption
    that it was probably fine.
    """
    sharpness = measure_sharpness(image)
    brightness = measure_brightness(image)
    clipping = measure_clipping(image)

    reasons: list[str] = []
    verdict = Verdict.ACCEPT

    def reject(message: str) -> None:
        nonlocal verdict
        verdict = Verdict.REJECT
        reasons.append(message)

    def warn(message: str) -> None:
        nonlocal verdict
        if verdict is Verdict.ACCEPT:
            verdict = Verdict.WARN
        reasons.append(message)

    if fiducials_found < 4:
        reject(
            f"Only {fiducials_found} of the 4 corner markers are visible. "
            f"Make sure all four corners of the page are in frame and not covered."
        )

    if dpi < MIN_DPI_REJECT:
        reject(
            f"The photo is too low-resolution ({dpi:.0f} DPI). Move closer so the "
            f"page fills the frame, and check your app is not shrinking photos "
            f"before upload."
        )
    elif dpi < MIN_DPI_WARN:
        warn(f"Resolution is low ({dpi:.0f} DPI). Moving closer would be safer.")

    if sharpness < MIN_SHARPNESS_REJECT:
        reject("The photo is blurred. Hold still, tap to focus, and take it again.")
    elif sharpness < MIN_SHARPNESS_WARN:
        warn("The photo is slightly soft. It should still read.")

    if abs(skew_degrees) > MAX_SKEW_DEGREES:
        warn(f"The page is rotated about {abs(skew_degrees):.0f} degrees. Straighten it.")

    if keystone < MAX_KEYSTONE:
        warn("You are photographing at a steep angle. Hold the phone flatter over the page.")

    if brightness < MIN_BRIGHTNESS:
        reject("The photo is too dark. Find better light — avoid your own shadow.")

    if clipping > MAX_CLIPPED_FRACTION:
        reject(
            f"{clipping:.0%} of the photo is pure white, so writing has been lost to "
            f"glare. Move away from the light source and turn the flash off."
        )

    return QualityReport(
        verdict=verdict,
        dpi=dpi,
        sharpness=sharpness,
        skew_degrees=skew_degrees,
        keystone=keystone,
        brightness=brightness,
        clipped_fraction=clipping,
        fiducials_found=fiducials_found,
        reasons=tuple(reasons),
    )


def recommended_capture_pixels() -> int:
    """Shortest image edge that reliably clears the gate.

    Useful for the capture app, which should refuse to downscale below this
    before upload — the failure that produced these thresholds in the first
    place.

    Rounded up, never to nearest: rounding down by a single pixel produces a
    recommendation that does not itself clear the threshold it is recommending.
    """
    return math.ceil(MIN_DPI_WARN * PAGE_WIDTH_MM / 25.4)
