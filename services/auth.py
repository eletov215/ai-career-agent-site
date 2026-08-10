"""First-party account service for AUTH-001."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from collections.abc import Callable
from urllib.parse import urlparse

from config import AppSettings
from domain import AuthActionResult, AuthenticatedSession, AuthUserRecord
from repositories import AuthRepository
from services.email_delivery import AuthEmail, AuthEmailSender
from services.passwords import DUMMY_PASSWORD_HASH, hash_password, verify_password

_VERIFY_PURPOSE = "verify_email"
_RESET_PURPOSE = "password_reset"
_COMMON_PASSWORDS = {
    "password",
    "password123",
    "qwerty123456",
    "123456789012",
    "adminadmin123",
    "пароль123456",
}
_EMAIL_LOCAL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_GENERIC_LOGIN_ERROR = "Неверный email, пароль или email ещё не подтверждён."


class AuthValidationError(ValueError):
    """Public-safe validation failure for account forms."""


def normalize_email(value: str) -> tuple[str, str]:
    """Return display and canonical email forms.

    AUTH-001 deliberately supports the conservative ASCII local-part subset and
    IDNA domains. This keeps uniqueness deterministic across PostgreSQL and
    SQLite without guessing provider-specific aliases.
    """

    raw = (value or "").strip()
    if not raw or len(raw) > 254 or raw.count("@") != 1:
        raise AuthValidationError("Введите корректный email.")
    local, domain = raw.rsplit("@", 1)
    if (
        not local
        or len(local) > 64
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or not _EMAIL_LOCAL_RE.fullmatch(local)
    ):
        raise AuthValidationError("Введите корректный email.")
    try:
        ascii_domain = domain.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise AuthValidationError("Введите корректный email.") from exc
    if not ascii_domain or len(ascii_domain) > 253 or "." not in ascii_domain:
        raise AuthValidationError("Введите корректный email.")
    labels = ascii_domain.split(".")
    if any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or not re.fullmatch(r"[a-z0-9-]+", label)
        for label in labels
    ):
        raise AuthValidationError("Введите корректный email.")
    normalized = f"{local.casefold()}@{ascii_domain}"
    return raw, normalized


def validate_display_name(value: str | None) -> str | None:
    normalized = " ".join((value or "").split())
    if not normalized:
        return None
    if len(normalized) > 120:
        raise AuthValidationError("Имя не должно превышать 120 символов.")
    if any(ord(char) < 32 for char in normalized):
        raise AuthValidationError("Имя содержит недопустимые символы.")
    return normalized


def validate_password(password: str, *, minimum_length: int, email: str | None = None) -> None:
    if not isinstance(password, str):
        raise AuthValidationError("Введите пароль.")
    if len(password) < minimum_length:
        raise AuthValidationError(f"Пароль должен содержать не менее {minimum_length} символов.")
    if len(password) > 128:
        raise AuthValidationError("Пароль не должен превышать 128 символов.")
    if password.casefold() in _COMMON_PASSWORDS:
        raise AuthValidationError("Выберите менее распространённый пароль.")
    if email:
        local = email.split("@", 1)[0].casefold()
        if len(local) >= 4 and local in password.casefold():
            raise AuthValidationError("Пароль не должен содержать email.")
    if len(set(password)) < 6:
        raise AuthValidationError("Пароль должен содержать больше разных символов.")


def hash_secret(value: str) -> str:
    """Hash opaque session/email tokens before persistence."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def user_agent_hash(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return hashlib.sha256(cleaned[:512].encode("utf-8", "ignore")).hexdigest()


def safe_next_path(value: str | None, *, fallback: str = "/dashboard") -> str:
    """Accept only local absolute paths for post-login redirects."""

    candidate = (value or "").strip()
    if not candidate:
        return fallback
    parsed = urlparse(candidate)
    if (
        parsed.scheme
        or parsed.netloc
        or not candidate.startswith("/")
        or candidate.startswith("//")
        or "\\" in candidate
        or any(ord(char) < 32 for char in candidate)
    ):
        return fallback
    return candidate[:2048]


