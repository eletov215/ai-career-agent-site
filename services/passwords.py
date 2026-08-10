"""Versioned password hashing for first-party AI Career Agent accounts.

The format is application-owned so authentication tests do not depend on Flask
or Werkzeug being importable. Password material is never logged or persisted in
plaintext.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_SCHEME = "aca_scrypt"
_VERSION = "1"
_N = 2**15
_R = 8
_P = 1
_DKLEN = 32
_SALT_BYTES = 16
_MAX_MEMORY = 64 * 1024 * 1024


class PasswordHashError(ValueError):
    """Raised when a stored password hash is malformed or unsafe to evaluate."""


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str, *, maximum_bytes: int) -> bytes:
    if not value or len(value) > maximum_bytes * 2:
        raise PasswordHashError("Malformed password hash component.")
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise PasswordHashError("Malformed password hash component.") from exc
    if not decoded or len(decoded) > maximum_bytes:
        raise PasswordHashError("Malformed password hash component.")
    return decoded


def _derive(password: str, *, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=_DKLEN,
        maxmem=_MAX_MEMORY,
    )


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a versioned scrypt password hash."""

    if not isinstance(password, str):
        raise TypeError("password must be text")
    actual_salt = salt if salt is not None else secrets.token_bytes(_SALT_BYTES)
    if len(actual_salt) != _SALT_BYTES:
        raise ValueError(f"salt must be exactly {_SALT_BYTES} bytes")
    digest = _derive(password, salt=actual_salt, n=_N, r=_R, p=_P)
    return "$".join(
        (
            _SCHEME,
            _VERSION,
            str(_N),
            str(_R),
            str(_P),
            _encode(actual_salt),
            _encode(digest),
        )
    )


def _parse(encoded: str) -> tuple[int, int, int, bytes, bytes]:
    try:
        scheme, version, n_text, r_text, p_text, salt_text, digest_text = encoded.split("$")
        n, r, p = int(n_text), int(r_text), int(p_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise PasswordHashError("Malformed password hash.") from exc
    if scheme != _SCHEME or version != _VERSION:
        raise PasswordHashError("Unsupported password hash.")
    if n < 2**14 or n > 2**18 or n & (n - 1):
        raise PasswordHashError("Unsafe password hash cost.")
    if not 1 <= r <= 16 or not 1 <= p <= 4:
        raise PasswordHashError("Unsafe password hash cost.")
    salt = _decode(salt_text, maximum_bytes=32)
    digest = _decode(digest_text, maximum_bytes=64)
    if len(salt) < 16 or len(digest) != _DKLEN:
        raise PasswordHashError("Malformed password hash.")
    return n, r, p, salt, digest


def verify_password(encoded: str | None, password: str) -> bool:
    """Verify a candidate without propagating malformed-hash details."""

    if not encoded or not isinstance(password, str):
        return False
    try:
        n, r, p, salt, expected = _parse(encoded)
        actual = _derive(password, salt=salt, n=n, r=r, p=p)
    except (PasswordHashError, ValueError, TypeError, MemoryError):
        return False
    return hmac.compare_digest(actual, expected)


def needs_rehash(encoded: str | None) -> bool:
    if not encoded:
        return True
    try:
        n, r, p, _salt, _digest = _parse(encoded)
    except PasswordHashError:
        return True
    return (n, r, p) != (_N, _R, _P)


# Fixed salt is intentional: the value is not a credential and is used only to
# make unknown-user login paths perform the same expensive verification work.
DUMMY_PASSWORD_HASH = hash_password(
    "not-a-real-password-used-only-for-timing-equalization",
    salt=b"ACA-dummy-salt-1",
)
