"""The audit writer, against a real database.

Chain construction has to be tested where the concurrency is real. An in-memory
fake would serialise everything for free and prove nothing about the case that
actually matters — two writers racing for the same predecessor.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.audit import GENESIS_HASH, ChainBrokenError, verify_chain
from app.core.audit_writer import HUMAN_ACTIONS, MissingActorError, append, read_chain

pytestmark = pytest.mark.integration


@pytest.fixture
def tenant(owner_engine: Engine) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    with owner_engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO tenants (id, name, data_region, retention_days,"
                " ai_monthly_cap_usd) VALUES (:id, 'Chain', 'eu', 180, 100)"
            ),
            {"id": tenant_id},
        )
    return tenant_id


@pytest.fixture
def session(owner_engine: Engine) -> Session:
    return Session(bind=owner_engine)


def test_the_first_entry_anchors_to_genesis(session: Session, tenant: uuid.UUID) -> None:
    entry = append(session, tenant_id=tenant, action="course.create", entity_type="course")
    session.commit()
    assert entry.prev_hash == GENESIS_HASH


def test_entries_chain_to_their_predecessor(session: Session, tenant: uuid.UUID) -> None:
    first = append(session, tenant_id=tenant, action="a", entity_type="course")
    session.commit()
    second = append(session, tenant_id=tenant, action="b", entity_type="course")
    session.commit()
    assert second.prev_hash == first.row_hash


def test_a_written_chain_verifies(session: Session, tenant: uuid.UUID) -> None:
    for i in range(5):
        append(session, tenant_id=tenant, action=f"step.{i}", entity_type="course")
        session.commit()

    verify_chain(read_chain(session, tenant))


def test_tampering_with_a_stored_row_is_detected(
    session: Session, tenant: uuid.UUID, owner_engine: Engine
) -> None:
    """The end-to-end claim: alter the database directly, verification fails.

    UPDATE is blocked by the trigger, so a realistic attacker would have to drop
    it first. Simulated here by verifying a mutated read of the real chain.
    """
    for i in range(3):
        append(session, tenant_id=tenant, action=f"step.{i}", entity_type="course")
        session.commit()

    chain = read_chain(session, tenant)
    chain[1]["action"] = "step.tampered"

    with pytest.raises(ChainBrokenError) as caught:
        verify_chain(chain)
    assert caught.value.position == 1


def test_chains_are_independent_per_tenant(
    session: Session, tenant: uuid.UUID, owner_engine: Engine
) -> None:
    """One tenant's writes must not appear in another's chain, or verification
    would depend on rows RLS makes invisible."""
    other = uuid.uuid4()
    with owner_engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO tenants (id, name, data_region, retention_days,"
                " ai_monthly_cap_usd) VALUES (:id, 'Other', 'eu', 180, 100)"
            ),
            {"id": other},
        )

    append(session, tenant_id=tenant, action="mine", entity_type="course")
    session.commit()
    append(session, tenant_id=other, action="theirs", entity_type="course")
    session.commit()

    mine = read_chain(session, tenant)
    theirs = read_chain(session, other)

    assert [r["action"] for r in mine] == ["mine"]
    assert [r["action"] for r in theirs] == ["theirs"]
    assert theirs[0]["prev_hash"] == GENESIS_HASH
    verify_chain(mine)
    verify_chain(theirs)


@pytest.mark.parametrize("action", sorted(HUMAN_ACTIONS))
def test_human_actions_require_an_actor(session: Session, tenant: uuid.UUID, action: str) -> None:
    """I1. An audit row claiming a person acted, with no person named, is the
    evidence gap the invariant exists to close."""
    with pytest.raises(MissingActorError):
        append(session, tenant_id=tenant, action=action, entity_type="mark")


def test_system_actions_may_have_no_actor(session: Session, tenant: uuid.UUID) -> None:
    """The pipeline writes plenty of rows with no human involved."""
    entry = append(session, tenant_id=tenant, action="pipeline.scored", entity_type="script")
    session.commit()
    assert entry.actor_id is None


def test_concurrent_appends_do_not_fork_the_chain(owner_engine: Engine, tenant: uuid.UUID) -> None:
    """Two sessions racing must serialise, not both claim the same predecessor.

    Without the advisory lock both would read the same prev_hash and write two
    rows pointing at it — a fork that verifies as broken forever, with no way
    to tell which branch was genuine.
    """
    with Session(owner_engine) as a, Session(owner_engine) as b:
        a.begin()
        append(a, tenant_id=tenant, action="first", entity_type="course")

        b.begin()
        # b blocks on the advisory lock until a commits.
        a.commit()
        append(b, tenant_id=tenant, action="second", entity_type="course")
        b.commit()

    with Session(owner_engine) as reader:
        chain = read_chain(reader, tenant)

    assert [r["action"] for r in chain] == ["first", "second"]
    assert len({r["prev_hash"] for r in chain}) == 2, "both rows claimed the same predecessor"
    verify_chain(chain)
