from __future__ import annotations

from services.passwords import hash_password, needs_rehash, verify_password


def test_password_hash_is_salted_versioned_and_one_way():
    password = "Long unique passphrase 42!"
    first = hash_password(password)
    second = hash_password(password)

    assert first.startswith("aca_scrypt$1$")
    assert second.startswith("aca_scrypt$1$")
    assert first != second
    assert password not in first
    assert verify_password(first, password) is True
    assert verify_password(first, "wrong password") is False
    assert needs_rehash(first) is False


def test_malformed_or_attacker_controlled_hashes_fail_closed():
    malformed = (
        None,
        "",
        "plain-text-password",
        "aca_scrypt$1$999999999$8$1$c2FsdA$ZGlnZXN0",
        "aca_scrypt$1$32768$8$1$not-base64$also-not-base64",
    )
    for encoded in malformed:
        assert verify_password(encoded, "candidate") is False
        assert needs_rehash(encoded) is True
