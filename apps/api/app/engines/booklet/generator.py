"""Booklet PDF generation.

Produces the structured answer booklet described in spec.md §1.1: four ArUco
fiducials, a QR carrying the page's identity, and printed question boxes with
declared maximum marks.

Output is deterministic. The same specification always produces byte-identical
bytes, so a booklet can be regenerated and compared, and a reprint is provably
the same page rather than merely a similar one (I5).
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

import qrcode
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.engines.booklet.layout import (
    CONTENT_MARGIN_MM,
    CONTENT_WIDTH_MM,
    FIDUCIAL_SIZE_MM,
    IDENTITY_BOX_HEIGHT_MM,
    IDENTITY_BOX_WIDTH_MM,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    QR_SIZE_MM,
    QUESTION_BOX_MAX_HEIGHT_MM,
    QUESTION_BOX_MIN_HEIGHT_MM,
    QUESTION_BOX_PADDING_MM,
    QUESTION_BOX_TITLE_HEIGHT_MM,
    RULE_SPACING_MM,
    fiducial_origins_mm,
    mm,
)
from app.engines.booklet.markers import marker_bitmap
from app.engines.booklet.payload import BookletPayload

_RULE_GREY = HexColor("#C8CDD6")


def format_marks(value: Decimal) -> str:
    """Render a mark total for printing.

    `Decimal.normalize()` alone is wrong here: it renders 10 as `1E+1`, so the
    booklet would have gone to the printer reading "[1E+1 marks]". The `f`
    presentation type forces fixed-point, while normalise still strips the
    trailing zero from values like 5.0.
    """
    return format(value.normalize(), "f")


@dataclass(frozen=True, slots=True)
class QuestionSlot:
    """One printed answer region with its declared maximum."""

    number: str  # "3(a)"
    max_marks: Decimal
    height_mm: float = QUESTION_BOX_MIN_HEIGHT_MM

    def __post_init__(self) -> None:
        if not self.number.strip():
            raise ValueError("question number cannot be blank")
        if self.max_marks <= 0:
            raise ValueError(f"max_marks must be positive, got {self.max_marks}")
        if self.height_mm < QUESTION_BOX_MIN_HEIGHT_MM:
            raise ValueError(
                f"height {self.height_mm}mm is below the {QUESTION_BOX_MIN_HEIGHT_MM}mm minimum"
            )
        if self.height_mm > QUESTION_BOX_MAX_HEIGHT_MM:
            raise ValueError(
                f"height {self.height_mm}mm exceeds the {QUESTION_BOX_MAX_HEIGHT_MM}mm maximum "
                f"that fits on a page. Split this into two questions rather than "
                f"printing a box that runs off the paper."
            )


@dataclass(frozen=True, slots=True)
class BookletSpec:
    """Everything needed to print one booklet.

    Carries no student name or index number. Booklets are anonymous by design
    so marking is anonymous by default; identity is joined only at export, via
    a separate restricted table (spec.md §1.1, §3).
    """

    booklet_id: uuid.UUID
    exam_id: uuid.UUID
    exam_code: str
    exam_title: str
    questions: list[QuestionSlot] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.questions:
            raise ValueError("a booklet needs at least one question slot")
        seen = [q.number for q in self.questions]
        if len(seen) != len(set(seen)):
            raise ValueError(f"duplicate question numbers: {seen}")


def _qr_image(payload: BookletPayload) -> ImageReader:
    """Render the payload as a QR image.

    Error correction M (~15%). Q or H would survive more damage but push the
    version higher, shrinking each module at a fixed 26 mm. A booklet is
    photographed once, flat, minutes after being written on — module size
    matters more here than resistance to physical damage.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload.encode())
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def _draw_fiducials(pdf: canvas.Canvas) -> None:
    """Four corner markers, each on a white patch.

    The patch matters: ArUco needs a quiet zone, and a marker printed directly
    onto a tinted or textured background loses the contrast its edge detection
    depends on.
    """
    size = mm(FIDUCIAL_SIZE_MM)
    quiet = mm(2.0)

    for marker_id, (x_mm, y_mm) in fiducial_origins_mm().items():
        x, y = mm(x_mm), mm(y_mm)

        pdf.setFillColor(white)
        pdf.rect(x - quiet, y - quiet, size + 2 * quiet, size + 2 * quiet, stroke=0, fill=1)

        pdf.drawImage(
            ImageReader(io.BytesIO(marker_bitmap(marker_id))),
            x,
            y,
            width=size,
            height=size,
            preserveAspectRatio=True,
            # No interpolation: smoothing rounds the hard cell edges the
            # detector keys on, and a blurred marker is an unreadable one.
            anchor="sw",
        )


