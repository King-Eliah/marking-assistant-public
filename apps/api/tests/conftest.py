"""Shared fixtures.

Integration tests need a real PostgreSQL: RLS, triggers, and grants cannot be
exercised against SQLite or a mock, and a mock of the thing under test proves
nothing. They are marked `integration` and skipped when no database is
reachable, so `pytest` stays useful without Docker running.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

#: The migration owner. Superuser in dev, so it bypasses RLS.
OWNER_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://marking:marking@localhost:5433/marking",
)

#: The unprivileged role the application uses. RLS actually applies to this one.
APP_URL = OWNER_URL.replace("marking:marking@", "marking_app:marking_app@")


def _reachable(url: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect():
            return True
    except Exception:
        return False
    finally:
        # Without this the probe connection is garbage-collected while open and
        # surfaces as a ResourceWarning on whichever test happens to run next.
        engine.dispose()


@pytest.fixture(scope="session")
def owner_engine() -> Iterator[Engine]:
    """Connects as the migration owner. Used for seeding only."""
    if not _reachable(OWNER_URL):
        pytest.skip("no database reachable — run `make dev`")
    engine = create_engine(OWNER_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def app_engine(owner_engine: Engine) -> Iterator[Engine]:
    """Connects as `marking_app`.

    Every isolation assertion must run through this engine. Asserting against
    `owner_engine` would pass regardless, because a superuser bypasses RLS —
    that is exactly the bug this suite exists to catch.
    """
    if not _reachable(APP_URL):
        pytest.skip("marking_app role unavailable — run `make migrate`")
    engine = create_engine(APP_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def two_tenants(owner_engine: Engine) -> Iterator[tuple[uuid.UUID, uuid.UUID]]:
    """Two freshly created tenants.

    Ids are unique per test rather than shared, so tests neither collide nor
    depend on cleaning up `audit_log` — which is append-only by design and
    cannot be emptied.
    """
    alpha, beta = uuid.uuid4(), uuid.uuid4()
    with owner_engine.begin() as conn:
        for tid, name in ((alpha, "Alpha"), (beta, "Beta")):
            conn.execute(
                sa.text(
                    "INSERT INTO tenants (id, name, data_region, retention_days,"
                    " ai_monthly_cap_usd) VALUES (:id, :name, 'eu', 180, 100)"
                ),
                {"id": tid, "name": name},
            )
    yield alpha, beta
    with owner_engine.begin() as conn:
        conn.execute(
            sa.text("DELETE FROM courses WHERE tenant_id = ANY(:ids)"),
            {"ids": [alpha, beta]},
        )
