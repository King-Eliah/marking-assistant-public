"""Scaffold test: the service starts and reports liveness."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_returns_200() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200


def test_healthz_reports_pinned_pipeline_version() -> None:
    """I5 depends on pipeline_version being explicit and pinned, never inferred."""
    body = response_body()
    assert body["status"] == "ok"
    assert body["pipeline_version"] == "2.3.1"


def response_body() -> dict[str, str]:
    return client.get("/healthz").json()
