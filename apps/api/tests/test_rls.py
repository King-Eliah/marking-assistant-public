"""Row-Level Security — isolation layer one of two for I7.

These began as manual psql checks that caught a total isolation failure: the
policies existed, `\\d+` reported "forced row security enabled", and both
tenants still saw every row, because the connecting role was a superuser.
They are tests now so that regression cannot recur silently.

Every assertion runs through `app_engine`. Running them as the owner would
pass unconditionally and prove nothing.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine

pytestmark = pytest.mark.integration


def set_tenant(conn: sa.Connection, tenant_id: uuid.UUID | None) -> None:
    """Set the session tenant the RLS policies read."""
    value = str(tenant_id) if tenant_id else ""
    conn.execute(sa.text("SELECT set_config('app.tenant_id', :v, false)"), {"v": value})


def insert_course(conn: sa.Connection, tenant_id: uuid.UUID, code: str) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO courses (id, tenant_id, code, title, academic_year)"
            " VALUES (:id, :tid, :code, :code, '2026')"
        ),
        {"id": uuid.uuid4(), "tid": tenant_id, "code": code},
    )


def count_courses(conn: sa.Connection) -> int:
    return int(conn.execute(sa.text("SELECT count(*) FROM courses")).scalar_one())


def test_the_app_role_does_not_bypass_rls(app_engine: Engine) -> None:
    """The precondition every other test here depends on.

    A superuser or a role with BYPASSRLS makes the whole suite vacuous, so this
    is asserted rather than assumed.
    """
    with app_engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()
    assert row.rolsuper is False, "the app role must not be a superuser"
    assert row.rolbypassrls is False, "the app role must not have BYPASSRLS"


def test_a_tenant_sees_only_its_own_rows(
    app_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    alpha, beta = two_tenants

    with app_engine.begin() as conn:
        set_tenant(conn, alpha)
        insert_course(conn, alpha, "ALPHA-1")
    with app_engine.begin() as conn:
        set_tenant(conn, beta)
        insert_course(conn, beta, "BETA-1")

    with app_engine.connect() as conn:
        set_tenant(conn, alpha)
        assert count_courses(conn) == 1
        set_tenant(conn, beta)
        assert count_courses(conn) == 1


def test_no_tenant_set_sees_nothing(
    app_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Default-deny. Forgetting to set the tenant must yield nothing, not
    everything, and must not raise on an empty setting."""
    alpha, _ = two_tenants
    with app_engine.begin() as conn:
        set_tenant(conn, alpha)
        insert_course(conn, alpha, "ALPHA-2")

    with app_engine.connect() as conn:
        set_tenant(conn, None)
        assert count_courses(conn) == 0


def test_writing_for_another_tenant_is_rejected(
    app_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """WITH CHECK. Reading someone else's data is one hole; planting rows in
    their tenant is a worse one."""
    alpha, beta = two_tenants
    with app_engine.begin() as conn:
        set_tenant(conn, alpha)
        with pytest.raises(sa.exc.ProgrammingError, match="row-level security"):
            insert_course(conn, beta, "SNEAK")


def test_a_tenant_cannot_read_another_tenants_row_by_id(
    app_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Knowing the primary key must not help — the row is invisible, so a
    lookup returns nothing and the caller can only answer 404."""
    alpha, beta = two_tenants
    course_id = uuid.uuid4()

    with app_engine.begin() as conn:
        set_tenant(conn, beta)
        conn.execute(
            sa.text(
                "INSERT INTO courses (id, tenant_id, code, title, academic_year)"
                " VALUES (:id, :tid, 'BETA-2', 'Beta', '2026')"
            ),
            {"id": course_id, "tid": beta},
        )

    with app_engine.connect() as conn:
        set_tenant(conn, alpha)
        found = conn.execute(
            sa.text("SELECT id FROM courses WHERE id = :id"), {"id": course_id}
        ).first()
    assert found is None


def test_tenants_table_is_itself_scoped(
    app_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """The tenant list must not be an enumeration of every institution."""
    alpha, _ = two_tenants
    with app_engine.connect() as conn:
        set_tenant(conn, alpha)
        rows = conn.execute(sa.text("SELECT id FROM tenants")).scalars().all()
    assert rows == [alpha]
