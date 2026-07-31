"""Booklet PDF generation.

Two properties carry most of the weight here: the output is deterministic
(I5), and nothing identifying a student can reach the page. Anonymous marking
is a stated selling point of the system, and it is only true if it is true of
the artefact the student actually writes on.
"""

from __future__ import annotations

import io
import uuid
from decimal import Decimal

import cv2
import numpy as np
import pytest
import qrcode
from pypdf import PdfReader

from app.engines.booklet.generator import (
    BookletSpec,
    QuestionSlot,
    format_marks,
    generate,
)
from app.engines.booklet.payload import BookletPayload, decode

BOOKLET = uuid.UUID("11111111-2222-3333-4444-555555555555")
EXAM = uuid.UUID("66666666-7777-8888-9999-aaaaaaaaaaaa")


def spec(**overrides: object) -> BookletSpec:
    defaults: dict[str, object] = {
        "booklet_id": BOOKLET,
        "exam_id": EXAM,
        "exam_code": "CSM 355",
        "exam_title": "Operating Systems",
        "questions": [
            QuestionSlot("1(a)", Decimal("6")),
            QuestionSlot("1(b)", Decimal("4")),
            QuestionSlot("2", Decimal("10"), height_mm=60),
        ],
    }
    defaults.update(overrides)
    return BookletSpec(**defaults)  # type: ignore[arg-type]


def read(pdf: bytes) -> PdfReader:
    return PdfReader(io.BytesIO(pdf))


def page_count(pdf: bytes) -> int:
    return len(read(pdf).pages)


def text_of(pdf: bytes) -> str:
    """All extracted text. Content streams are compressed, so a byte search of
    the raw PDF finds nothing and would pass or fail for the wrong reason."""
    return "\n".join(page.extract_text() for page in read(pdf).pages)


# --- output ----------------------------------------------------------------


def test_it_produces_a_pdf() -> None:
    pdf = generate(spec())
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")


def test_output_is_deterministic() -> None:
    """I5. A reprint must be provably the same page, not merely a similar one.

    ReportLab stamps the current time into a document by default, which would
    make two identical booklets differ byte for byte and defeat any attempt to
    verify a reprint.
    """
    assert generate(spec()) == generate(spec())


def test_different_booklets_differ() -> None:
    other = spec(booklet_id=uuid.uuid4())
    assert generate(spec()) != generate(other)


def test_it_paginates_when_questions_exceed_one_page() -> None:
    tall = [QuestionSlot(f"Q{i}", Decimal("5"), height_mm=90) for i in range(1, 7)]
    pdf = generate(spec(questions=tall))
    assert page_count(pdf) >= 3


# --- anonymity -------------------------------------------------------------


def test_no_student_identity_can_be_placed_on_the_page() -> None:
    """`BookletSpec` has nowhere to put a name, so no caller can add one.

    Enforced structurally rather than by convention: anonymity that depends on
    every caller remembering is not anonymity.
    """
    fields = set(BookletSpec.__dataclass_fields__)
    assert fields == {"booklet_id", "exam_id", "exam_code", "exam_title", "questions"}
    for banned in ("student", "name", "index_number", "candidate"):
        assert not any(banned in f for f in fields)


def test_the_pdf_tells_the_student_not_to_write_their_name() -> None:
    assert "not write your name" in text_of(generate(spec()))


def test_the_printed_page_carries_the_declared_maximum_marks() -> None:
    """This is what turns question segmentation into a lookup rather than an
    inference, so it has to actually reach the paper."""
    text = text_of(generate(spec()))
    assert "QUESTION 1(a)" in text
    assert "6 marks" in text
    assert "10 marks" in text


def test_the_booklet_id_is_not_in_the_pdf_metadata() -> None:
    """Metadata survives printing to file and is trivially read, so the
    identifier lives only in the QR."""
    pdf = generate(spec())
    head = pdf[:2048]
    assert BOOKLET.hex.encode() not in head
    assert str(BOOKLET).encode() not in head


# --- the QR ----------------------------------------------------------------


