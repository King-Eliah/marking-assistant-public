"""tenancy courses and audit log

Revision ID: 948dd5e979f4
Revises:
Create Date: 2026-07-29 23:01:24.968360

Adds the stage 1 tables plus the two things autogenerate cannot produce:
Row-Level Security (I7) and audit immutability (I4).

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "948dd5e979f4"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Tables carrying tenant_id. Every one gets an isolation policy.
TENANT_SCOPED_TABLES = ("users", "courses", "audit_log")

#: The role the application connects as. Deliberately NOT the migration owner.
#:
#: A superuser — which is what the default compose role is — bypasses RLS
#: entirely, and FORCE ROW LEVEL SECURITY does not apply to it. Policies then
#: exist, read correctly in \d+, and filter nothing. The only way isolation
#: actually holds is to connect as a role with neither SUPERUSER nor BYPASSRLS.
APP_ROLE = "marking_app"


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("country_code", sa.CHAR(length=2), nullable=True),
        sa.Column("data_region", sa.Text(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("ai_monthly_cap_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("failed_logins", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_users_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("tenant_id", "email", name=op.f("uq_users_tenant_id")),
    )
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("row_hash", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_audit_log_actor_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_audit_log_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
        sa.UniqueConstraint("row_hash", name=op.f("uq_audit_log_row_hash")),
    )
    op.create_index(op.f("ix_audit_log_tenant_id"), "audit_log", ["tenant_id"], unique=False)
    op.create_table(
        "courses",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("academic_year", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_courses_owner_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_courses_tenant_id_tenants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint(
            "tenant_id", "code", "academic_year", name=op.f("uq_courses_tenant_id")
        ),
    )
    op.create_index(op.f("ix_courses_tenant_id"), "courses", ["tenant_id"], unique=False)

    _create_application_role()
    _enable_row_level_security()
    _make_audit_log_immutable()


def _create_application_role() -> None:
    """The unprivileged role the API and workers connect as.

    Dev-only password. In any deployed environment this role is provisioned
    out of band with a secret from the secret manager, and this block is a
    no-op because the role already exists.
    """
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
            CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_ROLE}'
              NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT;
          END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT SELECT ON tenants TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON users, courses TO {APP_ROLE}")
    # audit_log is append-only even for the application (I4)
    op.execute(f"GRANT SELECT, INSERT ON audit_log TO {APP_ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")


def _enable_row_level_security() -> None:
    """Layer one of two for I7. The service-layer guard is the other.

    `FORCE ROW LEVEL SECURITY` makes the policy apply to the table owner too.
    It does *not* apply to a SUPERUSER or a role with BYPASSRLS — hence
    APP_ROLE above. Without that, these policies read correctly in `\\d+` and
    filter nothing.

    Default-deny relies on `NULLIF`. `current_setting(..., true)` yields NULL on
    a fresh connection but an *empty string* after `RESET`, and `''::uuid`
    raises rather than returning nothing. That still fails closed, but an error
    is the wrong signal for "no tenant selected" — NULLIF turns both cases into
    NULL, so the predicate is NULL and no rows match.
    """
    tenant_expr = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"

    for table in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
              USING (tenant_id = {tenant_expr})
              WITH CHECK (tenant_id = {tenant_expr})
            """
        )

    # A tenant may only see its own row here, keyed on id rather than tenant_id.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON tenants
          USING (id = {tenant_expr})
          WITH CHECK (id = {tenant_expr})
        """
    )


def _make_audit_log_immutable() -> None:
    """I4 and spec.md §5.3: nobody, including ADMIN, may alter the audit log.

    Revoking is necessary but not sufficient — the table owner keeps its rights
    regardless. The trigger is what actually holds, because it fires for every
    role including superusers.
    """
    op.execute("REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_is_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
          RAISE EXCEPTION 'audit_log is append-only: % denied', TG_OP
            USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_log_no_update_or_delete
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_is_append_only()
        """
    )
    # A FOR EACH ROW trigger does not fire on TRUNCATE, so the row trigger above
    # leaves the whole log wipeable in one statement. Verified: TRUNCATE removed
    # every row without raising. A statement-level trigger is the only thing
    # that closes it.
    op.execute(
        """
        CREATE TRIGGER audit_log_no_truncate
        BEFORE TRUNCATE ON audit_log
        FOR EACH STATEMENT EXECUTE FUNCTION audit_log_is_append_only()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update_or_delete ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_is_append_only()")
    for table in (*TENANT_SCOPED_TABLES, "tenants"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    # The role is cluster-level and may be shared, so revoke rather than drop.
    # Guarded: the role is absent when downgrading a database that never had it.
    op.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
            REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {APP_ROLE};
            REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {APP_ROLE};
            REVOKE USAGE ON SCHEMA public FROM {APP_ROLE};
          END IF;
        END
        $$
        """
    )

    op.drop_index(op.f("ix_courses_tenant_id"), table_name="courses")
    op.drop_table("courses")
    op.drop_index(op.f("ix_audit_log_tenant_id"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
