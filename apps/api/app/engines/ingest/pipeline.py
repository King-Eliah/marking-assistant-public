"""Engine 1 end to end — spec.md ENGINE 1.

One photograph in, one rectified and anonymised page out, or an explicit
refusal. The ordering is not arbitrary; each step exists because the next one
depends on it:

    detect fiducials -> rectify -> identify -> assess -> redact identity

Detection comes first because the homography needs the four markers.
Rectification comes before identification because a page at 79 DPI failed to
decode raw and succeeded once flattened — perspective correction is worth real
resolution to the QR decoder. Assessment comes after rectification because the
measurements it judges (DPI, skew, keystone) are computed while rectifying.
Redaction comes last because it needs the rectified page to crop by coordinate.

Every failure is explicit. Engine 1 never emits a page it is unsure about: a
page warped from three markers, or filed under a guessed booklet, looks
entirely correct and is wrong in a way nobody downstream can detect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.states import State
from app.engines.booklet.layout import HEADER_BOTTOM_MM, identity_region_mm
from app.engines.booklet.markers import detect
from app.engines.booklet.payload import BookletPayload
from app.engines.ingest.identify import UnidentifiablePageError, identify
from app.engines.ingest.quality import QualityReport, Verdict, assess
from app.engines.ingest.warp import WarpError, rectify, redact, region_px

ImageArray = np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]]


@dataclass(frozen=True, slots=True)
class IngestedPage:
    """A page that made it through Engine 1.

    `image` is the anonymised page — the identity region is already removed, so
    this is the artefact safe to hand to a marker. The original photograph is
    kept elsewhere for the appeal bundle; it is deliberately not carried here,
    because an object holding both would make it easy to send the wrong one.
    """

    payload: BookletPayload
    image: ImageArray
    quality: QualityReport
    #: True when the page carried an identity region that was removed. Only
    #: page 1 does, so a False here on page 1 means the crop did not happen.
    identity_removed: bool

    @property
    def next_state(self) -> State:
        return State.OCR_RUNNING


@dataclass(frozen=True, slots=True)
class RejectedPage:
    """A page Engine 1 refused, and why.

    `reasons` is written for the person holding the phone, not for a log.
    """

    reasons: tuple[str, ...]
    quality: QualityReport | None

    @property
    def next_state(self) -> State:
        return State.QUALITY_REJECTED


def ingest(photograph: ImageArray) -> IngestedPage | RejectedPage:
    """Run one captured page through Engine 1.

    Returns a rejection rather than raising for the ordinary failures — a
    blurred or badly framed photograph is an expected outcome of asking a human
    to photograph three hundred scripts, not an exceptional one.
    """
    corners = detect(photograph)
    if len(corners) < 4:
        return RejectedPage(
            reasons=(
                f"Only {len(corners)} of the 4 corner markers are visible. "
                f"Make sure all four corners of the page are in frame.",
            ),
            quality=None,
        )

    try:
        warped = rectify(photograph, corners)
    except WarpError as exc:
        return RejectedPage(reasons=(str(exc),), quality=None)

    report = assess(
        image=photograph,
        dpi=warped.source_dpi,
        skew_degrees=warped.skew_degrees,
        keystone=warped.keystone,
        fiducials_found=len(corners),
    )

    # Identify before judging quality, so a rejection can still say which page
    # failed. "Page 2 of Booklet a3f2 was too blurred" is actionable; "a page
    # was too blurred" sends someone back through three hundred scripts.
    try:
        identity = identify(photograph, warped.image)
    except UnidentifiablePageError as exc:
        return RejectedPage(reasons=(str(exc), *report.reasons), quality=report)

    if report.verdict is Verdict.REJECT:
        return RejectedPage(reasons=report.reasons, quality=report)

    image = warped.image
    identity_removed = False
    if identity.payload.page_no == 1:
        image = redact(image, region_px(*identity_region_mm(HEADER_BOTTOM_MM)))
        identity_removed = True

    return IngestedPage(
        payload=identity.payload,
        image=image,
        quality=report,
        identity_removed=identity_removed,
    )
