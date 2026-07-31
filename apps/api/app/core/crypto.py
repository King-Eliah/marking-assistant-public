"""Encryption for student identifiers at rest.

Index numbers are the one piece of directly identifying data this system
holds. They are stored encrypted in `student_identity_map`, separate from
everything on the marking path, so a read of the marking tables — by a
misconfigured query, a backup, or an attacker — yields no identities.

Fernet: AES-128-CBC with an HMAC-SHA256 authentication tag. Authenticated, so
a tampered ciphertext is rejected rather than silently decrypting to garbage
that might then be matched against a class list.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MissingEncryptionKeyError(RuntimeError):
    """No usable key outside development.

    Generating an ephemeral key would make every stored identity permanently
    unreadable after a restart — the marks would survive and no one would know
    whose they were.
    """


class DecryptionError(Exception):
    """The ciphertext is not ours, or has been altered.

    Never surfaces the underlying reason to a caller: distinguishing "wrong
    key" from "tampered" from "corrupt" leaks information about the key
    material.
    """


@lru_cache
def _cipher() -> MultiFernet:
    """The process-wide cipher.

    `MultiFernet` takes a list so keys can be rotated: put the new key first,
    keep the old one, and existing ciphertexts stay readable while new writes
    use the new key. A single-key deployment is just a list of one.
    """
    settings = get_settings()
    keys = [k.strip() for k in settings.identity_encryption_keys.split(",") if k.strip()]

    if not keys:
        if settings.app_env != "development":
            raise MissingEncryptionKeyError(
                "IDENTITY_ENCRYPTION_KEYS is empty. Student identifiers cannot be "
                f"stored in {settings.app_env} without a persistent key."
            )
        logger.warning(
            "No IDENTITY_ENCRYPTION_KEYS set — generating an ephemeral key. "
            "Anything encrypted now becomes unreadable on restart. Development only."
        )
        keys = [Fernet.generate_key().decode()]

    try:
        return MultiFernet([Fernet(k.encode()) for k in keys])
    except (ValueError, TypeError) as exc:
        raise MissingEncryptionKeyError(
            "IDENTITY_ENCRYPTION_KEYS contains a value that is not a valid "
            "Fernet key. Generate one with Fernet.generate_key()."
        ) from exc


def encrypt_identifier(value: str) -> bytes:
    """Encrypt a student identifier for storage.

    Whitespace is stripped first so that "  20512345 " and "20512345" do not
    become two different ciphertexts for the same student.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("cannot encrypt an empty identifier")
    return _cipher().encrypt(cleaned.encode("utf-8"))


def decrypt_identifier(token: bytes) -> str:
    """Decrypt a stored identifier.

    Every call is a reveal of identity and belongs in the audit log — see
    spec.md §5.3, where revealing identity is itself an audited event.
    """
    try:
        return _cipher().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionError("identifier could not be decrypted") from exc


def rotate(token: bytes) -> bytes:
    """Re-encrypt an existing ciphertext under the newest key."""
    try:
        return _cipher().rotate(token)
    except InvalidToken as exc:
        raise DecryptionError("identifier could not be rotated") from exc
