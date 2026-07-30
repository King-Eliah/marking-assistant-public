"""Password hashing and token issuance.

argon2id for passwords and RS256 for tokens, both per docs/spec.md §3 and
Appendix A.

RS256 rather than HS256 is a deliberate choice with a security consequence:
the workers and any future service can verify a token with the public key
alone, so the signing key lives in exactly one place. It also means this
module must reject the algorithm-confusion attack explicitly — see
`decode_token`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

ALGORITHM: Final[str] = "RS256"

#: Only RS256 is ever accepted on decode. Passing a list of one is not
#: redundant: PyJWT will honour whatever `alg` the *token header* claims if
#: given the chance, which is how HS256 confusion attacks work.
ACCEPTED_ALGORITHMS: Final[list[str]] = [ALGORITHM]

#: argon2id at RFC 9106's "second recommended" profile. Deliberately explicit
#: rather than relying on library defaults, which change between releases and
#: would silently alter every new hash.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class Role(StrEnum):
    """MVP subset of spec.md §5.3."""

    ADMIN = "ADMIN"
    LECTURER = "LECTURER"


class InvalidTokenError(Exception):
    """One error for every rejection reason.

    Expired, wrong signature, wrong algorithm, wrong type, malformed — all
    surface identically. A caller that can distinguish them learns something
    about the key material.
    """


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """What a verified token asserts."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: Role
    token_type: TokenType


def hash_password(password: str) -> str:
    """Hash with argon2id. Every call returns a different string.

    The salt is generated per call and encoded into the output, so two users
    with the same password get different hashes and a stolen table cannot be
    attacked with one precomputed set.
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time-ish verification. Returns False rather than raising.

    A malformed stored hash returns False too: it means the row is corrupt,
    which is not a reason to let the caller in.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when a stored hash predates the current cost parameters.

    Call after a successful verify; if true, rehash with the new parameters
    while the plaintext is briefly in hand.
    """
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def _now() -> datetime:
    return datetime.now(UTC)


def create_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: Role,
    token_type: TokenType,
    private_key: str,
    issued_at: datetime | None = None,
) -> str:
    """Sign a token. TTLs come from Appendix A, never from the caller."""
    settings = get_settings()
    ttl = (
        settings.jwt_access_ttl_seconds
        if token_type is TokenType.ACCESS
        else settings.jwt_refresh_ttl_seconds
    )
    now = issued_at or _now()

    payload: dict[str, Any] = {
        "sub": str(user_id),
        # tenant travels in the token so no request can be served without one.
        # The RLS session variable is set from this and nothing else (I7).
        "tid": str(tenant_id),
        "role": role.value,
        "typ": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, private_key, algorithm=ALGORITHM)


def decode_token(token: str, public_key: str, *, expect: TokenType | None = None) -> TokenClaims:
    """Verify and return the claims, or raise `InvalidTokenError`.

    `algorithms` is pinned to RS256. Without that pin an attacker can re-sign a
    token as HS256 using the *public* key as the HMAC secret — the public key
    is public, so the forgery verifies. That is the classic JWT algorithm
    confusion attack and the pin is the whole defence.
    """
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=ACCEPTED_ALGORITHMS,
            options={"require": ["exp", "iat", "sub", "tid", "role", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    try:
        claims = TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tid"]),
            role=Role(payload["role"]),
            token_type=TokenType(payload["typ"]),
        )
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("malformed claims") from exc

    # A refresh token must never be accepted where an access token is required.
    if expect is not None and claims.token_type is not expect:
        raise InvalidTokenError("wrong token type")

    return claims
