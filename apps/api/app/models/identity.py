"""Student identity, kept apart from everything on the marking path.

Two tables, deliberately separate from `booklets`:

- `enrolments` — the class list. An index number that is not enrolled in the
  course is rejected on sight, which catches most OCR misreads for free: a
  wrong digit almost never lands on another *enrolled* student.
- `student_identity_map` — the booklet-to-student link, encrypted, joined only
  at export.

Nothing in the marking flow reads either. That is what makes anonymous marking
a property of the schema rather than a promise about behaviour.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScoped, Timestamped, UUIDPrimaryKey


class Enrolment(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """One student registered for one exam.

    Index numbers are stored in the clear here on purpose. This is the class
    list the institution already holds and already prints; encrypting it would
    add no protection while making the membership check — the whole point of
    the table — impossible.
    """

    __tablename__ = "enrolments"
    __table_args__ = (UniqueConstraint("exam_id", "index_number"),)

    exam_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    #: Free-form text, not a pattern. KNUST formats vary by faculty and year,
    #: so membership in this list is the validation rather than any regex.
    index_number: Mapped[str] = mapped_column(Text, nullable=False)
    #: Optional, for the exams officer's own reconciliation. Never shown to a
    #: marker and never used by the pipeline.
    display_name: Mapped[str | None] = mapped_column(Text)


class BookletIdentity(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Which student wrote which booklet.

    Written after capture, once a human has confirmed what the identity box
    says. Never written automatically from OCR alone: a misread digit here
    puts a mark on the wrong student's record, which is the worst outcome this
    system can produce.
    """

    __tablename__ = "student_identity_map"
    __table_args__ = (UniqueConstraint("booklet_id"),)

    booklet_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("booklets.id", ondelete="RESTRICT"), nullable=False
    )
    #: Fernet ciphertext. See app/core/crypto.py.
    index_number_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    #: The enrolment this was matched against. A row here without one means the
    #: link was made to a student not registered for the exam, which should be
    #: impossible and is worth being able to query for.
    enrolment_id: Mapped[uuid.UUID | None] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("enrolments.id", ondelete="RESTRICT")
    )

    #: Who confirmed the reading, and how confident the OCR was when they did.
    #: Kept so a later dispute can distinguish "the machine was sure and the
    #: human agreed" from "the machine was unsure and the human overrode it".
    confirmed_by: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    #: What the OCR proposed, when a human changed it. Null when they agreed.
    ocr_suggestion: Mapped[str | None] = mapped_column(Text)

    #: Set the first time identity is revealed for export. spec.md §5.3 makes
    #: revealing an audited event in its own right.
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revealed_by: Mapped[uuid.UUID | None] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
