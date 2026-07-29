"""Tenants and users. See docs/spec.md §3."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CHAR,
    DateTime,
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


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INVITED = "INVITED"


class Role(StrEnum):
    """MVP subset. spec.md §5.3 defines six; the other four land post-MVP."""

    ADMIN = "ADMIN"
    LECTURER = "LECTURER"


class Tenant(UUIDPrimaryKey, Timestamped, Base):
    """An institution. Institutions, not users, are the unit of isolation."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str | None] = mapped_column(CHAR(2))
    data_region: Mapped[str] = mapped_column(Text, nullable=False, default="eu")
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    ai_monthly_cap_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("100.00")
    )


class User(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """A person within one tenant. Email is unique per tenant, not globally."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)  # argon2id
    role: Mapped[Role] = mapped_column(String(32), nullable=False, default=Role.LECTURER)
    status: Mapped[UserStatus] = mapped_column(
        String(16), nullable=False, default=UserStatus.ACTIVE
    )
    failed_logins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Course(UUIDPrimaryKey, TenantScoped, Timestamped, Base):
    """Academic structure. The simplest tenant-scoped resource, used by the
    stage 1 isolation test."""

    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "academic_year"),)

    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    academic_year: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        pg.UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
