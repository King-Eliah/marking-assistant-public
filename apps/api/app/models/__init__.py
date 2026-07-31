"""SQLAlchemy models.

Imported here so Alembic autogenerate sees every table. A model not reachable
from this module silently will not get a migration.
"""

from app.models.academic import (
    AnswerType,
    Booklet,
    Exam,
    ExamStatus,
    Question,
)
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.tenancy import Course, Role, Tenant, User, UserStatus

__all__ = [
    "AnswerType",
    "AuditLog",
    "Base",
    "Booklet",
    "Course",
    "Exam",
    "ExamStatus",
    "Question",
    "Role",
    "Tenant",
    "User",
    "UserStatus",
]
