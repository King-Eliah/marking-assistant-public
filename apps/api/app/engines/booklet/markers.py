"""ArUco fiducial rendering.

The generator and Engine 1's detector must agree exactly on the dictionary and
the id-to-corner assignment. Both import from `layout`, so there is one place
for that agreement to live and no way for the two sides to drift apart.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import cv2
import numpy as np

from app.engines.booklet.layout import ARUCO_DICTIONARY, FIDUCIAL_IDS

#: Any 2-D image array. Kept loose deliberately — callers pass grayscale from
#: `imdecode`, colour from a camera, and warped output from `warpPerspective`.
ImageArray = np.ndarray[Any, np.dtype[Any]]


@lru_cache
def get_dictionary() -> cv2.aruco.Dictionary:
    """The shared ArUco dictionary. Detection must use this same object."""
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICTIONARY))


@lru_cache
def marker_bitmap(marker_id: int, side_px: int = 240) -> bytes:
    """Render one marker as a PNG.

    Rendered at high resolution and scaled down by the PDF rather than drawn at
    final size, so cell edges land on exact pixel boundaries. A marker whose
    cells are resampled with interpolation develops grey edges, and grey edges
    are what makes an otherwise sharp photograph fail to decode.
    """
    if marker_id not in FIDUCIAL_IDS:
        raise ValueError(f"{marker_id} is not one of the four corner ids {FIDUCIAL_IDS}")

    image = cv2.aruco.generateImageMarker(get_dictionary(), marker_id, side_px)
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(f"could not encode marker {marker_id}")
    return bytes(buffer)


def detect(image: ImageArray) -> dict[int, ImageArray]:
    """Find corner markers in an image.

    Returns `{marker_id: corners}` for the four corner ids only. Anything else
    in the dictionary is ignored rather than treated as a page corner.

    Lives here rather than in Engine 1 so that detection and generation are
    tested against each other in one place — a generator that emits markers its
    own detector cannot read is the failure this arrangement rules out.
    """
    detector = cv2.aruco.ArucoDetector(get_dictionary(), cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(image)

    # OpenCV's stubs declare `ids` non-optional, but detectMarkers genuinely
    # returns None when nothing is found — `test_a_blank_page_yields_no_markers`
    # relies on it. Removing this check to satisfy the type checker would crash
    # on every blank or over-exposed page.
    if ids is None:
        return {}  # type: ignore[unreachable]

    found: dict[int, ImageArray] = {}
    for corner, marker_id in zip(corners, ids.flatten(), strict=True):
        if int(marker_id) in FIDUCIAL_IDS:
            found[int(marker_id)] = corner.reshape(4, 2)
    return found
