"""JWT signing key material.

The private key is read from `JWT_PRIVATE_KEY_PATH` (Appendix A) and the
public key is derived from it, so there is one file to provision and no way
for the pair to drift apart.

In development the file usually does not exist. Rather than refusing to start,
an ephemeral pair is generated in memory — which is correct behaviour for dev
and catastrophic in production, so `require_persistent_keys` refuses it
outside development.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MissingSigningKeyError(RuntimeError):
    """No signing key outside development.

    An ephemeral key would invalidate every issued token on restart and differ
    between replicas, so a deployment that reaches this state is misconfigured
    and must not serve traffic.
    """


@dataclass(frozen=True, slots=True)
class KeyPair:
    private_pem: str
    public_pem: str


def _generate() -> KeyPair:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return KeyPair(private_pem=private_pem, public_pem=public_pem)


def _load(path: Path) -> KeyPair:
    private_pem = path.read_text()
    key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return KeyPair(private_pem=private_pem, public_pem=public_pem)


@lru_cache
def get_keypair() -> KeyPair:
    """The process-wide signing pair."""
    settings = get_settings()
    path = Path(settings.jwt_private_key_path)

    if path.is_file():
        return _load(path)

    if settings.app_env != "development":
        raise MissingSigningKeyError(
            f"no signing key at {path}. An ephemeral key is never acceptable "
            f"in {settings.app_env}: tokens would not survive a restart and "
            f"replicas would not agree."
        )

    logger.warning(
        "No signing key at %s — generating an ephemeral pair. "
        "Tokens will not survive a restart. Development only.",
        path,
    )
    return _generate()
