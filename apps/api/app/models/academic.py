"""Exams, questions, and printed booklets. See docs/spec.md §3."""

from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class ExamStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    MARKING = "MARKING"
    MODERATION = "MODERATION"
    CLOSED = "CLOSED"


class AnswerType(StrEnum):
    """spec.md §1.4 draws the v1 scope line here.

    PROSE and SHORT are marked. Everything else is routed to a human rather
    than attempted — "the system knows what it cannot mark" is a stronger
    position than "the system attempts everything".
    """

    PROSE = "PROSE"
    SHORT = "SHORT"
    LIST = "LIST"
    NUMERIC = "NUMERIC"
    DIAGRAM = "DIAGRAM"
    CODE = "CODE"
    MATH = "MATH"

    @property
    def auto_markable(self) -> bool:
        return self in {AnswerType.PROSE, AnswerType.SHORT}


class Exam(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    __tablename__ = "exams"

    course_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    total_marks: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[ExamStatus] = mapped_column(String(16), nullable=False, default=ExamStatus.DRAFT)
    #: Default true. Anonymous marking removes marker bias and is a genuine
    #: academic selling point (spec.md §1.1).
    anonymous_marking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Question(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("exam_id", "number"),)

    exam_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    #: "3(a)". Printed on the booklet, which is what makes segmentation a
    #: lookup rather than an inference.
    number: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    max_marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    answer_type: Mapped[AnswerType] = mapped_column(
        String(16), nullable=False, default=AnswerType.PROSE
    )
    #: Ordering on the printed page. Explicit rather than inferred from
    #: `number`, because "10" sorts before "2" as text.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Printed height of the answer region, in millimetres.
    answer_height_mm: Mapped[int] = mapped_column(Integer, nullable=False, default=60)


class Booklet(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One printed booklet, identified anonymously.

    No student reference here. Identity lives in a separate restricted table
    joined only at export (spec.md §3), so the marking path never sees it.

    The PDF is not stored. `generate()` is deterministic, so the booklet can be
    reproduced byte-for-byte from this row plus the exam's questions —
    provided `layout_version` still matches, which is why it is recorded.
    """

    __tablename__ = "booklets"

    exam_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The first page's QR content. Unique across the platform, so a scan
    #: resolves to exactly one booklet or to none.
    qr_payload: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    #: Geometry in force when this booklet was printed. A booklet printed under
    #: one layout and detected under another produces a valid-looking warp onto
    #: the wrong coordinates, so a mismatch has to be detectable rather than
    #: silently tolerated.
    layout_version: Mapped[str] = mapped_column(String(16), nullable=False)
