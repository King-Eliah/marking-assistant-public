"""Booklet issue and download.

The PDF is never stored. `generate()` is deterministic, so a booklet is
reproduced byte-for-byte from its row plus the exam's questions — which means
there is no second copy to drift, no storage to back up, and a reprint is
provably the same page rather than merely a similar one.

The one thing that could break that is a change to `layout`, so every booklet
records the geometry version it was issued under and a download refuses on a
mismatch.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.core import audit_writer
from app.core.deps import CurrentClaims, CurrentScope, DbSession
from app.core.scope import NotFoundError, require_owned
from app.engines.booklet.generator import BookletSpec, QuestionSlot, generate
from app.engines.booklet.layout import LAYOUT_VERSION
from app.engines.booklet.payload import BookletPayload
from app.models.academic import Booklet, Exam, Question

router = APIRouter(tags=["booklets"])

#: An exam has a few hundred candidates at most. The cap is here so a typo in
#: a request cannot generate work measured in hours.
MAX_BOOKLETS_PER_REQUEST = 500


class BookletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exam_id: uuid.UUID
    page_count: int
    layout_version: str


class IssueRequest(BaseModel):
    count: int = Field(ge=1, le=MAX_BOOKLETS_PER_REQUEST)


def _load_exam(session: DbSession, scope: CurrentScope, exam_id: uuid.UUID) -> Exam:
    exam = session.execute(select(Exam).where(Exam.id == exam_id)).scalar_one_or_none()
    return require_owned(scope, exam, "exam", exam_id)


def _spec_for(session: DbSession, exam: Exam, booklet_id: uuid.UUID) -> BookletSpec:
    """Build the print specification from the exam's questions."""
    questions = list(
        session.execute(
            select(Question)
            .where(Question.exam_id == exam.id)
            .order_by(Question.position, Question.number)
        ).scalars()
    )
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This exam has no questions, so a booklet would have nowhere to write.",
        )

    return BookletSpec(
        booklet_id=booklet_id,
        exam_id=exam.id,
        exam_code=exam.code,
        exam_title=exam.title,
        questions=[
            QuestionSlot(
                number=q.number,
                max_marks=Decimal(q.max_marks),
                height_mm=float(q.answer_height_mm),
            )
            for q in questions
        ],
    )


@router.post(
    "/exams/{exam_id}/booklets",
    response_model=list[BookletOut],
    status_code=status.HTTP_201_CREATED,
)
def issue_booklets(
    exam_id: uuid.UUID,
    body: IssueRequest,
    scope: CurrentScope,
    claims: CurrentClaims,
    session: DbSession,
    request: Request,
) -> list[Booklet]:
    """Issue `count` anonymous booklets for an exam.

    Each gets its own UUID and its own QR. No student is attached: the
    invigilator hands them out, and identity is resolved only at export.
    """
    exam = _load_exam(session, scope, exam_id)
    issued: list[Booklet] = []

    for _ in range(body.count):
        booklet_id = uuid.uuid4()
        spec = _spec_for(session, exam, booklet_id)
        pdf = generate(spec)

        # Page count comes from generating, not from a second guess at
        # pagination. Two implementations of "how many pages" would eventually
        # disagree, and the QR would then claim a total the PDF contradicts.
        first_page = BookletPayload(
            booklet_id=booklet_id,
            exam_id=exam.id,
            page_no=1,
            page_total=_page_count(pdf),
        )

        booklet = Booklet(
            id=booklet_id,
            tenant_id=scope.tenant_id,
            exam_id=exam.id,
            page_count=first_page.page_total,
            qr_payload=first_page.encode(),
            layout_version=LAYOUT_VERSION,
        )
        session.add(booklet)
        issued.append(booklet)

    audit_writer.append(
        session,
        tenant_id=scope.tenant_id,
        actor_id=claims.user_id,
        action="booklets.issue",
        entity_type="exam",
        entity_id=str(exam_id),
        after={"count": body.count, "layout_version": LAYOUT_VERSION},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.flush()
    return issued


def _page_count(pdf: bytes) -> int:
    """Pages in a generated PDF, counted from the document itself."""
    return max(pdf.count(b"/Type /Page\n"), pdf.count(b"/Type/Page"), 1)


@router.get("/booklets/{booklet_id}.pdf")
def download_booklet(
    booklet_id: uuid.UUID,
    scope: CurrentScope,
    session: DbSession,
) -> Response:
    """Regenerate and stream one booklet.

    Deterministic, so this is the same file that was issued — not a
    re-rendering that happens to look similar.
    """
    booklet = session.execute(select(Booklet).where(Booklet.id == booklet_id)).scalar_one_or_none()
    booklet = require_owned(scope, booklet, "booklet", booklet_id)

    if booklet.layout_version != LAYOUT_VERSION:
        # Regenerating under different geometry would produce a page whose
        # fiducials sit elsewhere. It would look right and warp onto the wrong
        # coordinates, which is worse than refusing.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This booklet was issued under layout {booklet.layout_version}; "
                f"the current layout is {LAYOUT_VERSION}. Reprinting it would not "
                f"match the booklet the student wrote on."
            ),
        )

    exam = session.execute(select(Exam).where(Exam.id == booklet.exam_id)).scalar_one_or_none()
    if exam is None:
        raise NotFoundError("booklet", booklet_id)

    pdf = generate(_spec_for(session, exam, booklet.id))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{exam.code}-{booklet.id}.pdf"',
            # Deterministic output means the bytes for a given booklet never
            # change, so this is safe to cache hard.
            "Cache-Control": "private, max-age=31536000, immutable",
        },
    )


@router.get("/exams/{exam_id}/booklets", response_model=list[BookletOut])
def list_booklets(
    exam_id: uuid.UUID,
    scope: CurrentScope,
    session: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Booklet]:
    _load_exam(session, scope, exam_id)
    return list(
        session.execute(
            select(Booklet)
            .where(Booklet.exam_id == exam_id)
            .order_by(Booklet.created_at, Booklet.id)
            .limit(limit)
            .offset(offset)
        ).scalars()
    )


@router.get("/exams/{exam_id}/booklets/count")
def count_booklets(
    exam_id: uuid.UUID,
    scope: CurrentScope,
    session: DbSession,
) -> dict[str, int]:
    _load_exam(session, scope, exam_id)
    total = session.execute(
        select(func.count()).select_from(Booklet).where(Booklet.exam_id == exam_id)
    ).scalar_one()
    return {"count": int(total)}
