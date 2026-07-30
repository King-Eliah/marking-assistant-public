"""Appending to the audit chain.

The only supported way to write `audit_log`. A row inserted by any other path
gets no valid `prev_hash` and breaks verification from that point forward —
which is the intended behaviour, not a limitation.

Chains are per tenant. A tenant can only read its own rows under RLS, so a
global chain would be unverifiable by anyone except a superuser, and the point
of the chain is that the institution can check it themselves.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.audit import GENESIS_HASH, compute_row_hash
from app.models.audit import AuditLog


class MissingActorError(Exception):
    """A human action was recorded without saying who performed it.

    I1: no mark is final without an authenticated human action. An audit row
    claiming a human acted, with no actor, is exactly the evidence gap that
    invariant exists to prevent.
    """

    def __init__(self, action: str) -> None:
        super().__init__(f"{action!r} is a human action and requires an actor_id")


#: Actions only a person can perform. Recording one without an actor is a bug,
#: not a permitted edge case.
HUMAN_ACTIONS: frozenset[str] = frozenset(
    {
        "marks.confirm",
        "marks.adjust",
        "marks.finalise",
        "rubric.freeze",
        "transcript.correct",
        "identity.reveal",
        "results.export",
    }
)


def _lock_tenant_chain(session: Session, tenant_id: uuid.UUID) -> None:
    """Serialise appends within one tenant's chain.

    Two concurrent appends would otherwise read the same `prev_hash` and write
    two rows claiming the same predecessor — a forked chain that verifies as
    broken forever after, with no way to tell which branch was genuine.

    A transaction-scoped advisory lock is released on commit or rollback, so a
    crashed worker cannot wedge a tenant's audit log.
    """
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"audit:{tenant_id}"},
    )


def _last_hash(session: Session, tenant_id: uuid.UUID) -> str:
    row = session.execute(
        select(AuditLog.row_hash)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return row or GENESIS_HASH


def append(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Append one event and return it.

    Caller commits. The advisory lock is held until then, so the chain cannot
    fork between computing the hash and writing the row.
    """
    if action in HUMAN_ACTIONS and actor_id is None:
        raise MissingActorError(action)

    _lock_tenant_chain(session, tenant_id)
    prev_hash = _last_hash(session, tenant_id)

    fields: dict[str, Any] = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before": before,
        "after": after,
        "reason": reason,
        # `at` is set by the database default, so it is excluded from the hash
        # here and recomputed from the stored value at verification time.
        "at": None,
    }

    entry = AuditLog(
        **{k: v for k, v in fields.items() if k != "at"},
        ip=ip,
        user_agent=user_agent,
        prev_hash=prev_hash,
        row_hash=compute_row_hash(prev_hash, fields),
    )
    session.add(entry)
    session.flush()
    return entry


def read_chain(session: Session, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Read one tenant's chain in insertion order, shaped for `verify_chain`."""
    rows = session.execute(
        select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(AuditLog.id)
    ).scalars()

    return [
        {
            "tenant_id": r.tenant_id,
            "actor_id": r.actor_id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "before": r.before,
            "after": r.after,
            "reason": r.reason,
            "at": None,
            "prev_hash": r.prev_hash,
            "row_hash": r.row_hash,
        }
        for r in rows
    ]
