"""Tests for SQLCipher key derivation utilities."""

from app.utils.crypto import derive_sqlcipher_key


def test_key_derivation_is_deterministic():
    """Same secret should always derive the same key."""
    secret = "device-secret-123"
    key_one = derive_sqlcipher_key(secret)
    key_two = derive_sqlcipher_key(secret)
    assert key_one == key_two


def test_key_derivation_returns_64_char_hex():
    """Derived key must be 256 bits represented as 64 hex chars."""
    key = derive_sqlcipher_key("device-secret-abc")
    assert len(key) == 64
    int(key, 16)


def test_key_derivation_differs_for_different_secrets():
    """Different secrets should derive different keys."""
    key_one = derive_sqlcipher_key("device-secret-one")
    key_two = derive_sqlcipher_key("device-secret-two")
    assert key_one != key_two


def test_derived_key_represents_256_bits():
    """64 hex chars should decode to exactly 32 bytes."""
    key = derive_sqlcipher_key("device-secret-length-check")
    assert len(bytes.fromhex(key)) == 32
