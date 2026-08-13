"""PROF-003 server-side resume draft policy, validation, and versioning."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from domain import ResumeAssetRecord, ResumeDraftRecord, ResumeExportRecord, ResumeVersionRecord
from repositories.resume_drafts import (
    ResumeDraftConflictError as RepositoryConflictError,
    ResumeDraftNotFoundError,
    ResumeDraftRepository,
)

RESUME_DRAFT_SCHEMA_VERSION = 1
RESUME_QUESTION_KEYS = (
    "name",
    "role",
    "experience",
    "achievements",
    "skills",
    "education",
    "contacts",
    "goal",
)
RESUME_QUESTIONS = (
    "Привет! Я помогу создать профессиональное резюме. Для начала, как вас зовут?",
    "На какую должность вы хотите устроиться?",
    "Расскажите о вашем опыте работы. Где вы работали и сколько времени?",
    "Какие задачи или достижения с прошлого места работы вы считаете самыми важными?",
    "Какими профессиональными навыками, инструментами или технологиями вы владеете?",
    "Расскажите об образовании, курсах или профессиональной подготовке.",
    "Какие контакты добавить в резюме? Укажите телефон, email и при желании ссылку на портфолио.",
    "Что для вас важно в новой работе: формат, график, зарплата, город или другие условия?",
)
ANSWER_LIMITS = {
    "name": 180,
    "role": 180,
    "experience": 8_000,
    "achievements": 6_000,
    "skills": 4_000,
    "education": 5_000,
    "contacts": 2_000,
    "goal": 3_000,
}
RESUME_ASSET_KINDS = {"photo", "university_logo"}
RESUME_VERSION_REASONS = {"checkpoint", "export", "restore"}
RESUME_ASSET_CONTENT_TYPES = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/webp": b"RIFF",
    "image/gif": b"GIF",
    "image/x-icon": b"\x00\x00\x01\x00",
    "image/vnd.microsoft.icon": b"\x00\x00\x01\x00",
}
RESUME_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_RESUME_ASSET_BYTES = 2 * 1024 * 1024
MAX_RESUME_DRAFT_STATE_BYTES = 160 * 1024
MAX_RESUME_MESSAGES = 40
MAX_RESUME_MESSAGE_TEXT = 5_000
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ResumeDraftValidationError(ValueError):
    """Raised when a draft payload violates the bounded schema."""


class ResumeDraftConflictError(RuntimeError):
    """Raised when optimistic draft revision protection detects a stale client."""


@dataclass(frozen=True, slots=True)
class ResumeDraftView:
    id: str
    user_id: str
    schema_version: int
    revision: int
    title: str
    state: dict[str, Any]
    content_hash: str
    completion_percent: int
    profile_version: int | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class ResumeDraftSummary:
    draft: ResumeDraftView
    version_count: int
    export_count: int


@dataclass(frozen=True, slots=True)
class ResumeDraftSaveResult:
    draft: ResumeDraftView
    changed: bool


@dataclass(frozen=True, slots=True)
class ResumeCheckpointResult:
    version: ResumeVersionRecord
    created: bool


@dataclass(frozen=True, slots=True)
class ResumeExportResult:
    export: ResumeExportRecord
    version: ResumeVersionRecord
    version_created: bool


def _clean_text(value: Any, *, label: str, maximum: int, multiline: bool = False) -> str:
    text = str(value or "").replace("\x00", "")
    if multiline:
        text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    else:
        text = " ".join(text.split())
    if len(text) > maximum:
        raise ResumeDraftValidationError(f"{label}: максимум {maximum} символов.")
    return text


def _uuid_or_none(value: Any, *, label: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return str(uuid.UUID(text))
    except ValueError as exc:
        raise ResumeDraftValidationError(f"{label} имеет неверный формат.") from exc


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def default_resume_state() -> dict[str, Any]:
    return {
        "schemaVersion": RESUME_DRAFT_SCHEMA_VERSION,
        "index": 0,
        "answers": {},
        "messages": [],
        "photoAssetId": None,
        "universityLogoAssetId": None,
        "universityLogoFor": "",
        "universityResolvedName": "",
    }


def normalise_resume_state(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise ResumeDraftValidationError("Черновик имеет неверный формат.")

    try:
        schema_version = int(
            payload.get("schemaVersion")
            or payload.get("schema_version")
            or RESUME_DRAFT_SCHEMA_VERSION
        )
    except (TypeError, ValueError) as exc:
        raise ResumeDraftValidationError("Версия формата черновика неверна.") from exc
    if schema_version != RESUME_DRAFT_SCHEMA_VERSION:
        raise ResumeDraftValidationError("Эта версия черновика пока не поддерживается.")

    try:
        index = int(payload.get("index") or 0)
    except (TypeError, ValueError) as exc:
        raise ResumeDraftValidationError("Текущий шаг черновика имеет неверный формат.") from exc
    if index < 0 or index > len(RESUME_QUESTION_KEYS):
        raise ResumeDraftValidationError("Текущий шаг черновика вне допустимого диапазона.")

    raw_answers = payload.get("answers") or {}
    if not isinstance(raw_answers, Mapping):
        raise ResumeDraftValidationError("Ответы черновика имеют неверный формат.")
    answers: dict[str, str] = {}
    unknown_keys = set(str(key) for key in raw_answers) - set(RESUME_QUESTION_KEYS)
    if unknown_keys:
        raise ResumeDraftValidationError("Черновик содержит неизвестные поля ответов.")
    for key in RESUME_QUESTION_KEYS:
        if key not in raw_answers:
            continue
        value = _clean_text(
            raw_answers.get(key),
            label=f"Поле «{key}»",
            maximum=ANSWER_LIMITS[key],
            multiline=True,
        )
        if value:
            answers[key] = value

    raw_messages = payload.get("messages") or []
    if not isinstance(raw_messages, Sequence) or isinstance(
        raw_messages, (str, bytes, bytearray)
    ):
        raise ResumeDraftValidationError("История интервью имеет неверный формат.")
    if len(raw_messages) > MAX_RESUME_MESSAGES:
        raise ResumeDraftValidationError("История интервью слишком длинная.")
    messages: list[dict[str, str]] = []
    for item in raw_messages:
        if not isinstance(item, Mapping):
            raise ResumeDraftValidationError("Сообщение интервью имеет неверный формат.")
        message_type = str(item.get("type") or "").strip().casefold()
        if message_type not in {"ai", "user"}:
            raise ResumeDraftValidationError("Неизвестный тип сообщения интервью.")
        text = _clean_text(
            item.get("text"),
            label="Сообщение интервью",
            maximum=MAX_RESUME_MESSAGE_TEXT,
            multiline=True,
        )
        if text:
            messages.append({"type": message_type, "text": text})

    result = {
        "schemaVersion": schema_version,
        "index": index,
        "answers": answers,
        "messages": messages,
        "photoAssetId": _uuid_or_none(
            payload.get("photoAssetId") or payload.get("photo_asset_id"),
            label="Фотография",
        ),
        "universityLogoAssetId": _uuid_or_none(
            payload.get("universityLogoAssetId")
            or payload.get("university_logo_asset_id"),
            label="Эмблема",
        ),
        "universityLogoFor": _clean_text(
            payload.get("universityLogoFor") or payload.get("university_logo_for"),
            label="Название учебного заведения для эмблемы",
            maximum=500,
        ),
        "universityResolvedName": _clean_text(
            payload.get("universityResolvedName")
            or payload.get("university_resolved_name"),
            label="Распознанное название учебного заведения",
            maximum=500,
        ),
    }
    encoded = _canonical_json(result).encode("utf-8")
    if len(encoded) > MAX_RESUME_DRAFT_STATE_BYTES:
        raise ResumeDraftValidationError("Черновик слишком большой для сохранения.")
    return result


def resume_completion_percent(state: Mapping[str, Any]) -> int:
    answers = state.get("answers") or {}
    completed = sum(1 for key in RESUME_QUESTION_KEYS if str(answers.get(key) or "").strip())
    return int(round(completed / len(RESUME_QUESTION_KEYS) * 100))


def _record_view(record: ResumeDraftRecord) -> ResumeDraftView:
    try:
        state = normalise_resume_state(json.loads(record.state_json))
    except (json.JSONDecodeError, ResumeDraftValidationError) as exc:
        raise ResumeDraftValidationError("Сохранённый черновик повреждён.") from exc
    return ResumeDraftView(
        id=record.id,
        user_id=record.user_id,
        schema_version=record.schema_version,
        revision=record.revision,
        title=record.title,
        state=state,
        content_hash=record.content_hash,
        completion_percent=record.completion_percent,
        profile_version=record.profile_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _format_month(value: Any) -> str:
    text = str(value or "").strip()
    return text


def state_from_profile(profile: Any, *, display_name: str | None = None) -> dict[str, Any]:
    """Build a document draft from confirmed PROF-001 facts only."""

    state = default_resume_state()
    answers: dict[str, str] = {}
    name = _clean_text(display_name, label="Имя", maximum=180) if display_name else ""
    if name:
        answers["name"] = name

    headline = str(getattr(profile, "headline", None) or "").strip()
    goals = getattr(profile, "goals", {}) or {}
    target_roles = list(goals.get("target_roles") or []) if isinstance(goals, Mapping) else []
    role = headline or (str(target_roles[0]).strip() if target_roles else "")
    if role:
        answers["role"] = role

    employment_lines: list[str] = []
    for row in getattr(profile, "employment", ()) or ():
        company = str(row.get("company") or "").strip()
        position = str(row.get("position") or "").strip()
        start = _format_month(row.get("start"))
        end = "по настоящее время" if row.get("current") else _format_month(row.get("end"))
        heading = " — ".join(item for item in (company, position) if item)
        period = " — ".join(item for item in (start, end) if item)
        description = str(row.get("description") or "").strip()
        value = heading
        if period:
            value = f"{value} ({period})" if value else period
        if description:
            value = f"{value}\n{description}" if value else description
        if value:
            employment_lines.append(value)
    if employment_lines:
        answers["experience"] = "\n\n".join(employment_lines)

    achievement_lines: list[str] = []
    for row in getattr(profile, "achievements", ()) or ():
        title = str(row.get("title") or "").strip()
        year = row.get("year")
        description = str(row.get("description") or "").strip()
        value = title
        if year:
            value = f"{value} ({year})" if value else str(year)
        if description:
            value = f"{value}: {description}" if value else description
        if value:
            achievement_lines.append(value)
    if achievement_lines:
        answers["achievements"] = "\n".join(achievement_lines)

    skills = [str(item.get("name") or "").strip() for item in (getattr(profile, "skills", ()) or ())]
    skills = [item for item in skills if item]
    if skills:
        answers["skills"] = ", ".join(skills)

    education_lines: list[str] = []
    for row in getattr(profile, "education", ()) or ():
        institution = str(row.get("institution") or "").strip()
        degree = str(row.get("degree") or "").strip()
        field = str(row.get("field") or "").strip()
        years = "–".join(
            str(item)
            for item in (row.get("start_year"), row.get("end_year"))
            if item
        )
        first = ", ".join(item for item in (institution, degree, field) if item)
        description = str(row.get("description") or "").strip()
        value = first
        if years:
            value = f"{value} ({years})" if value else years
        if description:
            value = f"{value}\n{description}" if value else description
        if value:
            education_lines.append(value)
    if education_lines:
        answers["education"] = "\n\n".join(education_lines)

    contacts = getattr(profile, "contacts", {}) or {}
    if isinstance(contacts, Mapping):
        contact_values = [
            contacts.get("phone"),
            contacts.get("contact_email"),
            contacts.get("telegram"),
            contacts.get("portfolio_url"),
            contacts.get("linkedin_url"),
        ]
        clean_contacts = [str(item).strip() for item in contact_values if str(item or "").strip()]
        if clean_contacts:
            answers["contacts"] = " · ".join(clean_contacts)

    goal_parts: list[str] = []
    geography = getattr(profile, "geography", {}) or {}
    if isinstance(geography, Mapping):
        preferred = [str(item).strip() for item in geography.get("preferred_locations") or [] if str(item).strip()]
        if preferred:
            goal_parts.append("Локации: " + ", ".join(preferred))
    if isinstance(goals, Mapping):
        formats = [str(item).strip() for item in goals.get("work_formats") or [] if str(item).strip()]
        employment_types = [str(item).strip() for item in goals.get("employment_types") or [] if str(item).strip()]
        if formats:
            goal_parts.append("Формат: " + ", ".join(formats))
        if employment_types:
            goal_parts.append("Занятость: " + ", ".join(employment_types))
    salary = getattr(profile, "salary", {}) or {}
    if isinstance(salary, Mapping) and (salary.get("minimum") is not None or salary.get("maximum") is not None):
        minimum = salary.get("minimum")
        maximum = salary.get("maximum")
        currency = str(salary.get("currency") or "").strip()
        if minimum is not None and maximum is not None:
            salary_text = f"{minimum}–{maximum} {currency}".strip()
        elif minimum is not None:
            salary_text = f"от {minimum} {currency}".strip()
        else:
            salary_text = f"до {maximum} {currency}".strip()
        goal_parts.append("Зарплата: " + salary_text)
    if goal_parts:
        answers["goal"] = "; ".join(goal_parts)

    first_missing = len(RESUME_QUESTION_KEYS)
    for idx, key in enumerate(RESUME_QUESTION_KEYS):
        if not answers.get(key):
            first_missing = idx
            break
    state["index"] = first_missing
    state["answers"] = answers
    messages: list[dict[str, str]] = []
    for idx in range(first_missing):
        key = RESUME_QUESTION_KEYS[idx]
        messages.append({"type": "ai", "text": RESUME_QUESTIONS[idx]})
        messages.append({"type": "user", "text": answers[key]})
    state["messages"] = messages
    return normalise_resume_state(state)


class ResumeDraftService:
    """Own server-side resume drafts without making them canonical profile facts."""

    def __init__(self, repository: ResumeDraftRepository) -> None:
        self.repository = repository

    @staticmethod
    def _title(value: Any) -> str:
        title = _clean_text(value, label="Название резюме", maximum=160)
        return title or "Новое резюме"

    @staticmethod
    def _state_material(state: Mapping[str, Any]) -> tuple[str, str, int]:
        state_json = _canonical_json(state)
        content_hash = hashlib.sha256(state_json.encode("utf-8")).hexdigest()
        completion = resume_completion_percent(state)
        return state_json, content_hash, completion

    def _validate_asset_references(
        self,
        *,
        user_id: str,
        draft_id: str,
        state: Mapping[str, Any],
    ) -> None:
        references = (
            ("photoAssetId", "photo", "Фотография"),
            ("universityLogoAssetId", "university_logo", "Эмблема"),
        )
        for key, kind, label in references:
            asset_id = state.get(key)
            if not asset_id:
                continue
            if not self.repository.asset_belongs_to_draft(
                user_id=str(user_id),
                draft_id=str(draft_id),
                asset_id=str(asset_id),
                kind=kind,
            ):
                raise ResumeDraftValidationError(
                    f"{label} не принадлежит этому черновику. Загрузите изображение заново."
                )

    def get(self, *, user_id: str, draft_id: str) -> ResumeDraftView | None:
        record = self.repository.get_by_owner(user_id=str(user_id), draft_id=str(draft_id))
        return _record_view(record) if record else None

    def list_drafts(self, *, user_id: str) -> list[ResumeDraftSummary]:
        result: list[ResumeDraftSummary] = []
        for record in self.repository.list_by_user(user_id=str(user_id), limit=100):
            version_count, export_count = self.repository.counts(
                user_id=str(user_id),
                draft_id=record.id,
            )
            result.append(
                ResumeDraftSummary(
                    draft=_record_view(record),
                    version_count=version_count,
                    export_count=export_count,
                )
            )
        return result

    def create(
        self,
        *,
        user_id: str,
        title: str | None = None,
        profile: Any | None = None,
        display_name: str | None = None,
        now: int | None = None,
    ) -> ResumeDraftView:
        state = (
            state_from_profile(profile, display_name=display_name)
            if profile is not None and getattr(profile, "exists", False)
            else normalise_resume_state(
                {
                    **default_resume_state(),
                    "answers": ({"name": display_name} if display_name else {}),
                }
            )
        )
        role = str(state.get("answers", {}).get("role") or "").strip()
        resolved_title = self._title(title or (f"Резюме — {role}" if role else "Новое резюме"))
        state_json, content_hash, completion = self._state_material(state)
        record = self.repository.create(
            user_id=str(user_id),
            title=resolved_title,
            schema_version=RESUME_DRAFT_SCHEMA_VERSION,
            state_json=state_json,
            content_hash=content_hash,
            completion_percent=completion,
            profile_version=(
                int(getattr(profile, "version", 0))
                if profile is not None and getattr(profile, "exists", False)
                else None
            ),
            now=now,
        )
        return _record_view(record)

    def latest_or_create(
        self,
        *,
        user_id: str,
        profile: Any | None,
        display_name: str | None,
    ) -> ResumeDraftView:
        latest = self.repository.latest_by_user(user_id=str(user_id))
        if latest:
            return _record_view(latest)
        return self.create(
            user_id=str(user_id),
            profile=profile,
            display_name=display_name,
        )

    def save(
        self,
        *,
        user_id: str,
        draft_id: str,
        expected_revision: int,
        state: Mapping[str, Any],
        now: int | None = None,
    ) -> ResumeDraftSaveResult:
        try:
            expected = int(expected_revision)
        except (TypeError, ValueError) as exc:
            raise ResumeDraftValidationError("Версия черновика имеет неверный формат.") from exc
        normalised_state = normalise_resume_state(state)
        self._validate_asset_references(
            user_id=str(user_id),
            draft_id=str(draft_id),
            state=normalised_state,
        )
        state_json, content_hash, completion = self._state_material(normalised_state)
        try:
            record, changed = self.repository.save_state(
                user_id=str(user_id),
                draft_id=str(draft_id),
                expected_revision=expected,
                schema_version=RESUME_DRAFT_SCHEMA_VERSION,
                state_json=state_json,
                content_hash=content_hash,
                completion_percent=completion,
                now=now,
            )
        except RepositoryConflictError as exc:
            raise ResumeDraftConflictError(str(exc)) from exc
        return ResumeDraftSaveResult(draft=_record_view(record), changed=changed)

    def rename(self, *, user_id: str, draft_id: str, title: Any) -> ResumeDraftView:
        record = self.repository.rename(
            user_id=str(user_id),
            draft_id=str(draft_id),
            title=self._title(title),
        )
        return _record_view(record)

    def delete(self, *, user_id: str, draft_id: str) -> bool:
        return self.repository.delete(user_id=str(user_id), draft_id=str(draft_id))

    def checkpoint(
        self,
        *,
        user_id: str,
        draft_id: str,
        expected_revision: int,
    ) -> ResumeCheckpointResult:
        try:
            version, created = self.repository.create_checkpoint(
                user_id=str(user_id),
                draft_id=str(draft_id),
                expected_revision=int(expected_revision),
                reason="checkpoint",
            )
        except RepositoryConflictError as exc:
            raise ResumeDraftConflictError(str(exc)) from exc
        return ResumeCheckpointResult(version=version, created=created)

    def counts(self, *, user_id: str, draft_id: str) -> tuple[int, int]:
        return self.repository.counts(
            user_id=str(user_id),
            draft_id=str(draft_id),
        )

    def list_versions(
        self,
        *,
        user_id: str,
        draft_id: str,
    ) -> list[ResumeVersionRecord]:
        return self.repository.list_versions(
            user_id=str(user_id),
            draft_id=str(draft_id),
            limit=200,
        )

    def get_version(
        self,
        *,
        user_id: str,
        draft_id: str,
        version: int,
    ) -> ResumeVersionRecord | None:
        return self.repository.get_version(
            user_id=str(user_id),
            draft_id=str(draft_id),
            version=int(version),
        )

    def restore(
        self,
        *,
        user_id: str,
        draft_id: str,
        version: int,
        expected_revision: int,
    ) -> tuple[ResumeDraftView, ResumeVersionRecord]:
        source = self.get_version(
            user_id=str(user_id),
            draft_id=str(draft_id),
            version=int(version),
        )
        if source is None:
            raise ResumeDraftNotFoundError("Версия резюме не найдена.")
        try:
            state = normalise_resume_state(json.loads(source.snapshot_json))
        except (json.JSONDecodeError, ResumeDraftValidationError) as exc:
            raise ResumeDraftValidationError("Сохранённая версия повреждена.") from exc
        try:
            draft, restored = self.repository.restore_version(
                user_id=str(user_id),
                draft_id=str(draft_id),
                version=int(version),
                expected_revision=int(expected_revision),
                completion_percent=resume_completion_percent(state),
            )
        except RepositoryConflictError as exc:
            raise ResumeDraftConflictError(str(exc)) from exc
        return _record_view(draft), restored

    def store_asset(
        self,
        *,
        user_id: str,
        draft_id: str,
        kind: str,
        content_type: str,
        data: bytes,
    ) -> ResumeAssetRecord:
        resolved_kind = str(kind or "").strip().casefold()
        if resolved_kind not in RESUME_ASSET_KINDS:
            raise ResumeDraftValidationError("Неизвестный тип изображения.")
        resolved_type = str(content_type or "").split(";", 1)[0].strip().casefold()
        signature = RESUME_ASSET_CONTENT_TYPES.get(resolved_type)
        if signature is None:
            raise ResumeDraftValidationError("Формат изображения не поддерживается.")
        if resolved_kind == "photo" and resolved_type not in RESUME_PHOTO_CONTENT_TYPES:
            raise ResumeDraftValidationError("Для фотографии поддерживаются только JPG, PNG и WebP.")
        payload = bytes(data or b"")
        if not payload:
            raise ResumeDraftValidationError("Изображение пустое.")
        if len(payload) > MAX_RESUME_ASSET_BYTES:
            raise ResumeDraftValidationError("Изображение после обработки не должно превышать 2 МБ.")
        if resolved_type == "image/webp":
            valid_signature = (
                len(payload) >= 12
                and payload.startswith(b"RIFF")
                and payload[8:12] == b"WEBP"
            )
        elif resolved_type == "image/gif":
            valid_signature = payload.startswith((b"GIF87a", b"GIF89a"))
        else:
            valid_signature = payload.startswith(signature)
        if not valid_signature:
            raise ResumeDraftValidationError("Содержимое изображения не соответствует формату файла.")
        digest = hashlib.sha256(payload).hexdigest()
        return self.repository.store_asset(
            user_id=str(user_id),
            draft_id=str(draft_id),
            kind=resolved_kind,
            content_type=resolved_type,
            data=payload,
            sha256=digest,
        )

    def get_asset(self, *, user_id: str, asset_id: str) -> ResumeAssetRecord | None:
        return self.repository.get_asset(user_id=str(user_id), asset_id=str(asset_id))

    def record_export(
        self,
        *,
        user_id: str,
        draft_id: str,
        expected_revision: int,
        page_count: Any,
        byte_size: Any,
        pdf_sha256: Any,
        file_name: Any,
    ) -> ResumeExportResult:
        try:
            pages = int(page_count)
            size = int(byte_size)
        except (TypeError, ValueError) as exc:
            raise ResumeDraftValidationError("Метаданные PDF имеют неверный формат.") from exc
        if pages < 1 or pages > 100:
            raise ResumeDraftValidationError("Количество страниц PDF вне допустимого диапазона.")
        if size < 1 or size > 50 * 1024 * 1024:
            raise ResumeDraftValidationError("Размер PDF вне допустимого диапазона.")
        digest = str(pdf_sha256 or "").strip().casefold()
        if not _SHA256_RE.fullmatch(digest):
            raise ResumeDraftValidationError("Контрольная сумма PDF имеет неверный формат.")
        name = _clean_text(file_name, label="Имя PDF", maximum=255) or "resume.pdf"
        try:
            export, version, created = self.repository.record_export(
                user_id=str(user_id),
                draft_id=str(draft_id),
                expected_revision=int(expected_revision),
                page_count=pages,
                byte_size=size,
                pdf_sha256=digest,
                file_name=name,
            )
        except RepositoryConflictError as exc:
            raise ResumeDraftConflictError(str(exc)) from exc
        return ResumeExportResult(
            export=export,
            version=version,
            version_created=created,
        )

    @staticmethod
    def client_state(
        draft: ResumeDraftView,
        *,
        asset_url_builder: Callable[[str], str],
    ) -> dict[str, Any]:
        state = json.loads(_canonical_json(draft.state))
        photo_id = state.get("photoAssetId")
        logo_id = state.get("universityLogoAssetId")
        state["photo"] = asset_url_builder(photo_id) if photo_id else ""
        state["universityLogo"] = asset_url_builder(logo_id) if logo_id else ""
        return state

    @staticmethod
    def version_state(version: ResumeVersionRecord) -> dict[str, Any]:
        try:
            return normalise_resume_state(json.loads(version.snapshot_json))
        except (json.JSONDecodeError, ResumeDraftValidationError) as exc:
            raise ResumeDraftValidationError("Сохранённая версия повреждена.") from exc
