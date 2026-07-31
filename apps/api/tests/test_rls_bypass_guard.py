"""The application must refuse to start as a role that ignores RLS.

This exists because it happened. Pointing `DATABASE_URL` at the migration
owner — a superuser — left every policy in place and inert. Every query
succeeded, every unit test passed, and the only symptom was a listing endpoint
quietly returning another institution's rows.

A configuration that disables tenant isolation must fail loudly at startup,
not serve traffic.
"""

from __future__ import annotations

from contextlib import suppress

import pytest
from sqlalchemy import Engine, create_engine, text

from app.core.db import RlsBypassError, assert_rls_applies, get_engine
from app.core.scope import TenantScope
from tests.conftest import APP_URL, OWNER_URL

pytestmark = pytest.mark.integration


def _reset_engine() -> None:
    """Dispose before clearing the cache.

    `cache_clear()` alone orphans the engine with its pool still open. The
    connection is then garbage-collected mid-run and, with warnings as errors,
    fails whichever unrelated test happens to be executing.
    """
    # An unbuildable engine has nothing to dispose; clearing the cache is the
    # part that must happen either way.
    with suppress(Exception):
        get_engine().dispose()
    get_engine.cache_clear()


@pytest.fixture(autouse=True)
def _clean_engine() -> None:
    yield
    _reset_engine()


def test_the_app_role_passes_the_guard(app_engine: Engine) -> None:
    """Takes `app_engine` purely so it skips rather than fails when no database
    is reachable — consistent with every other integration test. Without it a
    stopped Docker looks like a broken guard."""
    del app_engine
    _reset_engine()
    assert_rls_applies()


def test_connecting_as_the_owner_is_refused(
    owner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact misconfiguration that leaked, now caught before serving."""
    del owner_engine
    from app.core import config, db

    _reset_engine()
    config.get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", OWNER_URL)

    try:
        with pytest.raises(RlsBypassError, match="SUPERUSER|BYPASSRLS"):
            db.assert_rls_applies()
    finally:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        _reset_engine()
        config.get_settings.cache_clear()


def test_the_two_urls_are_actually_different_roles(owner_engine: Engine) -> None:
    """Guards against a future edit collapsing them back into one."""
    del owner_engine
    assert "marking_app:" in APP_URL
    assert "marking_app:" not in OWNER_URL

    for url, expect_bypass in ((OWNER_URL, True), (APP_URL, False)):
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT rolsuper OR rolbypassrls AS bypasses "
                        "FROM pg_roles WHERE rolname = current_user"
                    )
                ).one()
            assert row.bypasses is expect_bypass
        finally:
            engine.dispose()


def test_an_object_without_a_tenant_is_never_owned() -> None:
    """A type that forgot `tenant_id` must be denied, not silently accepted."""
    import uuid

    scope = TenantScope(uuid.uuid4())

    class Forgot:
        pass

    assert not scope.owns(Forgot())
    assert not scope.owns(object())
    assert not scope.owns(None)
