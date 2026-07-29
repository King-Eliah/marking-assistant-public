"""Declarative base and the mixins every table uses.

Every table carries `tenant_id` (I7) and `created_at`. Tenancy is enforced
twice — Postgres RLS and a service-layer scope check — so that a bug in one
layer does not leak data. See .claude/rules/api.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#: Explicit naming so Alembic autogenerate produces stable, reviewable names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for every model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKey:
    """UUID primary key, generated application-side so callers know the id early."""

    id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class Timestamped:
    """`created_at`, set by the database so it cannot be back-dated by a client."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TenantScoped:
    """`tenant_id` on every row — the anchor for RLS and the service-layer guard.

    Indexed because every query filters on it, and RLS adds that predicate to
    every statement whether the caller wrote it or not.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