def render_qr(payload: BookletPayload) -> np.ndarray:
    """Reproduce the generator's QR as an image, for decoding."""
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
    raw = np.frombuffer(buffer.getvalue(), dtype=np.uint8)
    return cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)


def test_the_printed_qr_decodes_back_to_its_payload() -> None:
    """The gate: what is printed must be readable, and must mean what it said."""
    payload = BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=2, page_total=5)

    raw, _, _ = cv2.QRCodeDetector().detectAndDecode(render_qr(payload))
    assert raw, "the QR could not be decoded at all"
    assert decode(raw) == payload


def test_the_qr_survives_being_photographed() -> None:
    """Downscaled, tilted and blurred — a phone in an exam hall, not a scanner."""
    payload = BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=1, page_total=3)
    image = render_qr(payload)

    small = cv2.resize(image, (160, 160), interpolation=cv2.INTER_AREA)
    height, width = small.shape
    shift = width * 0.05
    warped = cv2.warpPerspective(
        small,
        cv2.getPerspectiveTransform(
            np.float32([[0, 0], [width, 0], [width, height], [0, height]]),
            np.float32(
                [[shift, 0], [width, shift * 0.6], [width - shift, height], [0, height - shift]]
            ),
        ),
        (width, height),
        borderValue=255,
    )
    blurred = cv2.GaussianBlur(warped, (3, 3), 0)

    raw, _, _ = cv2.QRCodeDetector().detectAndDecode(blurred)
    assert raw, "the QR did not survive a realistic capture"
    assert decode(raw) == payload


def test_every_page_carries_its_own_page_number() -> None:
    """Page ordering and missing-page detection depend on this being per page,
    not per booklet."""
    payloads = [
        BookletPayload(booklet_id=BOOKLET, exam_id=EXAM, page_no=n, page_total=4)
        for n in range(1, 5)
    ]
    encoded = {p.encode() for p in payloads}
    assert len(encoded) == 4


# --- validation ------------------------------------------------------------


def test_a_booklet_needs_at_least_one_question() -> None:
    with pytest.raises(ValueError, match="at least one"):
        spec(questions=[])


def test_duplicate_question_numbers_are_rejected() -> None:
    """Two boxes with the same number would make segmentation ambiguous, and an
    answer could be scored against the wrong rubric point."""
    with pytest.raises(ValueError, match="duplicate"):
        spec(questions=[QuestionSlot("1", Decimal("5")), QuestionSlot("1", Decimal("5"))])


@pytest.mark.parametrize(
    ("value", "printed"),
    [
        (Decimal("6"), "6"),
        (Decimal("10"), "10"),  # normalize() alone renders this as 1E+1
        (Decimal("100"), "100"),
        (Decimal("2.5"), "2.5"),
        (Decimal("5.0"), "5"),
        (Decimal("0.5"), "0.5"),
    ],
)
def test_marks_print_as_numbers_a_student_can_read(value: Decimal, printed: str) -> None:
    """Caught in review of a real failure: `Decimal("10").normalize()` is
    `1E+1`, so the booklet would have gone to print reading "[1E+1 marks]"."""
    assert format_marks(value) == printed


def test_whole_tens_reach_the_page_correctly() -> None:
    pdf = generate(spec(questions=[QuestionSlot("1", Decimal("10"))]))
    text = text_of(pdf)
    assert "10 marks" in text
    assert "E+" not in text


@pytest.mark.parametrize("marks", [Decimal("0"), Decimal("-1")])
def test_non_positive_marks_are_rejected(marks: Decimal) -> None:
    with pytest.raises(ValueError, match="positive"):
        QuestionSlot("1", marks)


def test_a_blank_question_number_is_rejected() -> None:
    with pytest.raises(ValueError, match="blank"):
        QuestionSlot("   ", Decimal("5"))


def test_a_box_too_small_to_write_in_is_rejected() -> None:
    with pytest.raises(ValueError, match="minimum"):
        QuestionSlot("1", Decimal("5"), height_mm=5)
