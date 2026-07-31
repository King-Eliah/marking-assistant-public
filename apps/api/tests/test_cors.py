"""Cross-origin access.

Missing CORS is a distinctive kind of bug: every server-side test passes,
`curl` works perfectly, and only a real browser fails — because only a browser
sends a preflight. The failure then surfaces in the client as a network error
rather than an HTTP status, so it is indistinguishable from the API being down.

That is exactly how it was found: sign-in reported "something went wrong"
while `curl` against the same endpoint returned 200.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)

CONSOLE = "http://localhost:5173"
CAPTURE = "http://localhost:5174"


def preflight(origin: str, path: str = "/auth/login", method: str = "POST"):
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )


def test_the_console_may_preflight_a_login() -> None:
    """The exact request a browser makes before POSTing credentials."""
    response = preflight(CONSOLE)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == CONSOLE


def test_the_capture_app_may_too() -> None:
    assert preflight(CAPTURE).status_code == 200


def test_credentials_are_allowed() -> None:
    """The refresh token is an httpOnly cookie, so the browser will not send it
    cross-origin without this."""
    assert preflight(CONSOLE).headers["access-control-allow-credentials"] == "true"


def test_the_authorization_header_is_allowed() -> None:
    """Every authenticated call carries a bearer token. Without this on the
    preflight, the browser drops the header and the request 401s."""
    allowed = preflight(CONSOLE).headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed
    assert "content-type" in allowed


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_the_methods_the_api_uses_are_allowed(method: str) -> None:
    allowed = preflight(CONSOLE, method=method).headers["access-control-allow-methods"]
    assert method in allowed


def test_an_unknown_origin_is_not_echoed_back() -> None:
    """The check that makes the allowlist meaningful.

    A permissive configuration reflects whatever Origin it is given, which lets
    any site make authenticated calls on behalf of a signed-in user.
    """
    response = preflight("https://evil.example.com")
    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"


def test_the_origin_is_never_a_wildcard() -> None:
    """A wildcard is incompatible with credentials — the browser refuses the
    combination — and would defeat the allowlist entirely."""
    assert preflight(CONSOLE).headers["access-control-allow-origin"] != "*"


def test_the_allowlist_is_configurable() -> None:
    """Deployment origins differ from development ones, and hardcoding them
    would mean a code change to deploy."""
    settings = get_settings()
    assert CONSOLE in settings.cors_origin_list
    assert len(settings.cors_origin_list) >= 1


def test_a_real_request_carries_the_origin_header() -> None:
    """A preflight passing is not sufficient — the actual response needs the
    header too, or the browser discards a perfectly good reply."""
    response = client.get("/healthz", headers={"Origin": CONSOLE})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == CONSOLE
