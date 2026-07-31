"""Login, over HTTP.

The property under test is not "correct credentials work" — it is that every
kind of failure is indistinguishable. An API answering differently for an
unknown address than for a wrong password hands over a list of who has an
account at an institution, and that list is worth having on its own.
"""

from __future__ import annotations

import time
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.security import hash_password
from app.main import app
from app.routers.auth import MAX_FAILED_LOGINS

pytestmark = pytest.mark.integration

client = TestClient(app, raise_server_exceptions=False)

PASSWORD = "correct horse battery staple"


@pytest.fixture
def account(owner_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]):
    """One active lecturer, plus a suspended one in the same institution."""
    tenant, _ = two_tenants
    active, suspended = uuid.uuid4(), uuid.uuid4()
    email = f"lecturer-{active.hex[:8]}@knust.edu.gh"
    suspended_email = f"suspended-{suspended.hex[:8]}@knust.edu.gh"
    digest = hash_password(PASSWORD)

    with owner_engine.begin() as conn:
        for uid, mail, status in (
            (active, email, "ACTIVE"),
            (suspended, suspended_email, "SUSPENDED"),
        ):
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, tenant_id, email, password_hash, role,"
                    " status, failed_logins) VALUES (:id, :t, :e, :h, 'LECTURER',"
                    " :s, 0)"
                ),
                {"id": uid, "t": tenant, "e": mail, "h": digest, "s": status},
            )

    yield {
        "tenant": tenant,
        "user_id": active,
        "email": email,
        "suspended_email": suspended_email,
    }

    with owner_engine.begin() as conn:
        conn.execute(
            sa.text("UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = :i"),
            {"i": active},
        )


def login(email: str, password: str = PASSWORD, **extra: object):
    return client.post("/auth/login", json={"email": email, "password": password, **extra})


# --- the happy path --------------------------------------------------------


def test_correct_credentials_return_a_token_pair(account) -> None:
    response = login(account["email"])
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_the_access_token_works_against_a_protected_route(account) -> None:
    token = login(account["email"]).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == account["email"]
    assert me.json()["tenant_id"] == str(account["tenant"])


def test_the_refresh_token_is_httponly(account) -> None:
    """Script must not be able to read it. That is what stops an XSS bug from
    becoming a week-long stolen session."""
    response = login(account["email"], remember_me=True)
    cookie = response.headers.get("set-cookie", "")
    assert "refresh_token=" in cookie
    assert "HttpOnly" in cookie


def test_a_refresh_token_buys_a_new_access_token(account) -> None:
    refresh = login(account["email"]).json()["refresh_token"]
    response = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_an_access_token_cannot_be_used_to_refresh(account) -> None:
    """Access tokens live 15 minutes, refresh tokens a week. Accepting one for
    the other collapses that distinction."""
    access = login(account["email"]).json()["access_token"]
    assert client.post("/auth/refresh", json={"refresh_token": access}).status_code == 401


# --- every failure looks the same ------------------------------------------


def test_an_unknown_address_and_a_wrong_password_are_identical(account) -> None:
    """The enumeration defence, stated directly."""
    unknown = login("nobody-at-all@knust.edu.gh")
    wrong = login(account["email"], "not the password")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_a_suspended_account_is_also_indistinguishable(account) -> None:
    """Otherwise "your account is suspended" confirms the account exists."""
    suspended = login(account["suspended_email"])
    unknown = login("nobody-at-all@knust.edu.gh")

    assert suspended.status_code == unknown.status_code == 401
    assert suspended.json() == unknown.json()


def test_the_message_matches_the_one_the_ui_shows(account) -> None:
    """frontend.md §A1 specifies the wording. The API and the sign-in screen
    saying different things would be a second, subtler oracle."""
    detail = login(account["email"], "wrong").json()["detail"]
    assert "don't match" in detail
    assert "reset your password" in detail


