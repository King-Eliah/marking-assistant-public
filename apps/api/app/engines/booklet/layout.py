"""Physical geometry of the answer booklet.

spec.md §1.1 calls the structured booklet the highest-leverage decision in the
project, and this module is why. Because every dimension here is fixed and
known in millimetres, downstream code can compute real values instead of
guessing:

- four fiducials at known positions make perspective correction an exact
  homography from four point correspondences, not a guessed contour
- a known physical page size means the effective DPI of a photograph is
  measurable, so blur and skew thresholds become real numbers rather than
  magic constants
- printed question boxes turn segmentation into a lookup, removing an entire
  class of catastrophic error where text is scored against the wrong rubric

Nothing in this file may drift without a `PIPELINE_VERSION` bump: a booklet
printed under one geometry and detected under another produces a valid-looking
warp onto the wrong coordinates.
"""

from __future__ import annotations

from typing import Final

#: Bump on any change to a dimension in this file.
#:
#: Recorded against every issued booklet. A booklet printed under one geometry
#: and detected under another produces a warp that looks entirely valid and
#: maps onto the wrong coordinates — a silent failure that would attribute
#: handwriting to the wrong question. A recorded version makes it loud instead.
LAYOUT_VERSION: Final[str] = "1.0"

#: ReportLab works in points. 72 pt = 1 inch = 25.4 mm.
MM_TO_PT: Final[float] = 72.0 / 25.4


def mm(value: float) -> float:
    """Millimetres to points."""
    return value * MM_TO_PT


# --- page ------------------------------------------------------------------

PAGE_WIDTH_MM: Final[float] = 210.0  # A4
PAGE_HEIGHT_MM: Final[float] = 297.0

# --- fiducials -------------------------------------------------------------

#: 12 mm per spec.md §1.1. At 150 DPI that is ~71 px across a 6x6 ArUco grid
#: including its quiet border, so roughly 12 px per cell — comfortably above
#: the ~4 px per cell where detection starts to fail on phone photographs.
FIDUCIAL_SIZE_MM: Final[float] = 12.0

#: Distance from page edge to the outer edge of each marker. Kept at 8 mm
#: because consumer printers routinely cannot print within ~5 mm of the edge,
#: and a clipped fiducial is an undetectable fiducial.
FIDUCIAL_MARGIN_MM: Final[float] = 8.0

#: ArUco IDs are assigned per corner and never reused. Detection returns ids
#: alongside corners, so orientation is read directly from *which* markers were
#: found — a page photographed upside down still resolves correctly, with no
#: guessing from geometry.
FIDUCIAL_ID_TOP_LEFT: Final[int] = 0
FIDUCIAL_ID_TOP_RIGHT: Final[int] = 1
FIDUCIAL_ID_BOTTOM_RIGHT: Final[int] = 2
FIDUCIAL_ID_BOTTOM_LEFT: Final[int] = 3

#: Clockwise from top-left. Homography needs a stable correspondence order.
FIDUCIAL_IDS: Final[tuple[int, int, int, int]] = (
    FIDUCIAL_ID_TOP_LEFT,
    FIDUCIAL_ID_TOP_RIGHT,
    FIDUCIAL_ID_BOTTOM_RIGHT,
    FIDUCIAL_ID_BOTTOM_LEFT,
)

#: DICT_4X4_50 — 4x4 bits, 50 markers. Chosen deliberately over denser
#: dictionaries: fewer bits means larger cells at a fixed 12 mm, and only four
#: distinct markers are ever needed. Detection robustness on a phone camera in
#: poor exam-hall light matters far more than dictionary capacity here.
ARUCO_DICTIONARY: Final[str] = "DICT_4X4_50"


def fiducial_origins_mm() -> dict[int, tuple[float, float]]:
    """Bottom-left corner of each fiducial, in millimetres from the page's
    bottom-left origin (ReportLab's coordinate system).

    Returned per id rather than as a list so a caller cannot silently rely on
    ordering.
    """
    near = FIDUCIAL_MARGIN_MM
    far_x = PAGE_WIDTH_MM - FIDUCIAL_MARGIN_MM - FIDUCIAL_SIZE_MM
    far_y = PAGE_HEIGHT_MM - FIDUCIAL_MARGIN_MM - FIDUCIAL_SIZE_MM

    return {
        FIDUCIAL_ID_TOP_LEFT: (near, far_y),
        FIDUCIAL_ID_TOP_RIGHT: (far_x, far_y),
        FIDUCIAL_ID_BOTTOM_RIGHT: (far_x, near),
        FIDUCIAL_ID_BOTTOM_LEFT: (near, near),
    }


def fiducial_centres_mm() -> dict[int, tuple[float, float]]:
    """Centre of each fiducial. These are the four points Engine 1 matches
    against detected marker centres to build the homography."""
    half = FIDUCIAL_SIZE_MM / 2
    return {mid: (x + half, y + half) for mid, (x, y) in fiducial_origins_mm().items()}


# --- content area ----------------------------------------------------------

#: Content is inset clear of the fiducials so nothing overlaps a marker's quiet
#: zone. An overlapping glyph is the most common cause of a marker that images
#: perfectly and still fails to decode.
CONTENT_MARGIN_MM: Final[float] = FIDUCIAL_MARGIN_MM + FIDUCIAL_SIZE_MM + 5.0

CONTENT_WIDTH_MM: Final[float] = PAGE_WIDTH_MM - 2 * CONTENT_MARGIN_MM

# --- header ----------------------------------------------------------------

QR_SIZE_MM: Final[float] = 26.0
HEADER_HEIGHT_MM: Final[float] = 30.0

# --- question boxes --------------------------------------------------------

QUESTION_BOX_PADDING_MM: Final[float] = 4.0
QUESTION_BOX_TITLE_HEIGHT_MM: Final[float] = 8.0
QUESTION_BOX_MIN_HEIGHT_MM: Final[float] = 25.0

#: Ruled writing lines inside each answer region. 8 mm suits adult handwriting
#: and gives OCR a predictable baseline pitch, which materially helps line
#: segmentation on unlined prose.
RULE_SPACING_MM: Final[float] = 8.0


def expected_dpi(pixel_width: int) -> float:
    """Effective DPI of a photograph, given its width in pixels.

    Possible only because the page width is a known constant. This is what lets
    the quality gate express thresholds in real units — "blur radius exceeds
    0.2 mm" rather than an unexplained pixel count that silently means
    something different on every camera.
    """
    return pixel_width / (PAGE_WIDTH_MM / 25.4)
