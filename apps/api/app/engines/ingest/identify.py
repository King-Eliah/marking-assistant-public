"""Reading a page's identity from its QR — Engine 1, spec.md §1.3.

Runs on the *rectified* page, never the raw photograph. That ordering was
established from real photographs: a page at 79 DPI failed to decode raw and
succeeded once flattened. Perspective correction is worth real resolution to
the decoder, and it is free here because the page has to be rectified anyway.

A page whose QR cannot be read is not identifiable, and an unidentifiable page
cannot be assembled into a script. It is refused rather than guessed at — a
page filed under the wrong booklet is a mark awarded to the wrong student.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from app.engines.booklet.payload import BookletPayload, InvalidPayloadError, decode

ImageArray = np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]]


class UnidentifiablePageError(Exception):
    """No usable booklet payload on this page.

    Deliberately fatal for the page. There is no safe fallback: assigning it to
    a neighbouring booklet, or to whichever script was last uploaded, produces
    a plausible-looking script containing another student's answers.
    """


@dataclass(frozen=True, slots=True)
class PageIdentity:
    """Which booklet and page this image is, and how it was read."""

    payload: BookletPayload
    #: True when the raw photograph decoded without rectification. Worth
    #: recording: a fleet where this is usually false is a fleet capturing at
    #: marginal resolution, which is a warning long before pages start failing.
    decoded_before_rectifying: bool


def _try_decode(detector: cv2.QRCodeDetector, image: ImageArray) -> BookletPayload | None:
    text, _, _ = detector.detectAndDecode(image)
    if not text:
        return None
    try:
        return decode(text)
    except InvalidPayloadError:
        # A QR that reads but is not ours — a sticker, a form, another system's
        # label. Not our page, and not something to interpret generously.
        return None


def identify(raw: ImageArray, rectified: ImageArray) -> PageIdentity:
    """Read the booklet payload, preferring the rectified page.

    Both are tried so the result can record which worked, which is a cheap
    early-warning signal about capture quality across a whole exam.
    """
    detector = cv2.QRCodeDetector()

    from_raw = _try_decode(detector, raw)
    from_rectified = _try_decode(detector, rectified)

    payload = from_rectified or from_raw
    if payload is None:
        raise UnidentifiablePageError(
            "No booklet QR could be read from this page, before or after "
            "rectification. The page cannot be assigned to a script."
        )

    if from_raw is not None and from_rectified is not None and from_raw != from_rectified:
        # Two different readings of the same sheet. One of them is wrong and
        # there is no way to tell which, so neither is used.
        raise UnidentifiablePageError(
            f"The QR read as {from_raw.encode()} before rectification and "
            f"{from_rectified.encode()} after. Refusing to choose between them."
        )

    return PageIdentity(payload=payload, decoded_before_rectifying=from_raw is not None)