def test_an_unknown_address_still_costs_a_password_verification(account) -> None:
    """argon2 is deliberately slow. Skipping it when no user matched would make
    a miss measurably faster than a hit, which is a timing oracle.

    Generous bounds — this asserts the dummy verify happens at all, not a
    precise timing, because CI machines are noisy.
    """
    start = time.perf_counter()
    login("definitely-nobody@knust.edu.gh")
    miss = time.perf_counter() - start

    start = time.perf_counter()
    login(account["email"], "wrong password")
    hit = time.perf_counter() - start

    assert miss > hit * 0.25, "a miss returned suspiciously faster than a wrong password"


# --- lockout ---------------------------------------------------------------


def test_repeated_failures_lock_the_account(account, owner_engine: Engine) -> None:
    for _ in range(MAX_FAILED_LOGINS):
        login(account["email"], "wrong")

    # even the correct password is refused once locked
    assert login(account["email"]).status_code == 401

    with owner_engine.connect() as conn:
        locked_until = conn.execute(
            sa.text("SELECT locked_until FROM users WHERE id = :i"), {"i": account["user_id"]}
        ).scalar_one()
    assert locked_until is not None


def test_the_lockout_survives_a_restart(account, owner_engine: Engine) -> None:
    """The counter lives on the user row, not in memory, so a lockout cannot be
    cleared by hitting a different worker."""
    for _ in range(MAX_FAILED_LOGINS):
        login(account["email"], "wrong")

    with owner_engine.connect() as conn:
        failures = conn.execute(
            sa.text("SELECT failed_logins FROM users WHERE id = :i"), {"i": account["user_id"]}
        ).scalar_one()
    assert failures >= MAX_FAILED_LOGINS


def test_a_successful_login_clears_the_counter(account, owner_engine: Engine) -> None:
    for _ in range(MAX_FAILED_LOGINS - 1):
        login(account["email"], "wrong")
    assert login(account["email"]).status_code == 200

    with owner_engine.connect() as conn:
        failures = conn.execute(
            sa.text("SELECT failed_logins FROM users WHERE id = :i"), {"i": account["user_id"]}
        ).scalar_one()
    assert failures == 0


# --- auditing --------------------------------------------------------------


def test_a_successful_login_is_audited(account) -> None:
    from app.core.audit_writer import read_chain
    from app.core.db import get_sessionmaker, set_session_tenant

    login(account["email"])

    session = get_sessionmaker()()
    try:
        set_session_tenant(session, account["tenant"])
        chain = read_chain(session, account["tenant"])
    finally:
        session.close()

    logins = [r for r in chain if r["action"] == "auth.login"]
    assert logins
    assert logins[-1]["actor_id"] == account["user_id"]


def test_a_failed_login_is_audited(account) -> None:
    """A burst of failures against one account is what a brute-force attempt
    looks like. It has to be visible afterwards."""
    from app.core.audit_writer import read_chain
    from app.core.db import get_sessionmaker, set_session_tenant

    login(account["email"], "wrong")

    session = get_sessionmaker()()
    try:
        set_session_tenant(session, account["tenant"])
        chain = read_chain(session, account["tenant"])
    finally:
        session.close()

    assert any(r["action"] == "auth.login_failed" for r in chain)


# --- input handling --------------------------------------------------------


def test_a_malformed_address_is_rejected_like_a_wrong_one(account) -> None:
    """Not a 422. A different status for a malformed address is a weak
    enumeration signal, and the lookup fails harmlessly anyway."""
    assert login("not-an-email-at-all").status_code == 401


def test_an_empty_password_is_refused(account) -> None:
    assert login(account["email"], "").status_code == 422


def test_a_very_long_password_does_not_reach_the_hasher(account) -> None:
    """Bounded before argon2 sees it, so a megabyte of input cannot be used to
    burn CPU."""
    assert login(account["email"], "x" * 5000).status_code == 422
