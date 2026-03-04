"""Cryptographic helpers for SQLCipher key management."""

from __future__ import annotations

import hashlib

from app.config import settings

_KDF_SALT = b"kinfolk-sqlcipher-key-v1"
_KDF_ITERATIONS = 200_000
_KEY_BYTES = 32


def derive_sqlcipher_key(device_secret: str) -> str:
    """Derive a deterministic SQLCipher-compatible 256-bit key.

    Returns a 64-character lowercase hex string suitable for PRAGMA key.
    """
    normalized_secret = device_secret.strip()
    if not normalized_secret:
        raise ValueError("database encryption secret must not be empty")

    derived_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        normalized_secret.encode("utf-8"),
        _KDF_SALT,
        _KDF_ITERATIONS,
        dklen=_KEY_BYTES,
    )
    return derived_bytes.hex()


def derive_sqlcipher_key_from_settings() -> str:
    """Derive SQLCipher key using configured device secret."""
    return derive_sqlcipher_key(settings.database_encryption_key)


def sqlcipher_hex_literal(hex_key: str) -> str:
    """Format a derived hex key as SQLCipher hex literal for PRAGMA key."""
    return f"x'{hex_key}'"
