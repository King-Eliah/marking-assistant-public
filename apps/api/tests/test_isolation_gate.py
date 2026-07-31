"""The stage 1 acceptance gate, end to end over HTTP.

spec.md §12, M0: *"a cross-tenant access attempt returns 404 and appears in
the audit log."*

Every other isolation test so far has exercised one layer in isolation. This
one goes through the whole stack — token, dependency, RLS-bound session,
service guard, exception handler, audit chain — because that is what the
milestone actually claims.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.audit import verify_chain
from app.core.audit_writer import read_chain
from app.core.db import get_sessionmaker, set_session_tenant
from app.core.keys import get_keypair
from app.core.security import Role, TokenType, create_token
from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app, raise_server_exceptions=False)


def token_for(tenant_id: uuid.UUID, user_id: uuid.UUID, role: Role = Role.LECTURER) -> str:
    return create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        token_type=TokenType.ACCESS,
        private_key=get_keypair().private_pem,
    )


def auth(tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(tenant_id, user_id)}"}


@pytest.fixture
def two_institutions(
    owner_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Alpha and Beta, each with a lecturer, and one course owned by Beta."""
    alpha, beta = two_tenants
    alpha_user, beta_user = uuid.uuid4(), uuid.uuid4()
    beta_course = uuid.uuid4()

    with owner_engine.begin() as conn:
        for uid, tid, email in (
            (alpha_user, alpha, "a@alpha.edu"),
            (beta_user, beta, "b@beta.edu"),
        ):
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, tenant_id, email, password_hash, role, status,"
                    " failed_logins) VALUES (:id, :tid, :email, 'x', 'LECTURER', 'ACTIVE', 0)"
                ),
                {"id": uid, "tid": tid, "email": email},
            )
        conn.execute(
            sa.text(
                "INSERT INTO courses (id, tenant_id, code, title, academic_year)"
                " VALUES (:id, :tid, 'BETA101', 'Beta course', '2026')"
            ),
            {"id": beta_course, "tid": beta},
        )

    yield alpha, beta, alpha_user, beta_user, beta_course

    # The users are deliberately *not* deleted. `audit_log.actor_id` is
    # ON DELETE RESTRICT, so anyone who appears in the audit trail cannot be
    # removed — otherwise a denial could be erased by deleting the account that
    # caused it, and the chain would reference an actor that no longer exists.
    # Ids are unique per test, so leaving the rows costs nothing.


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------


def test_the_owner_can_read_their_own_course(two_institutions) -> None:
    _, beta, _, beta_user, beta_course = two_institutions
    response = client.get(f"/courses/{beta_course}", headers=auth(beta, beta_user))
    assert response.status_code == 200
    assert response.json()["code"] == "BETA101"


def test_cross_tenant_read_returns_404(two_institutions) -> None:
    """The first half of the M0 gate."""
    alpha, _, alpha_user, _, beta_course = two_institutions
    response = client.get(f"/courses/{beta_course}", headers=auth(alpha, alpha_user))
    assert response.status_code == 404


def test_cross_tenant_read_appears_in_the_audit_log(two_institutions) -> None:
    """The second half. A silent denial is not defensible after the fact."""
    alpha, _, alpha_user, _, beta_course = two_institutions
    client.get(f"/courses/{beta_course}", headers=auth(alpha, alpha_user))

    session = get_sessionmaker()()
    try:
        set_session_tenant(session, alpha)
        chain = read_chain(session, alpha)
    finally:
        session.close()

    denials = [r for r in chain if r["action"] == "course.access_denied"]
    assert len(denials) == 1
    assert denials[0]["entity_id"] == str(beta_course)
    assert denials[0]["actor_id"] == alpha_user


def test_the_audit_chain_still_verifies_after_the_denial(two_institutions) -> None:
    """Writing the denial must not corrupt the chain it is written into."""
    alpha, _, alpha_user, _, beta_course = two_institutions
    client.get(f"/courses/{beta_course}", headers=auth(alpha, alpha_user))

    session = get_sessionmaker()()
    try:
        set_session_tenant(session, alpha)
        verify_chain(read_chain(session, alpha))
    finally:
        session.close()


# ---------------------------------------------------------------------------
# the ways round it
# ---------------------------------------------------------------------------


def test_a_missing_course_is_indistinguishable_from_another_tenants(
    two_institutions,
) -> None:
    """If these differed, the API would answer "does this id exist somewhere?"."""
    alpha, _, alpha_user, _, beta_course = two_institutions

    forbidden = client.get(f"/courses/{beta_course}", headers=auth(alpha, alpha_user))
    absent = client.get(f"/courses/{uuid.uuid4()}", headers=auth(alpha, alpha_user))

    assert forbidden.status_code == absent.status_code == 404
    assert forbidden.json() == absent.json()


def test_the_404_body_leaks_nothing(two_institutions) -> None:
    alpha, _, alpha_user, _, beta_course = two_institutions
    body = client.get(f"/courses/{beta_course}", headers=auth(alpha, alpha_user)).text
    assert str(beta_course) not in body
    assert "course" not in body.lower()


def test_listing_never_leaks_another_tenant(two_institutions) -> None:
    """`list_courses` has no tenant filter — RLS supplies it. This is what
    catches a dropped policy."""
    alpha, beta, alpha_user, beta_user, _ = two_institutions

    assert client.get("/courses", headers=auth(alpha, alpha_user)).json() == []
    beta_codes = [c["code"] for c in client.get("/courses", headers=auth(beta, beta_user)).json()]
    assert beta_codes == ["BETA101"]


def test_no_token_is_rejected(two_institutions) -> None:
    _, _, _, _, beta_course = two_institutions
    assert client.get(f"/courses/{beta_course}").status_code == 401


def test_a_forged_tenant_claim_does_not_help(two_institutions) -> None:
    """Editing `tid` in a token invalidates the signature. The tenant cannot be
    chosen by the caller — that is the point of it living in the claims."""
    alpha, beta, alpha_user, _, beta_course = two_institutions
    header, payload, signature = token_for(alpha, alpha_user).split(".")

    import base64
    import json

    decoded = json.loads(base64.urlsafe_b64decode(payload + "=="))
    decoded["tid"] = str(beta)  # claim to be the other institution
    tampered = base64.urlsafe_b64encode(json.dumps(decoded).encode()).rstrip(b"=").decode()

    response = client.get(
        f"/courses/{beta_course}",
        headers={"Authorization": f"Bearer {header}.{tampered}.{signature}"},
    )
    assert response.status_code == 401
