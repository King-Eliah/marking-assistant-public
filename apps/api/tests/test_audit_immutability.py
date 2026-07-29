"""The audit log is append-only at the database level (I4).

The claim in spec.md §5.3 is "nobody, including ADMIN, can modify or delete the
audit log". Grants alone cannot carry that claim, because the table owner keeps
its rights regardless — so these tests assert against the *owner* connection,
which is a superuser in dev. If the guard holds there, it holds everywhere.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine

pytestmark = pytest.mark.integration


@pytest.fixture
def audited_tenant(owner_engine: Engine) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    with owner_engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO tenants (id, name, data_region, retention_days,"
                " ai_monthly_cap_usd) VALUES (:id, 'Audited', 'eu', 180, 100)"
            ),
            {"id": tenant_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO audit_log (tenant_id, action, entity_type, prev_hash, row_hash)"
                " VALUES (:tid, 'marks.finalise', 'mark', :prev, :row)"
            ),
            {"tid": tenant_id, "prev": "0" * 64, "row": uuid.uuid4().hex},
        )
    return tenant_id


def test_update_is_denied_for_the_superuser_owner(
    owner_engine: Engine, audited_tenant: uuid.UUID
) -> None:
    with owner_engine.begin() as conn, pytest.raises(sa.exc.DBAPIError, match="append-only"):
        conn.execute(
            sa.text("UPDATE audit_log SET action = 'tampered' WHERE tenant_id = :t"),
            {"t": audited_tenant},
        )


def test_delete_is_denied_for_the_superuser_owner(
    owner_engine: Engine, audited_tenant: uuid.UUID
) -> None:
    with owner_engine.begin() as conn, pytest.raises(sa.exc.DBAPIError, match="append-only"):
        conn.execute(sa.text("DELETE FROM audit_log WHERE tenant_id = :t"), {"t": audited_tenant})


def test_truncate_is_denied(owner_engine: Engine, audited_tenant: uuid.UUID) -> None:
    """A FOR EACH ROW trigger does not fire on TRUNCATE.

    Before the statement-level trigger existed, this wiped the entire log in one
    statement without raising — the row trigger protected every row individually
    and the table not at all.
    """
    with owner_engine.begin() as conn, pytest.raises(sa.exc.DBAPIError, match="append-only"):
        conn.execute(sa.text("TRUNCATE audit_log"))


def test_the_row_survives_every_attempt(owner_engine: Engine, audited_tenant: uuid.UUID) -> None:
    """Errors are not enough — the content has to still be there afterwards."""
    for statement in (
        "UPDATE audit_log SET action = 'tampered' WHERE tenant_id = :t",
        "DELETE FROM audit_log WHERE tenant_id = :t",
    ):
        with owner_engine.connect() as conn:  # noqa: SIM117
            with conn.begin(), pytest.raises(sa.exc.DBAPIError):
                conn.execute(sa.text(statement), {"t": audited_tenant})

    with owner_engine.connect() as conn:
        action = conn.execute(
            sa.text("SELECT action FROM audit_log WHERE tenant_id = :t"),
            {"t": audited_tenant},
        ).scalar_one()
    assert action == "marks.finalise"


def test_the_app_role_cannot_update_or_delete(app_engine: Engine) -> None:
    """Belt and braces: the grant should stop it before the trigger has to."""
    with app_engine.connect() as conn:
        privileges = (
            conn.execute(
                sa.text(
                    "SELECT privilege_type FROM information_schema.table_privileges"
                    " WHERE table_name = 'audit_log' AND grantee = current_user"
                )
            )
            .scalars()
            .all()
        )

    assert "INSERT" in privileges
    assert "SELECT" in privileges
    assert "UPDATE" not in privileges
    assert "DELETE" not in privileges