def _draw_header(pdf: canvas.Canvas, spec: BookletSpec, payload: BookletPayload) -> float:
    """Draw the QR and page identification. Returns the y of the content top."""
    top = mm(PAGE_HEIGHT_MM - CONTENT_MARGIN_MM)
    qr_side = mm(QR_SIZE_MM)
    left = mm(CONTENT_MARGIN_MM)

    pdf.drawImage(_qr_image(payload), left, top - qr_side, width=qr_side, height=qr_side)

    text_x = left + qr_side + mm(6)
    pdf.setFillColor(black)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(text_x, top - mm(6), f"{spec.exam_code} — {spec.exam_title}")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(text_x, top - mm(12), f"Page {payload.page_no} of {payload.page_total}")

    # A seat number is written by the invigilator and is *not* the student's
    # identity. It exists so a physical booklet can be traced back if the
    # anonymity mapping ever has to be audited.
    pdf.drawString(text_x, top - mm(18), "Seat: ______________")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(HexColor("#5A6472"))
    pdf.drawString(
        text_x,
        top - mm(24),
        "Do not write your name. Write your index number in the box below.",
    )

    return top - qr_side - mm(8)


def _draw_identity_box(pdf: canvas.Canvas, bottom_of_header: float) -> float:
    """The index-number box. Page 1 only.

    Everything inside this rectangle is cropped away by Engine 1 before a
    marker sees the page, so the marker cannot know whose script they are
    marking even though the student wrote it plainly. Anonymity is enforced by
    geometry, not by anyone remembering to look away.

    The box is drawn from `layout` constants for the same reason the crop reads
    them: if drawing and cropping ever disagreed, either identity would leak to
    the marker or handwriting would be silently discarded.
    """
    left = mm(CONTENT_MARGIN_MM)
    width = mm(IDENTITY_BOX_WIDTH_MM)
    height = mm(IDENTITY_BOX_HEIGHT_MM)
    bottom = bottom_of_header - height

    pdf.setStrokeColor(black)
    pdf.setLineWidth(1.0)
    pdf.rect(left, bottom, width, height, stroke=1, fill=0)

    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(left + mm(3), bottom + height - mm(5.5), "INDEX NUMBER")

    pdf.setFont("Helvetica", 6.5)
    pdf.setFillColor(HexColor("#5A6472"))
    pdf.drawString(
        left + mm(3),
        bottom + mm(3),
        "Write clearly. This box is removed before marking.",
    )

    # A baseline to write on, so digits land in a predictable band.
    pdf.setStrokeColor(_RULE_GREY)
    pdf.setLineWidth(0.5)
    pdf.line(left + mm(3), bottom + mm(7), left + width - mm(3), bottom + mm(7))

    return bottom - mm(6)


