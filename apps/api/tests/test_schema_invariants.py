"""Structural guarantees about the schema itself.

Alembic autogenerate produces tables, indexes and constraints. It does not
produce RLS policies or grants, so a table added the normal way arrives
readable across every tenant — and nothing about it looks wrong until one
institution reads another's data.

These tests compare the live database against the declared models, so a table
that forgets fails the build rather than shipping quietly. This is the only
defence that keeps working when nobody remembers the rule.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine

from app.models import Base
from app.models.base import TenantScoped

pytestmark = pytest.mark.integration

#: `tenants` is scoped by its own `id` rather than a `tenant_id` column, so it
#: is checked separately below.
SELF_SCOPED = {"tenants"}


def declared_tenant_tables() -> set[str]:
    """Every mapped table inheriting the tenant mixin."""
    return {
        mapper.class_.__tablename__
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, TenantScoped)
    }


def test_the_models_actually_declare_tenant_tables() -> None:
    """Guards the guard: if this returned nothing, every test below would pass
    vacuously and prove the opposite of what it claims."""
    tables = declared_tenant_tables()
    assert len(tables) >= 5
    assert {"courses", "exams", "questions", "booklets"} <= tables


def test_every_tenant_table_has_a_tenant_id_column(owner_engine: Engine) -> None:
    inspector = sa.inspect(owner_engine)
    for table in declared_tenant_tables():
        columns = {c["name"] for c in inspector.get_columns(table)}
        assert "tenant_id" in columns, f"{table} has no tenant_id"


def test_every_tenant_table_is_protected(owner_engine: Engine) -> None:
    """RLS enabled *and* forced, on every one.

    `FORCE` is the half that gets missed: without it the table owner bypasses
    the policy, which is exactly how this project shipped a migration whose
    isolation was completely inert.
    """
    with owner_engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace"
            )
        ).all()
    state = {r.relname: (r.relrowsecurity, r.relforcerowsecurity) for r in rows}

    for table in declared_tenant_tables() | SELF_SCOPED:
        enabled, forced = state.get(table, (False, False))
        assert enabled, f"{table} does not have RLS enabled"
        assert forced, f"{table} does not FORCE RLS, so the owner bypasses it"


def test_every_tenant_table_has_an_isolation_policy(owner_engine: Engine) -> None:
    with owner_engine.connect() as conn:
        policies = set(
            conn.execute(sa.text("SELECT tablename FROM pg_policies WHERE schemaname = 'public'"))
            .scalars()
            .all()
        )

    for table in declared_tenant_tables() | SELF_SCOPED:
        assert table in policies, f"{table} has no tenant_isolation policy"


def test_the_app_role_can_reach_every_tenant_table(app_engine: Engine) -> None:
    """A protected table the application cannot read is just as broken as an
    unprotected one — it fails at runtime instead of leaking."""
    with app_engine.connect() as conn:
        granted = set(
            conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.table_privileges "
                    "WHERE grantee = current_user AND privilege_type = 'SELECT'"
                )
            )
            .scalars()
            .all()
        )

    for table in declared_tenant_tables():
        assert table in granted, f"{table} is not granted to the application role"


def test_the_policy_uses_a_null_safe_tenant_expression(owner_engine: Engine) -> None:
    """`''::uuid` raises rather than matching nothing.

    Without NULLIF, an unset tenant produces a database error instead of an
    empty result. It still fails closed, but an error is the wrong signal for
    "no tenant selected" and surfaces as a 500.
    """
    with owner_engine.connect() as conn:
        expressions = (
            conn.execute(sa.text("SELECT qual FROM pg_policies WHERE schemaname = 'public'"))
            .scalars()
            .all()
        )

    assert expressions
    for expression in expressions:
        assert "NULLIF" in expression.upper(), expression


def test_the_audit_log_is_never_granted_update_or_delete(app_engine: Engine) -> None:
    """I4. Checked here as well as in the immutability suite because this one
    runs against whatever the migrations actually produced."""
    with app_engine.connect() as conn:
        privileges = set(
            conn.execute(
                sa.text(
                    "SELECT privilege_type FROM information_schema.table_privileges "
                    "WHERE table_name = 'audit_log' AND grantee = current_user"
                )
            )
            .scalars()
            .all()
        )

    assert "UPDATE" not in privileges
    assert "DELETE" not in privileges


def test_no_model_drift(owner_engine: Engine) -> None:
    """Every mapped table exists in the database.

    Catches a model added without a migration, which otherwise fails at the
    first query rather than at the build.
    """
    existing = set(sa.inspect(owner_engine).get_table_names())
    declared = {mapper.class_.__tablename__ for mapper in Base.registry.mappers}
    assert declared <= existing, f"missing migrations for: {sorted(declared - existing)}"
