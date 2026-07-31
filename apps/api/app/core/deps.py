"""Request dependencies.

Every authenticated request resolves the same way: verify the token, take the
tenant from its claims, and bind the database session to that tenant before a
single statement runs. There is no path that reaches a query without a tenant,
because the session is created by this module and nowhere else.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_sessionmaker, reset_session_tenant, set_session_tenant
from app.core.keys import get_keypair
from app.core.scope import TenantScope
from app.core.security import InvalidTokenError, Role, TokenClaims, TokenType, decode_token


def get_claims(authorization: Annotated[str | None, Header()] = None) -> TokenClaims:
    """Verify the bearer token.

    Every failure returns the same 401 with the same body. Distinguishing
    "expired" from "bad signature" from "wrong algorithm" tells an attacker
    which of their guesses was closer.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized

    try:
        return decode_token(
            authorization.removeprefix("Bearer ").strip(),
            get_keypair().public_pem,
            expect=TokenType.ACCESS,
        )
    except InvalidTokenError as exc:
        raise unauthorized from exc


def get_scope(claims: Annotated[TokenClaims, Depends(get_claims)]) -> TenantScope:
    """The caller's tenant, taken from the token and never from the request."""
    return TenantScope(tenant_id=claims.tenant_id)


def get_session(
    claims: Annotated[TokenClaims, Depends(get_claims)],
) -> Iterator[Session]:
    """A session bound to the caller's tenant for the life of the request.

    The tenant is set before the caller can issue anything, and reset before
    the connection returns to the pool — otherwise the next borrower inherits
    this request's tenant and RLS faithfully applies the wrong scope.
    """
    session = get_sessionmaker()()
    try:
        set_session_tenant(session, claims.tenant_id)
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        try:
            reset_session_tenant(session)
            session.commit()
        finally:
            session.close()


def require_role(*allowed: Role) -> Callable[[TokenClaims], TokenClaims]:
    """Restrict a route to the given roles."""

    def guard(claims: Annotated[TokenClaims, Depends(get_claims)]) -> TokenClaims:
        if claims.role not in allowed:
            # 404 rather than 403, for the same reason as the tenant guard:
            # a 403 confirms the resource exists.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return claims

    return guard


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


CurrentClaims = Annotated[TokenClaims, Depends(get_claims)]
CurrentScope = Annotated[TenantScope, Depends(get_scope)]
DbSession = Annotated[Session, Depends(get_session)]


def actor_id(claims: CurrentClaims) -> uuid.UUID:
    return claims.user_id