class AuthService:
    """Own password, one-time-token, and revocable-session policy."""

    def __init__(
        self,
        repository: AuthRepository,
        email_sender: AuthEmailSender,
        settings: AppSettings,
    ) -> None:
        self.repository = repository
        self.email_sender = email_sender
        self.settings = settings

    @staticmethod
    def password_hash(password: str) -> str:
        return hash_password(password)

    @property
    def email_delivery_available(self) -> bool:
        return self.email_sender.available

    @property
    def email_backend_name(self) -> str:
        return self.email_sender.backend_name

    def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None,
        verification_url_builder: Callable[[str], str],
        now: int | None = None,
    ) -> AuthActionResult:
        timestamp = int(now or time.time())
        display = validate_display_name(display_name)
        public_email, normalized = normalize_email(email)
        validate_password(
            password,
            minimum_length=self.settings.auth_password_min_length,
            email=normalized,
        )

        # Deliberately perform the expensive hash before checking uniqueness so
        # duplicate registration has a closer timing profile to a new account.
        generated_hash = self.password_hash(password)
        existing = self.repository.find_user_by_email(normalized)
        if existing is not None:
            return self._generic_registration_result()

        user = self.repository.create_user(
            email=public_email,
            normalized_email=normalized,
            password_hash=generated_hash,
            display_name=display,
            now=timestamp,
        )
        if user is None:
            return self._generic_registration_result()

        raw_token = self._issue_token(
            user=user,
            purpose=_VERIFY_PURPOSE,
            ttl_seconds=self.settings.auth_verification_ttl_seconds,
            now=timestamp,
        )
        action_url = verification_url_builder(raw_token)
        self.email_sender.send(
            AuthEmail(
                purpose=_VERIFY_PURPOSE,
                recipient=user.email,
                subject="Подтвердите аккаунт AI Career Agent",
                text=(
                    f"Здравствуйте{', ' + user.display_name if user.display_name else ''}!\n\n"
                    "Подтвердите email, чтобы завершить регистрацию AI Career Agent:\n"
                    f"{action_url}\n\n"
                    "Если вы не регистрировались, просто проигнорируйте письмо."
                ),
                action_url=action_url,
            )
        )
        # Keep the browser-visible result identical for new addresses, existing
        # addresses, and temporary delivery failures. Delivery outcome remains
        # observable only through secret-free operational events.
        return AuthActionResult(
            ok=True,
            code="registration_received",
            message="Если адрес можно использовать, на него придёт письмо с дальнейшими шагами.",
            user=user,
        )

    @staticmethod
    def _generic_registration_result() -> AuthActionResult:
        return AuthActionResult(
            ok=True,
            code="registration_received",
            message="Если адрес можно использовать, на него придёт письмо с дальнейшими шагами.",
        )

    def resend_verification(
        self,
        *,
        email: str,
        verification_url_builder: Callable[[str], str],
        now: int | None = None,
    ) -> AuthActionResult:
        timestamp = int(now or time.time())
        try:
            _public_email, normalized = normalize_email(email)
        except AuthValidationError:
            return self._generic_delivery_result()
        user = self.repository.find_user_by_email(normalized)
        if user and not user.email_verified_at and user.status == "pending":
            raw_token = self._issue_token(
                user=user,
                purpose=_VERIFY_PURPOSE,
                ttl_seconds=self.settings.auth_verification_ttl_seconds,
                now=timestamp,
            )
            action_url = verification_url_builder(raw_token)
            self.email_sender.send(
                AuthEmail(
                    purpose=_VERIFY_PURPOSE,
                    recipient=user.email,
                    subject="Подтвердите аккаунт AI Career Agent",
                    text=(
                        "Подтвердите email, чтобы завершить регистрацию:\n"
                        f"{action_url}\n\n"
                        "Если вы не запрашивали письмо, проигнорируйте его."
                    ),
                    action_url=action_url,
                )
            )
        return self._generic_delivery_result()

    @staticmethod
    def _generic_delivery_result() -> AuthActionResult:
        return AuthActionResult(
            ok=True,
            code="request_received",
            message="Если аккаунт существует и действие доступно, письмо будет отправлено.",
        )

    def verify_email(self, raw_token: str, *, now: int | None = None) -> AuthActionResult:
        timestamp = int(now or time.time())
        user = self.repository.verify_email_with_token(
            token_hash=hash_secret(raw_token or ""),
            purpose=_VERIFY_PURPOSE,
            now=timestamp,
        )
        if user is None:
            return AuthActionResult(
                ok=False,
                code="invalid_token",
                message="Ссылка недействительна или срок её действия истёк.",
            )
        return AuthActionResult(
            ok=True,
            code="verified",
            message="Email подтверждён. Теперь можно войти в аккаунт.",
            user=user,
        )

    def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        now: int | None = None,
    ) -> AuthActionResult:
        timestamp = int(now or time.time())
        try:
            _public_email, normalized = normalize_email(email)
        except AuthValidationError:
            normalized = "invalid@example.invalid"
        user = self.repository.find_user_by_email(normalized)
        candidate_hash = user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
        password_ok = verify_password(candidate_hash, password or "")
        if (
            user is None
            or not password_ok
            or user.status != "active"
            or not user.email_verified_at
        ):
            # Keep one browser-visible failure for unknown, disabled, pending,
            # and wrong-password cases. The resend flow is available from the
            # login page without revealing whether this address exists.
            return AuthActionResult(False, "invalid_credentials", _GENERIC_LOGIN_ERROR)

        raw_session = secrets.token_urlsafe(32)
        self.repository.create_session(
            user_id=user.id,
            token_hash=hash_secret(raw_session),
            expires_at=timestamp + self.settings.auth_session_ttl_seconds,
            user_agent_hash=user_agent_hash(user_agent),
            now=timestamp,
        )
        self.repository.update_last_login(user.id, now=timestamp)
        return AuthActionResult(
            True,
            "authenticated",
            "Вы вошли в аккаунт.",
            user=user,
            session_token=raw_session,
        )

    def load_session(
        self,
        raw_session_token: str | None,
        *,
        now: int | None = None,
    ) -> AuthenticatedSession | None:
        if not raw_session_token:
            return None
        timestamp = int(now or time.time())
        token_hash = hash_secret(raw_session_token)
        auth_session = self.repository.get_active_session(token_hash, now=timestamp)
        if auth_session is None:
            return None
        user = self.repository.get_user(auth_session.user_id)
        if user is None or user.status != "active" or not user.email_verified_at:
            self.repository.revoke_session_by_hash(
                token_hash,
                reason="user_inactive",
                now=timestamp,
            )
            return None
        self.repository.touch_session(auth_session.id, now=timestamp)
        return AuthenticatedSession(user=user, session=auth_session)

    def logout(self, raw_session_token: str | None, *, now: int | None = None) -> None:
        if raw_session_token:
            self.repository.revoke_session_by_hash(
                hash_secret(raw_session_token),
                reason="logout",
                now=now,
            )

    def request_password_reset(
        self,
        *,
        email: str,
        reset_url_builder: Callable[[str], str],
        now: int | None = None,
    ) -> AuthActionResult:
        timestamp = int(now or time.time())
        try:
            _public_email, normalized = normalize_email(email)
        except AuthValidationError:
            return self._generic_delivery_result()
        user = self.repository.find_user_by_email(normalized)
        if user and user.status in {"active", "pending"} and user.password_hash:
            raw_token = self._issue_token(
                user=user,
                purpose=_RESET_PURPOSE,
                ttl_seconds=self.settings.auth_reset_ttl_seconds,
                now=timestamp,
            )
            action_url = reset_url_builder(raw_token)
            self.email_sender.send(
                AuthEmail(
                    purpose=_RESET_PURPOSE,
                    recipient=user.email,
                    subject="Сброс пароля AI Career Agent",
                    text=(
                        "Чтобы установить новый пароль, откройте ссылку:\n"
                        f"{action_url}\n\n"
                        "Если вы не запрашивали сброс, проигнорируйте письмо."
                    ),
                    action_url=action_url,
                )
            )
        return self._generic_delivery_result()

    def reset_token_active(self, raw_token: str, *, now: int | None = None) -> bool:
        if not raw_token:
            return False
        return self.repository.get_active_token(
            token_hash=hash_secret(raw_token),
            purpose=_RESET_PURPOSE,
            now=now,
        ) is not None

    def reset_password(
        self,
        *,
        raw_token: str,
        new_password: str,
        now: int | None = None,
    ) -> AuthActionResult:
        timestamp = int(now or time.time())
        token_hash = hash_secret(raw_token or "")
        token = self.repository.get_active_token(
            token_hash=token_hash,
            purpose=_RESET_PURPOSE,
            now=timestamp,
        )
        if token is None:
            return AuthActionResult(
                False,
                "invalid_token",
                "Ссылка недействительна или срок её действия истёк.",
            )
        user = self.repository.get_user(token.user_id)
        if user is None:
            return AuthActionResult(False, "invalid_token", "Ссылка недействительна.")
        validate_password(
            new_password,
            minimum_length=self.settings.auth_password_min_length,
            email=user.normalized_email,
        )
        updated = self.repository.reset_password_with_token(
            token_hash=token_hash,
            purpose=_RESET_PURPOSE,
            password_hash=self.password_hash(new_password),
            now=timestamp,
        )
        if updated is None:
            return AuthActionResult(
                False,
                "invalid_token",
                "Ссылка уже использована. Запросите новую.",
            )
        return AuthActionResult(
            True,
            "password_reset",
            "Пароль обновлён. Войдите заново на всех устройствах.",
            user=updated,
        )

    def list_sessions(self, user_id: str, *, now: int | None = None):
        return self.repository.list_active_sessions(user_id, now=now)

    def revoke_session(
        self,
        *,
        user_id: str,
        session_id: str,
        current_session_id: str,
        now: int | None = None,
    ) -> bool:
        if session_id == current_session_id:
            return False
        return bool(
            self.repository.revoke_session_by_id(
                user_id=user_id,
                session_id=session_id,
                reason="user_revoked",
                now=now,
            )
        )

    def revoke_other_sessions(
        self,
        *,
        user_id: str,
        current_session_id: str,
        now: int | None = None,
    ) -> int:
        return self.repository.revoke_all_sessions(
            user_id,
            reason="user_revoke_others",
            except_session_id=current_session_id,
            now=now,
        )

    def _issue_token(
        self,
        *,
        user: AuthUserRecord,
        purpose: str,
        ttl_seconds: int,
        now: int,
    ) -> str:
        raw_token = secrets.token_urlsafe(32)
        self.repository.issue_token(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_secret(raw_token),
            expires_at=now + ttl_seconds,
            now=now,
        )
        return raw_token
