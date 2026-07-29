"""Database engine and tenant-scoped sessions.

The application connects as an unprivileged role so RLS applies to it — see
the migration's `APP_ROLE` note. Every session that touches tenant data must
declare its tenant before issuing a statement, because the RLS policies read
`app.tenant_id` and default to matching nothing.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

#: The Postgres setting the RLS policies read.
TENANT_SETTING = "app.tenant_id"


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def set_session_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    """Bind this database session to one tenant.

    `set_config(..., false)` scopes the value to the session rather than the
    transaction, so it survives commits within the same connection. Pooled
    connections are reset by `reset_session_tenant` before release.
    """
    session.execute(
        text("SELECT set_config(:name, :value, false)"),
        {"name": TENANT_SETTING, "value": str(tenant_id)},
    )


def reset_session_tenant(session: Session) -> None:
    """Clear the tenant before a pooled connection goes back.

    Without this a connection carries its last tenant into whoever borrows it
    next, which is a cross-tenant leak that no policy can catch — the policy
    would be applied faithfully, to the wrong tenant.
    """
    session.execute(
        text("SELECT set_config(:name, '', false)"),
        {"name": TENANT_SETTING},
    )


@contextmanager
def tenant_session(tenant_id: uuid.UUID) -> Iterator[Session]:
    """A session bound to one tenant for its whole lifetime."""
    session = get_sessionmaker()()
    try:
        set_session_tenant(session, tenant_id)
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        try:
            reset_session_tenant(session)
            session.commit()
        finally:
            session.close()
