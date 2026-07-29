"""The service-layer guard, tested without a database.

Deliberately pure unit tests. This layer's whole purpose is to hold when the
database layer does not, so exercising it against a live RLS-protected
database would test the two layers together and prove neither independently.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.core.scope import NotFoundError, TenantScope, require_owned, require_same_tenant

ALPHA = uuid.uuid4()
BETA = uuid.uuid4()


@dataclass
class FakeCourse:
    tenant_id: uuid.UUID
    id: uuid.UUID


def test_owner_gets_their_entity() -> None:
    scope = TenantScope(ALPHA)
    course = FakeCourse(tenant_id=ALPHA, id=uuid.uuid4())
    assert require_owned(scope, course, "course", course.id) is course


def test_another_tenants_entity_is_not_found() -> None:
    """Not 'forbidden' — not found. The distinction is the whole point."""
    scope = TenantScope(ALPHA)
    course = FakeCourse(tenant_id=BETA, id=uuid.uuid4())
    with pytest.raises(NotFoundError):
        require_owned(scope, course, "course", course.id)


def test_missing_and_forbidden_are_indistinguishable() -> None:
    """A caller must not be able to tell an absent row from someone else's.

    If these produced different errors, the API would be an oracle for
    "does this id exist in some other institution?"
    """
    scope = TenantScope(ALPHA)
    other_id = uuid.uuid4()

    with pytest.raises(NotFoundError) as absent:
        require_owned(scope, None, "course", other_id)
    with pytest.raises(NotFoundError) as forbidden:
        require_owned(scope, FakeCourse(tenant_id=BETA, id=other_id), "course", other_id)

    assert str(absent.value) == str(forbidden.value)
    assert type(absent.value) is type(forbidden.value)


def test_writes_for_another_tenant_are_rejected() -> None:
    scope = TenantScope(ALPHA)
    with pytest.raises(NotFoundError):
        require_same_tenant(scope, BETA, "course")


def test_writes_for_the_callers_own_tenant_pass() -> None:
    scope = TenantScope(ALPHA)
    require_same_tenant(scope, ALPHA, "course")


def test_scope_is_immutable() -> None:
    """A scope reassignable mid-request is one a bug can reassign."""
    scope = TenantScope(ALPHA)
    with pytest.raises(AttributeError):
        scope.tenant_id = BETA  # type: ignore[misc]


def test_the_guard_does_not_consult_the_database() -> None:
    """This layer must hold when the database layer does not.

    `require_owned` is a pure comparison over an object already in memory. If
    it ever needs a session, the two layers have become one and the second has
    stopped being independent.
    """
    scope = TenantScope(ALPHA)
    course = FakeCourse(tenant_id=BETA, id=uuid.uuid4())

    # No session, no engine, no connection — and it still rejects.
    with pytest.raises(NotFoundError):
        require_owned(scope, course, "course", course.id)
