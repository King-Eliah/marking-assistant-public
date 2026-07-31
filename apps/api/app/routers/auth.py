"""Authentication — frontend.md §A1, spec.md §3.

Every failure returns the same message and the same status. An API that says
"no such user" for one address and "wrong password" for another is a way to
enumerate who has an account at an institution, and that list is itself worth
having to an attacker.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from app.core import audit_writer
from app.core.config import get_settings
from app.core.db import get_sessionmaker, set_session_tenant
from app.core.deps import CurrentClaims
from app.core.keys import get_keypair
from app.core.security import (
    InvalidTokenError,
    Role,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.tenancy import User, UserStatus

router = APIRouter(prefix="/auth", tags=["auth"])

#: Failed attempts before an account is locked. spec.md §3 keeps the counter on
#: the user row rather than in memory, so a lockout survives a restart and
#: cannot be reset by hitting a different worker.
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 5

#: Verified even when no user matched, so the response time does not reveal
#: whether the address exists. argon2 is deliberately slow; skipping it on a
#: miss would make misses measurably faster than hits.
_DUMMY_HASH = hash_password("timing-equalisation-only")


class LoginRequest(BaseModel):
    """Login credentials.

    `email` is a plain string rather than `EmailStr` deliberately. Validating
    the format here would return 422 for a malformed address and 401 for a
    wrong one, which is a weak account-enumeration signal — and the lookup is
    an exact match anyway, so a malformed address simply fails to find anyone.
    Refusing an unusual but legitimate address would be the worse outcome.
    """

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)
    remember_me: bool = False


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class Identity(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: Role


def _rejected() -> HTTPException:
    """The single response for every authentication failure.

    Unknown address, wrong password, suspended account, locked account — all
    identical. frontend.md §A1 specifies the same wording in the UI for the
    same reason.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="That email and password don't match. Try again, or reset your password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, request: Request, response: Response) -> TokenPair:
    """Exchange an email and password for a token pair.

    The three `auth_*` calls are SECURITY DEFINER functions, which is how this
    reaches across tenants without the application ever holding a connection
    that can. See the migration for why the alternatives are worse.
    """
    settings = get_settings()
    keys = get_keypair()

    session = get_sessionmaker()()
    try:
        row = session.execute(
            text(
                "SELECT id, tenant_id, email, password_hash, role, status,"
                " failed_logins, locked_until FROM auth_lookup(:email)"
            ),
            {"email": body.email},
        ).one_or_none()

        if row is None:
            # Still pay for a verification, so a miss does not return
            # measurably faster than a wrong password.
            verify_password(body.password, _DUMMY_HASH)
            raise _rejected()

        now = datetime.now(UTC)
        if row.locked_until is not None and row.locked_until > now:
            raise _rejected()

        if not verify_password(body.password, row.password_hash):
            session.execute(
                text("SELECT auth_record_failure(:uid, :maximum, :minutes)"),
                {
                    "uid": row.id,
                    "maximum": MAX_FAILED_LOGINS,
                    "minutes": LOCKOUT_MINUTES,
                },
            )
            session.commit()

            set_session_tenant(session, row.tenant_id)
            audit_writer.append(
                session,
                tenant_id=row.tenant_id,
                actor_id=row.id,
                action="auth.login_failed",
                entity_type="user",
                entity_id=str(row.id),
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            session.commit()
            raise _rejected()

        if row.status != UserStatus.ACTIVE.value:
            raise _rejected()

        # Upgrade the stored hash if it predates the current cost parameters.
        # This is the only moment the plaintext is available to do it.
        rehashed = hash_password(body.password) if needs_rehash(row.password_hash) else None
        session.execute(
            text("SELECT auth_record_success(:uid, :new_hash)"),
            {"uid": row.id, "new_hash": rehashed},
        )

        set_session_tenant(session, row.tenant_id)
        audit_writer.append(
            session,
            tenant_id=row.tenant_id,
            actor_id=row.id,
            action="auth.login",
            entity_type="user",
            entity_id=str(row.id),
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        session.commit()

        role = Role(row.role)
        pair = TokenPair(
            access_token=create_token(
                user_id=row.id,
                tenant_id=row.tenant_id,
                role=role,
                token_type=TokenType.ACCESS,
                private_key=keys.private_pem,
            ),
            refresh_token=create_token(
                user_id=row.id,
                tenant_id=row.tenant_id,
                role=role,
                token_type=TokenType.REFRESH,
                private_key=keys.private_pem,
            ),
            expires_in=settings.jwt_access_ttl_seconds,
        )
    finally:
        session.close()

    # httpOnly so script cannot read it, which is what keeps an XSS bug short
    # of stealing a week-long session.
    response.set_cookie(
        "refresh_token",
        pair.refresh_token,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        max_age=settings.jwt_refresh_ttl_seconds if body.remember_me else None,
        path="/auth",
    )
    return pair


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest) -> TokenPair:
    """Exchange a refresh token for a new pair."""
    settings = get_settings()
    keys = get_keypair()

    try:
        claims = decode_token(body.refresh_token, keys.public_pem, expect=TokenType.REFRESH)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        ) from exc

    return TokenPair(
        access_token=create_token(
            user_id=claims.user_id,
            tenant_id=claims.tenant_id,
            role=claims.role,
            token_type=TokenType.ACCESS,
            private_key=keys.private_pem,
        ),
        refresh_token=create_token(
            user_id=claims.user_id,
            tenant_id=claims.tenant_id,
            role=claims.role,
            token_type=TokenType.REFRESH,
            private_key=keys.private_pem,
        ),
        expires_in=settings.jwt_access_ttl_seconds,
    )


@router.get("/me", response_model=Identity)
def me(claims: CurrentClaims) -> Identity:
    """Who the current token says you are.

    Read back from the database rather than echoed from the token, so a user
    suspended after their token was issued is reflected here.
    """
    session = get_sessionmaker()()
    try:
        set_session_tenant(session, claims.tenant_id)
        user = session.execute(select(User).where(User.id == claims.user_id)).scalar_one_or_none()
        # `==`, not `is`. The column is a plain String, so SQLAlchemy returns
        # the raw text; identity against a StrEnum member is always False even
        # when the values are equal, which would lock out every active user.
        if user is None or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
        return Identity(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            role=Role(user.role),
        )
    finally:
        session.close()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(response: Response) -> Response:
    """Clear the refresh cookie.

    Access tokens are not revoked here — they are short-lived by design, and a
    revocation list would be a lie without somewhere durable to keep it. The
    refresh token is the one worth taking away.
    """
    response.delete_cookie("refresh_token", path="/auth")
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=dict(response.headers))
