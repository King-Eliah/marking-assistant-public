"""Booklet issue and download over HTTP.

The interesting properties are that booklets are anonymous, that every one is
distinguishable from every other, and that a download reproduces exactly what
was issued rather than something that merely resembles it.
"""

from __future__ import annotations

import io
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import Engine

from app.core.keys import get_keypair
from app.core.security import Role, TokenType, create_token
from app.engines.booklet.layout import LAYOUT_VERSION
from app.engines.booklet.payload import decode
from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app, raise_server_exceptions=False)


def auth(tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, str]:
    token = create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=Role.LECTURER,
        token_type=TokenType.ACCESS,
        private_key=get_keypair().private_pem,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def exam(
    owner_engine: Engine, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """An exam with three questions, plus a lecturer in another institution."""
    alpha, beta = two_tenants
    user, other_user = uuid.uuid4(), uuid.uuid4()
    course_id, exam_id = uuid.uuid4(), uuid.uuid4()

    with owner_engine.begin() as conn:
        for uid, tid, email in ((user, alpha, "a@alpha.edu"), (other_user, beta, "b@beta.edu")):
            conn.execute(
                sa.text(
                    "INSERT INTO users (id, tenant_id, email, password_hash, role, status,"
                    " failed_logins) VALUES (:id, :t, :e, 'x', 'LECTURER', 'ACTIVE', 0)"
                ),
                {"id": uid, "t": tid, "e": email},
            )
        conn.execute(
            sa.text(
                "INSERT INTO courses (id, tenant_id, code, title, academic_year)"
                " VALUES (:id, :t, 'CSM355', 'OS', '2026')"
            ),
            {"id": course_id, "t": alpha},
        )
        conn.execute(
            sa.text(
                "INSERT INTO exams (id, tenant_id, course_id, code, title, total_marks,"
                " status, anonymous_marking) VALUES (:id, :t, :c, 'CSM 355',"
                " 'Operating Systems', 40, 'DRAFT', true)"
            ),
            {"id": exam_id, "t": alpha, "c": course_id},
        )
        for i, (number, marks) in enumerate([("1(a)", 6), ("1(b)", 4), ("2", 10)], start=1):
            conn.execute(
                sa.text(
                    "INSERT INTO questions (id, tenant_id, exam_id, number, prompt_text,"
                    " max_marks, answer_type, position, answer_height_mm)"
                    " VALUES (:id, :t, :e, :n, '', :m, 'PROSE', :p, 60)"
                ),
                {"id": uuid.uuid4(), "t": alpha, "e": exam_id, "n": number, "m": marks, "p": i},
            )

    yield alpha, user, exam_id, other_user

    with owner_engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM booklets WHERE exam_id = :e"), {"e": exam_id})
        conn.execute(sa.text("DELETE FROM questions WHERE exam_id = :e"), {"e": exam_id})
        conn.execute(sa.text("DELETE FROM exams WHERE id = :e"), {"e": exam_id})
        conn.execute(sa.text("DELETE FROM courses WHERE id = :c"), {"c": course_id})


# --- issuing ---------------------------------------------------------------


def test_issuing_creates_the_requested_number(exam) -> None:
    tenant, user, exam_id, _ = exam
    response = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 5}, headers=auth(tenant, user)
    )
    assert response.status_code == 201
    assert len(response.json()) == 5


def test_every_booklet_gets_a_distinct_identity(exam) -> None:
    """Two booklets sharing a QR would make two students' scripts
    indistinguishable after collection."""
    tenant, user, exam_id, _ = exam
    client.post(f"/exams/{exam_id}/booklets", json={"count": 10}, headers=auth(tenant, user))

    listed = client.get(f"/exams/{exam_id}/booklets", headers=auth(tenant, user)).json()
    assert len({b["id"] for b in listed}) == 10


def test_the_issued_payload_decodes_and_names_its_exam(exam) -> None:
    tenant, user, exam_id, _ = exam
    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    ).json()[0]

    pdf = client.get(f"/booklets/{created['id']}.pdf", headers=auth(tenant, user))
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"


def test_the_layout_version_is_recorded(exam) -> None:
    """Without it, a later geometry change would silently reprint a page whose
    fiducials sit elsewhere."""
    tenant, user, exam_id, _ = exam
    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    ).json()[0]
    assert created["layout_version"] == LAYOUT_VERSION


def test_an_exam_with_no_questions_cannot_issue_booklets(owner_engine: Engine, exam) -> None:
    """A booklet with nowhere to write is worse than no booklet: it would be
    printed, handed out, and discovered in the hall."""
    tenant, user, exam_id, _ = exam
    with owner_engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM questions WHERE exam_id = :e"), {"e": exam_id})

    response = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    )
    assert response.status_code == 409
    assert "no questions" in response.json()["detail"]


