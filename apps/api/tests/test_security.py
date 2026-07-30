"""Password hashing and token verification.

The forgery tests matter more than the happy path. A JWT implementation that
only proves "a valid token decodes" has demonstrated nothing — every known JWT
break is about what the verifier *accepts* that it should not.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

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

USER = uuid.uuid4()
TENANT = uuid.uuid4()


def _b64url(raw: bytes) -> str:
    """base64url without padding, as JWT requires."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private, public


def issue(private: str, **kwargs: object) -> str:
    params: dict[str, object] = {
        "user_id": USER,
        "tenant_id": TENANT,
        "role": Role.LECTURER,
        "token_type": TokenType.ACCESS,
        "private_key": private,
    }
    params.update(kwargs)
    return create_token(**params)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# passwords
# --------------------------------------------------------------------------


def test_correct_password_verifies() -> None:
    assert verify_password(
        "correct horse battery staple", hash_password("correct horse battery staple")
    )


def test_wrong_password_is_rejected() -> None:
    assert not verify_password("wrong", hash_password("right"))


def test_the_same_password_hashes_differently_every_time() -> None:
    """Per-call salt. Otherwise one precomputed table breaks every user at once."""
    a = hash_password("same password")
    b = hash_password("same password")
    assert a != b
    assert verify_password("same password", a)
    assert verify_password("same password", b)


def test_the_hash_is_argon2id_not_argon2i_or_2d() -> None:
    assert hash_password("x").startswith("$argon2id$")


def test_the_plaintext_never_appears_in_the_hash() -> None:
    secret = "Tw3lveCharacterSecret!"
    assert secret not in hash_password(secret)


def test_a_corrupt_stored_hash_denies_access() -> None:
    """A corrupt row is not a reason to let someone in."""
    assert not verify_password("anything", "not-a-hash")
    assert not verify_password("anything", "")


def test_a_corrupt_hash_is_flagged_for_rehash() -> None:
    assert needs_rehash("not-a-hash")


def test_a_current_hash_does_not_need_rehashing() -> None:
    assert not needs_rehash(hash_password("x"))


# --------------------------------------------------------------------------
# tokens — the happy path
# --------------------------------------------------------------------------


def test_a_valid_token_round_trips(keypair: tuple[str, str]) -> None:
    private, public = keypair
    claims = decode_token(issue(private), public)
    assert claims.user_id == USER
    assert claims.tenant_id == TENANT
    assert claims.role is Role.LECTURER
    assert claims.token_type is TokenType.ACCESS


def test_the_tenant_travels_in_the_token(keypair: tuple[str, str]) -> None:
    """I7: no request can be served without a tenant, and the RLS session
    variable is set from this claim and nothing else."""
    private, public = keypair
    assert decode_token(issue(private), public).tenant_id == TENANT


def test_two_tokens_differ_even_with_identical_claims(keypair: tuple[str, str]) -> None:
    """The jti makes each token individually revocable later."""
    private, _ = keypair
    assert issue(private) != issue(private)


# --------------------------------------------------------------------------
# tokens — forgery and misuse
# --------------------------------------------------------------------------


def test_algorithm_confusion_is_rejected(keypair: tuple[str, str]) -> None:
    """The attack this whole module is shaped around.

    An attacker takes the *public* key — which is public — and re-signs a token
    of their choosing with HS256, using that key as the HMAC secret. A verifier
    that trusts the token header's `alg` will happily verify it and hand over
    an admin session.

    Pinning `algorithms=["RS256"]` is the entire defence.

    The token is assembled by hand rather than with `jwt.encode`, because PyJWT
    refuses to encode HS256 with an asymmetric key. That refusal protects the
    *signing* side and says nothing about what our verifier accepts — which is
    the side under test. An attacker has no such scruples and will build the
    three segments themselves, exactly as below.
    """
    _, public = keypair
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps(
            {
                "sub": str(uuid.uuid4()),
                "tid": str(uuid.uuid4()),
                "role": "ADMIN",
                "typ": "access",
                "iat": int(datetime.now(UTC).timestamp()),
                "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            }
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    # the public key — which is public — used as the HMAC secret
    signature = _b64url(hmac.new(public.encode(), signing_input, hashlib.sha256).digest())
    forged = f"{header}.{payload}.{signature}"

    with pytest.raises(InvalidTokenError):
        decode_token(forged, public)


def test_an_unsigned_token_is_rejected(keypair: tuple[str, str]) -> None:
    """`alg: none` — the other classic."""
    _, public = keypair
    unsigned = jwt.encode(
        {
            "sub": str(USER),
            "tid": str(TENANT),
            "role": "ADMIN",
            "typ": "access",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        key="",
        algorithm="none",
    )
    with pytest.raises(InvalidTokenError):
        decode_token(unsigned, public)


def test_a_token_from_another_key_is_rejected(keypair: tuple[str, str]) -> None:
    _, public = keypair
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    with pytest.raises(InvalidTokenError):
        decode_token(issue(other_pem), public)


def test_an_expired_token_is_rejected(keypair: tuple[str, str]) -> None:
    private, public = keypair
    stale = issue(private, issued_at=datetime.now(UTC) - timedelta(days=2))
    with pytest.raises(InvalidTokenError):
        decode_token(stale, public)


def test_a_refresh_token_cannot_be_used_as_an_access_token(
    keypair: tuple[str, str],
) -> None:
    """Refresh tokens live for a week. Accepting one as an access token turns a
    900-second exposure into a seven-day one."""
    private, public = keypair
    refresh = issue(private, token_type=TokenType.REFRESH)

    decode_token(refresh, public, expect=TokenType.REFRESH)  # fine
    with pytest.raises(InvalidTokenError):
        decode_token(refresh, public, expect=TokenType.ACCESS)


def test_a_tampered_payload_is_rejected(keypair: tuple[str, str]) -> None:
    """Escalate LECTURER to ADMIN by editing the payload segment."""
    private, public = keypair
    header, payload, signature = issue(private).split(".")

    decoded = json.loads(base64.urlsafe_b64decode(payload + "=="))
    decoded["role"] = "ADMIN"
    tampered_payload = base64.urlsafe_b64encode(json.dumps(decoded).encode()).rstrip(b"=").decode()

    with pytest.raises(InvalidTokenError):
        decode_token(f"{header}.{tampered_payload}.{signature}", public)


def test_garbage_is_rejected(keypair: tuple[str, str]) -> None:
    _, public = keypair
    for junk in ("", "not.a.token", "a.b.c", "....", "Bearer xyz"):
        with pytest.raises(InvalidTokenError):
            decode_token(junk, public)


def test_a_token_missing_the_tenant_claim_is_rejected(keypair: tuple[str, str]) -> None:
    """Without a tenant there is no RLS scope to set, so the request must not
    proceed rather than default to anything."""
    private, public = keypair
    no_tenant = jwt.encode(
        {
            "sub": str(USER),
            "role": "LECTURER",
            "typ": "access",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        private,
        algorithm="RS256",
    )
    with pytest.raises(InvalidTokenError):
        decode_token(no_tenant, public)


def test_an_unknown_role_is_rejected(keypair: tuple[str, str]) -> None:
    private, public = keypair
    bad_role = jwt.encode(
        {
            "sub": str(USER),
            "tid": str(TENANT),
            "role": "SUPERADMIN",
            "typ": "access",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        },
        private,
        algorithm="RS256",
    )
    with pytest.raises(InvalidTokenError):
        decode_token(bad_role, public)
