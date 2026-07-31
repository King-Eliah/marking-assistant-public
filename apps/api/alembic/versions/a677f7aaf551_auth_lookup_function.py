"""auth lookup function

Revision ID: a677f7aaf551
Revises: f7b402b377f4
Create Date: 2026-07-31 18:40:30.533862

Login is the one operation that cannot know its tenant in advance — the tenant
is a *result* of authenticating, not an input to it. But `users` is under RLS,
so a login query with no `app.tenant_id` set correctly sees nothing, and a user
is invisible to their own sign-in.

The wrong fixes are instructive:

- connect as the owner for login: that role bypasses RLS entirely, so any bug
  in the login path could read every user on the platform
- add a policy allowing unscoped reads of `users`: not an exception for login,
  a permanent hole any query can walk through
- put the institution in the sign-in form: pushes the problem onto the user and
  contradicts frontend.md §A1

A `SECURITY DEFINER` function is the narrow answer. It runs with the definer's
privileges, so it can see across tenants — but it is the *only* thing that can,
it takes one argument, and it returns exactly the columns authentication needs.
`password_hash` leaves the database as the argon2 digest it already is at rest.

`search_path` is pinned on every one. Without that, anyone able to create
objects could shadow `public.users` with their own table and have these
functions read it instead: the classic SECURITY DEFINER escalation.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a677f7aaf551"
down_revision: str | None = "f7b402b377f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "marking_app"


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION auth_lookup(p_email TEXT)
        RETURNS TABLE (
            id            UUID,
            tenant_id     UUID,
            email         TEXT,
            password_hash TEXT,
            role          TEXT,
            status        TEXT,
            failed_logins INT,
            locked_until  TIMESTAMPTZ
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        STABLE
        AS $$
            SELECT u.id, u.tenant_id, u.email, u.password_hash,
                   u.role::text, u.status::text, u.failed_logins, u.locked_until
            FROM users u
            WHERE lower(u.email) = lower(p_email)
            LIMIT 1
        $$
        """
    )
    # Nobody may call it by default; the application role is granted explicitly.
    op.execute("REVOKE ALL ON FUNCTION auth_lookup(TEXT) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_lookup(TEXT) TO {APP_ROLE}")

    # Recording a failed attempt has the same problem: the counter must be
    # incremented before the caller has a tenant to scope by. Kept as its own
    # function so neither does more than one job.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION auth_record_failure(
            p_user_id UUID, p_max_failures INT, p_lockout_minutes INT
        )
        RETURNS INT
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        DECLARE
            v_failures INT;
        BEGIN
            UPDATE users
               SET failed_logins = failed_logins + 1,
                   locked_until = CASE
                       WHEN failed_logins + 1 >= p_max_failures
                       THEN now() + (p_lockout_minutes || ' minutes')::interval
                       ELSE locked_until
                   END
             WHERE id = p_user_id
            RETURNING failed_logins INTO v_failures;
            RETURN v_failures;
        END
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION auth_record_failure(UUID, INT, INT) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_record_failure(UUID, INT, INT) TO {APP_ROLE}")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION auth_record_success(p_user_id UUID, p_new_hash TEXT)
        RETURNS VOID
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            UPDATE users
               SET failed_logins = 0,
                   locked_until = NULL,
                   password_hash = COALESCE(p_new_hash, password_hash)
             WHERE id = p_user_id
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION auth_record_success(UUID, TEXT) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION auth_record_success(UUID, TEXT) TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS auth_record_success(UUID, TEXT)")
    op.execute("DROP FUNCTION IF EXISTS auth_record_failure(UUID, INT, INT)")
    op.execute("DROP FUNCTION IF EXISTS auth_lookup(TEXT)")
