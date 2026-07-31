"""Courses.

The first tenant-scoped resource, and the one the stage 1 isolation gate is
proven against: a cross-tenant read must return 404 and must appear in the
audit log.

Both isolation layers are in play here and neither is redundant. RLS makes the
row invisible, so the query returns nothing. The service-layer guard then turns
"nothing" into a 404 — and would also reject a row that RLS somehow returned,
which is what makes the two layers independent rather than one layer written
twice.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.core import audit_writer
from app.core.deps import CurrentClaims, CurrentScope, DbSession
from app.core.scope import NotFoundError, require_owned
from app.models.tenancy import Course

router = APIRouter(prefix="/courses", tags=["courses"])


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    academic_year: str
    created_at: datetime


@router.get(
    "/{course_id}",
    response_model=CourseOut,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
)
def get_course(
    course_id: uuid.UUID,
    scope: CurrentScope,
    claims: CurrentClaims,
    session: DbSession,
    request: Request,
) -> Course:
    """Read one course.

    A course belonging to another institution is indistinguishable from one
    that does not exist. Same status, same body, same timing characteristics —
    see `require_owned`.
    """
    course = session.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()

    try:
        return require_owned(scope, course, "course", course_id)
    except NotFoundError:
        # A denied cross-tenant read is a security event, not a routine miss,
        # and the institution has to be able to see that it happened. Recorded
        # in the *caller's* chain, since that is who attempted it.
        audit_writer.append(
            session,
            tenant_id=scope.tenant_id,
            actor_id=claims.user_id,
            action="course.access_denied",
            entity_type="course",
            entity_id=str(course_id),
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        session.commit()
        raise


@router.get("", response_model=list[CourseOut])
def list_courses(scope: CurrentScope, session: DbSession) -> list[Course]:
    """List this tenant's courses.

    No tenant filter in the query on purpose: RLS supplies it. If a future
    change breaks the policy, `test_listing_never_leaks_another_tenant` fails
    rather than this endpoint quietly returning everyone's courses.
    """
    del scope  # RLS scopes this; the parameter documents that auth is required
    return list(session.execute(select(Course).order_by(Course.code)).scalars())
