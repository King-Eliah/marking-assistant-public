"""The service-layer tenant guard — isolation layer two of two for I7.

This layer exists precisely because the other one might fail. RLS is enforced
by Postgres and this is enforced in Python; a bug in either alone must not leak
data. That means this module may never assume RLS filtered anything, and must
never be implemented in terms of it.

The earlier discovery that RLS silently protected nothing — because the
connecting role was a superuser — is the argument for this layer in one
sentence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, TypeVar


class TenantOwned(Protocol):
    """Anything carrying a tenant. Every model inheriting `TenantScoped` fits.

    Documentation rather than a bound: a SQLAlchemy model declares
    `tenant_id: Mapped[uuid.UUID]`, and mypy compares protocols against that
    declared type rather than what the descriptor yields on an instance, so
    no mapped class ever matches structurally. Binding `T` to this pushed the
    TypeVar to resolve against `None` and rejected every real call.
    """

    @property
    def tenant_id(self) -> uuid.UUID: ...


#: Unbound on purpose — see `TenantOwned`. The ownership check reads
#: `tenant_id` defensively below, so a type lacking it is rejected rather than
#: silently treated as owned.
T = TypeVar("T")


class NotFoundError(Exception):
    """The resource does not exist, or does not belong to the caller.

    Deliberately one exception for both. Distinguishing them is what turns a
    permission check into an existence oracle: a 403 on someone else's course
    confirms that course exists. spec.md §7 requires 404.
    """

    def __init__(self, entity_type: str, entity_id: uuid.UUID | str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} {entity_id} not found")


@dataclass(frozen=True, slots=True)
class TenantScope:
    """The caller's tenant, resolved from their token.

    Frozen because a scope that can be reassigned mid-request is a scope that
    can be reassigned by a bug.
    """

    tenant_id: uuid.UUID

    def owns(self, entity: object) -> bool:
        """True only when `entity` carries this exact tenant.

        A missing `tenant_id` is *not* ownership. Defaulting to a sentinel
        rather than `self.tenant_id` means a type that forgot the column is
        denied instead of silently passing every check.
        """
        return getattr(entity, "tenant_id", None) == self.tenant_id


def require_owned(
    scope: TenantScope, entity: T | None, entity_type: str, entity_id: uuid.UUID | str
) -> T:
    """Return the entity, or raise `NotFoundError`.

    Handles both cases identically on purpose:

    - the row does not exist
    - the row exists and belongs to another tenant

    A caller cannot tell which, so the API cannot become a way to enumerate
    other institutions' data.
    """
    if entity is None or not scope.owns(entity):
        raise NotFoundError(entity_type, entity_id)
    return entity


def require_same_tenant(scope: TenantScope, tenant_id: uuid.UUID, entity_type: str) -> None:
    """Guard a write before it reaches the database.

    RLS `WITH CHECK` would also reject this, but relying on that alone means
    the error surfaces as a database exception rather than a clear rejection,
    and it would stop being caught at all if a policy were ever dropped.
    """
    if tenant_id != scope.tenant_id:
        raise NotFoundError(entity_type, tenant_id)