def _draw_question_box(pdf: canvas.Canvas, slot: QuestionSlot, top_y: float) -> float:
    """Draw one question region. Returns the y below it."""
    height = mm(slot.height_mm)
    left = mm(CONTENT_MARGIN_MM)
    width = mm(CONTENT_WIDTH_MM)
    bottom = top_y - height

    pdf.setStrokeColor(black)
    pdf.setLineWidth(0.8)
    pdf.rect(left, bottom, width, height, stroke=1, fill=0)

    title_h = mm(QUESTION_BOX_TITLE_HEIGHT_MM)
    pdf.setLineWidth(0.5)
    pdf.line(left, top_y - title_h, left + width, top_y - title_h)

    pad = mm(QUESTION_BOX_PADDING_MM)
    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(left + pad, top_y - title_h + mm(2.5), f"QUESTION {slot.number}")

    # The declared maximum is printed on the page, which is what turns
    # segmentation into a lookup instead of an inference (spec.md §1.1).
    label = f"[{format_marks(slot.max_marks)} mark{'' if slot.max_marks == 1 else 's'}]"
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(left + width - pad, top_y - title_h + mm(2.5), label)

    # Ruled lines give OCR a predictable baseline pitch.
    pdf.setStrokeColor(_RULE_GREY)
    pdf.setLineWidth(0.4)
    rule_y = top_y - title_h - mm(RULE_SPACING_MM)
    while rule_y > bottom + mm(3):
        pdf.line(left + pad, rule_y, left + width - pad, rule_y)
        rule_y -= mm(RULE_SPACING_MM)

    return bottom - mm(6)


#: Vertical gap below each question box.
_SLOT_GAP_MM = 6.0


def _usable_height_mm(page_no: int) -> float:
    """Space available for question boxes on a given page.

    Page 1 is shorter than the rest: the identity box takes 20 mm plus its
    gap. Assuming a uniform height here silently overflows the last box on
    page 1 off the bottom of the paper — which is invisible in the page count
    and only discovered when a student meets a truncated answer box.
    """
    usable = PAGE_HEIGHT_MM - 2 * CONTENT_MARGIN_MM - QR_SIZE_MM - 8
    if page_no == 1:
        usable -= IDENTITY_BOX_HEIGHT_MM + _SLOT_GAP_MM
    return usable


def _paginate(spec: BookletSpec) -> list[list[QuestionSlot]]:
    """Split questions into pages by available height.

    Done before any drawing so `page_total` is known when the first QR is
    encoded — a QR claiming "page 1 of 3" on a booklet that turns out to be
    four pages long would make missing-page detection actively wrong.
    """
    pages: list[list[QuestionSlot]] = []
    current: list[QuestionSlot] = []
    remaining = _usable_height_mm(1)

    for slot in spec.questions:
        needed = slot.height_mm + _SLOT_GAP_MM
        if current and needed > remaining:
            pages.append(current)
            current = []
            remaining = _usable_height_mm(len(pages) + 1)
        current.append(slot)
        remaining -= needed

    if current:
        pages.append(current)
    return pages


def generate(spec: BookletSpec) -> bytes:
    """Render a complete booklet as PDF bytes.

    Deterministic: identical input produces identical output.
    """
    pages = _paginate(spec)
    buffer = io.BytesIO()

    # `invariant=1` is ReportLab's supported switch for reproducible output: it
    # fixes the document timestamp and id, which otherwise make two identical
    # booklets differ byte for byte.
    pdf = canvas.Canvas(
        buffer,
        pagesize=(mm(PAGE_WIDTH_MM), mm(PAGE_HEIGHT_MM)),
        invariant=1,
    )
    pdf.setTitle(f"{spec.exam_code} answer booklet")
    pdf.setAuthor("Marking Assistant")
    # Neither the booklet id nor anything student-identifying goes in the
    # metadata: PDF metadata survives printing to a file and is trivially read.
    pdf.setSubject(spec.exam_title)

    for index, slots in enumerate(pages, start=1):
        payload = BookletPayload(
            booklet_id=spec.booklet_id,
            exam_id=spec.exam_id,
            page_no=index,
            page_total=len(pages),
        )

        _draw_fiducials(pdf)
        y = _draw_header(pdf, spec, payload)

        # Page 1 only. Repeating it would give a marker several chances to see
        # an identity that was meant to be cropped exactly once.
        if index == 1:
            y = _draw_identity_box(pdf, y)

        for slot in slots:
            y = _draw_question_box(pdf, slot, y)

        pdf.showPage()

    pdf.setProducer("Marking Assistant")
    pdf.save()

    return buffer.getvalue()
