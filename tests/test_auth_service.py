from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("sqlalchemy")

from config import load_settings
from database import create_database, upgrade_database
from repositories import AuthRepository
from services.auth import AuthService, AuthValidationError
from services.email_delivery import MemoryAuthEmailSender


def _service(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'auth.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    sender = MemoryAuthEmailSender()
    service = AuthService(AuthRepository(runtime), sender, load_settings({"APP_ENV": "test"}))
    return runtime, service, sender


def _token(message) -> str:
    return parse_qs(urlparse(message.action_url).query)["token"][0]


def test_register_verify_login_logout_round_trip(tmp_path):
    runtime, service, sender = _service(tmp_path)
    try:
        result = service.register(
            email="Person@Example.Test",
            password="correct horse battery staple!",
            display_name="  Тестовый   Пользователь ",
            verification_url_builder=lambda token: f"https://app.example.test/auth/verify?token={token}",
            now=1_000,
        )
        assert result.ok is True
        assert result.user is not None
        assert result.user.normalized_email == "person@example.test"
        assert result.user.display_name == "Тестовый Пользователь"
        assert result.user.password_hash != "correct horse battery staple!"

        verification = sender.latest("verify_email")
        assert verification is not None
        raw_token = _token(verification)
        assert raw_token not in (result.user.password_hash or "")

        verified = service.verify_email(raw_token, now=1_001)
        assert verified.ok is True
        assert verified.user is not None
        assert verified.user.status == "active"
        assert verified.user.email_verified_at == 1_001
        assert service.verify_email(raw_token, now=1_002).ok is False

        rejected = service.login(
            email="person@example.test",
            password="wrong password",
            user_agent="pytest",
            now=1_003,
        )
        assert rejected.code == "invalid_credentials"

        login = service.login(
            email="person@example.test",
            password="correct horse battery staple!",
            user_agent="pytest",
            now=1_004,
        )
        assert login.ok is True
        assert login.session_token
        authenticated = service.load_session(login.session_token, now=1_005)
        assert authenticated is not None
        assert authenticated.user.id == verified.user.id

        service.logout(login.session_token, now=1_006)
        assert service.load_session(login.session_token, now=1_007) is None
    finally:
        runtime.dispose()


def test_duplicate_registration_is_enumeration_safe_and_never_replaces_password(tmp_path):
    runtime, service, sender = _service(tmp_path)
    try:
        first = service.register(
            email="duplicate@example.test",
            password="Original very safe password 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=2_000,
        )
        second = service.register(
            email="DUPLICATE@example.test",
            password="Attacker replacement password 99!",
            display_name="Other",
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=2_001,
        )
        assert first.ok is True and second.ok is True
        assert second.user is None
        assert second.message == "Если адрес можно использовать, на него придёт письмо с дальнейшими шагами."
        token = _token(sender.latest("verify_email"))
        assert service.verify_email(token, now=2_002).ok is True
        assert service.login(
            email="duplicate@example.test",
            password="Original very safe password 42!",
            user_agent=None,
            now=2_003,
        ).ok is True
        assert service.login(
            email="duplicate@example.test",
            password="Attacker replacement password 99!",
            user_agent=None,
            now=2_004,
        ).ok is False
    finally:
        runtime.dispose()


def test_password_reset_is_single_use_and_revokes_existing_sessions(tmp_path):
    runtime, service, sender = _service(tmp_path)
    try:
        service.register(
            email="reset@example.test",
            password="Initial unique password 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=3_000,
        )
        assert service.verify_email(_token(sender.latest("verify_email")), now=3_001).ok
        first_login = service.login(
            email="reset@example.test",
            password="Initial unique password 42!",
            user_agent="device-one",
            now=3_002,
        )
        second_login = service.login(
            email="reset@example.test",
            password="Initial unique password 42!",
            user_agent="device-two",
            now=3_003,
        )
        assert first_login.session_token and second_login.session_token

        generic = service.request_password_reset(
            email="reset@example.test",
            reset_url_builder=lambda token: f"https://example.test/reset?token={token}",
            now=3_004,
        )
        unknown = service.request_password_reset(
            email="unknown@example.test",
            reset_url_builder=lambda token: f"https://example.test/reset?token={token}",
            now=3_005,
        )
        assert generic.message == unknown.message
        raw_reset = _token(sender.latest("password_reset"))

        reset = service.reset_password(
            raw_token=raw_reset,
            new_password="New unique password 99!",
            now=3_006,
        )
        assert reset.ok is True
        assert service.load_session(first_login.session_token, now=3_007) is None
        assert service.load_session(second_login.session_token, now=3_007) is None
        assert service.reset_password(
            raw_token=raw_reset,
            new_password="Another unique password 77!",
            now=3_008,
        ).ok is False
        assert service.login(
            email="reset@example.test",
            password="Initial unique password 42!",
            user_agent=None,
            now=3_009,
        ).ok is False
        assert service.login(
            email="reset@example.test",
            password="New unique password 99!",
            user_agent=None,
            now=3_010,
        ).ok is True
    finally:
        runtime.dispose()


def test_session_revocation_keeps_current_session(tmp_path):
    runtime, service, sender = _service(tmp_path)
    try:
        service.register(
            email="sessions@example.test",
            password="Device unique password 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=4_000,
        )
        user = service.verify_email(_token(sender.latest("verify_email")), now=4_001).user
        one = service.login(email=user.email, password="Device unique password 42!", user_agent="one", now=4_002)
        two = service.login(email=user.email, password="Device unique password 42!", user_agent="two", now=4_003)
        current = service.load_session(one.session_token, now=4_004)
        assert current is not None
        assert len(service.list_sessions(user.id, now=4_004)) == 2
        assert service.revoke_other_sessions(
            user_id=user.id,
            current_session_id=current.session.id,
            now=4_005,
        ) == 1
        assert service.load_session(one.session_token, now=4_006) is not None
        assert service.load_session(two.session_token, now=4_006) is None
    finally:
        runtime.dispose()


def test_validation_rejects_weak_password_and_malformed_email(tmp_path):
    runtime, service, _sender = _service(tmp_path)
    try:
        with pytest.raises(AuthValidationError, match="корректный email"):
            service.register(
                email="not-an-email",
                password="Long enough password 42!",
                display_name=None,
                verification_url_builder=lambda token: token,
            )
        with pytest.raises(AuthValidationError, match="не менее"):
            service.register(
                email="valid@example.test",
                password="short",
                display_name=None,
                verification_url_builder=lambda token: token,
            )
    finally:
        runtime.dispose()


def test_verification_token_supersession_and_expiry(tmp_path):
    runtime, service, sender = _service(tmp_path)
    try:
        service.register(
            email="verify-expiry@example.test",
            password="Verification unique password 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=5_000,
        )
        first_token = _token(sender.latest("verify_email"))
        service.resend_verification(
            email="verify-expiry@example.test",
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=5_001,
        )
        second_token = _token(sender.latest("verify_email"))
        assert first_token != second_token
        assert service.verify_email(first_token, now=5_002).ok is False
        assert service.verify_email(second_token, now=5_002).ok is True

        service.register(
            email="expired@example.test",
            password="Verification timeout phrase 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=6_000,
        )
        expired = _token(sender.latest("verify_email"))
        assert service.verify_email(
            expired,
            now=6_000 + service.settings.auth_verification_ttl_seconds + 1,
        ).ok is False
    finally:
        runtime.dispose()


def test_session_expiry_and_safe_local_redirect_policy(tmp_path):
    runtime, service, sender = _service(tmp_path)
    try:
        service.register(
            email="session-expiry@example.test",
            password="Session expiry password 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=7_000,
        )
        assert service.verify_email(_token(sender.latest("verify_email")), now=7_001).ok
        login = service.login(
            email="session-expiry@example.test",
            password="Session expiry password 42!",
            user_agent="pytest",
            now=7_002,
        )
        assert login.session_token
        assert service.load_session(login.session_token, now=7_003) is not None
        assert service.load_session(
            login.session_token,
            now=7_002 + service.settings.auth_session_ttl_seconds + 1,
        ) is None

        from services.auth import safe_next_path

        assert safe_next_path("/dashboard?tab=security") == "/dashboard?tab=security"
        for unsafe in (
            "https://evil.example/",
            "//evil.example/",
            "/\\evil.example/",
            "/dashboard\r\nLocation: https://evil.example/",
        ):
            assert safe_next_path(unsafe) == "/dashboard"
    finally:
        runtime.dispose()


def test_expired_verification_and_reset_tokens_fail_closed(tmp_path):
    runtime, service, sender = _service(tmp_path)
    try:
        service.register(
            email="expiry@example.test",
            password="Temporary unique password 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=10_000,
        )
        verification = _token(sender.latest("verify_email"))
        expired_at = 10_000 + service.settings.auth_verification_ttl_seconds + 1
        assert service.verify_email(verification, now=expired_at).ok is False

        service.resend_verification(
            email="expiry@example.test",
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=expired_at + 1,
        )
        verification = _token(sender.latest("verify_email"))
        assert service.verify_email(verification, now=expired_at + 2).ok is True

        service.request_password_reset(
            email="expiry@example.test",
            reset_url_builder=lambda token: f"https://example.test/reset?token={token}",
            now=20_000,
        )
        reset_token = _token(sender.latest("password_reset"))
        assert service.reset_token_active(reset_token, now=20_001) is True
        assert service.reset_password(
            raw_token=reset_token,
            new_password="Replacement unique password 99!",
            now=20_000 + service.settings.auth_reset_ttl_seconds + 1,
        ).ok is False
    finally:
        runtime.dispose()


def test_safe_next_path_rejects_external_and_backslash_values():
    from services.auth import safe_next_path

    assert safe_next_path("/dashboard?tab=security") == "/dashboard?tab=security"
    assert safe_next_path("https://evil.example/path") == "/dashboard"
    assert safe_next_path("//evil.example/path") == "/dashboard"
    assert safe_next_path("/\\evil.example/path") == "/dashboard"


def test_login_public_failure_is_identical_for_unknown_wrong_and_unverified(tmp_path):
    runtime, service, _sender = _service(tmp_path)
    try:
        service.register(
            email="pending-login@example.test",
            password="Pending unique password 42!",
            display_name=None,
            verification_url_builder=lambda token: f"https://example.test/verify?token={token}",
            now=6_000,
        )
        unknown = service.login(
            email="unknown-login@example.test",
            password="Any candidate password 42!",
            user_agent=None,
            now=6_001,
        )
        wrong = service.login(
            email="pending-login@example.test",
            password="Wrong candidate password 99!",
            user_agent=None,
            now=6_002,
        )
        pending = service.login(
            email="pending-login@example.test",
            password="Pending unique password 42!",
            user_agent=None,
            now=6_003,
        )
        assert unknown.code == wrong.code == pending.code == "invalid_credentials"
        assert unknown.message == wrong.message == pending.message
        assert "подтверждён" in pending.message
    finally:
        runtime.dispose()