@pytest.mark.parametrize("count", [0, -1, 501])
def test_absurd_counts_are_refused(exam, count: int) -> None:
    tenant, user, exam_id, _ = exam
    response = client.post(
        f"/exams/{exam_id}/booklets", json={"count": count}, headers=auth(tenant, user)
    )
    assert response.status_code == 422


# --- the PDF ---------------------------------------------------------------


def test_downloading_reproduces_the_issued_booklet_exactly(exam) -> None:
    """Deterministic generation is what makes storing the PDF unnecessary.

    If two downloads differed, the stored row would no longer describe the
    paper the student actually wrote on.
    """
    tenant, user, exam_id, _ = exam
    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    ).json()[0]

    first = client.get(f"/booklets/{created['id']}.pdf", headers=auth(tenant, user)).content
    second = client.get(f"/booklets/{created['id']}.pdf", headers=auth(tenant, user)).content
    assert first == second


def test_two_booklets_produce_different_pdfs(exam) -> None:
    tenant, user, exam_id, _ = exam
    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 2}, headers=auth(tenant, user)
    ).json()

    pdfs = [
        client.get(f"/booklets/{b['id']}.pdf", headers=auth(tenant, user)).content for b in created
    ]
    assert pdfs[0] != pdfs[1]


def test_the_pdf_carries_no_student_identity(exam) -> None:
    tenant, user, exam_id, _ = exam
    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    ).json()[0]

    pdf = client.get(f"/booklets/{created['id']}.pdf", headers=auth(tenant, user)).content
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)

    assert "not write your name" in text
    for banned in ("student", "candidate", "index number"):
        assert banned not in text.lower()


def test_the_printed_marks_match_the_stored_questions(exam) -> None:
    tenant, user, exam_id, _ = exam
    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    ).json()[0]

    pdf = client.get(f"/booklets/{created['id']}.pdf", headers=auth(tenant, user)).content
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)

    assert "QUESTION 1(a)" in text
    assert "6 marks" in text
    assert "10 marks" in text
    assert "E+" not in text  # Decimal("10").normalize() renders as 1E+1


# --- isolation -------------------------------------------------------------


def test_another_institution_cannot_issue_booklets_for_this_exam(exam) -> None:
    tenant, user, exam_id, other_user = exam
    del tenant, user

    other_tenant = uuid.uuid4()
    response = client.post(
        f"/exams/{exam_id}/booklets",
        json={"count": 1},
        headers=auth(other_tenant, other_user),
    )
    assert response.status_code == 404


def test_another_institution_cannot_download_a_booklet(
    exam, two_tenants: tuple[uuid.UUID, uuid.UUID]
) -> None:
    tenant, user, exam_id, other_user = exam
    _, beta = two_tenants

    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    ).json()[0]

    response = client.get(f"/booklets/{created['id']}.pdf", headers=auth(beta, other_user))
    assert response.status_code == 404


def test_issuing_is_audited(exam) -> None:
    """Booklets are physical objects handed to students; who issued how many,
    and when, has to be answerable afterwards."""
    from app.core.audit_writer import read_chain
    from app.core.db import get_sessionmaker, set_session_tenant

    tenant, user, exam_id, _ = exam
    client.post(f"/exams/{exam_id}/booklets", json={"count": 3}, headers=auth(tenant, user))

    session = get_sessionmaker()()
    try:
        set_session_tenant(session, tenant)
        chain = read_chain(session, tenant)
    finally:
        session.close()

    issues = [r for r in chain if r["action"] == "booklets.issue"]
    assert len(issues) == 1
    assert issues[0]["after"]["count"] == 3
    assert issues[0]["actor_id"] == user


def test_an_unknown_booklet_is_not_found(exam) -> None:
    tenant, user, _, _ = exam
    response = client.get(f"/booklets/{uuid.uuid4()}.pdf", headers=auth(tenant, user))
    assert response.status_code == 404


def test_the_qr_payload_round_trips_from_the_stored_row(owner_engine: Engine, exam) -> None:
    """What is stored must be exactly what a scanner will read back."""
    tenant, user, exam_id, _ = exam
    created = client.post(
        f"/exams/{exam_id}/booklets", json={"count": 1}, headers=auth(tenant, user)
    ).json()[0]

    with owner_engine.connect() as conn:
        raw = conn.execute(
            sa.text("SELECT qr_payload FROM booklets WHERE id = :i"), {"i": created["id"]}
        ).scalar_one()

    payload = decode(raw)
    assert str(payload.booklet_id) == created["id"]
    assert str(payload.exam_id) == str(exam_id)
    assert payload.page_no == 1
