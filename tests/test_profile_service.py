from __future__ import annotations

import time
import uuid

import pytest
from sqlalchemy import func, select

from database import create_database, upgrade_database
from models import CareerProfileVersion, User
from repositories import CareerProfileRepository
from services.profile import (
    CareerProfileService,
    ProfileConflictError,
    ProfileValidationError,
)


def _active_user(email: str) -> User:
    now = int(time.time())
    return User(
        id=str(uuid.uuid4()),
        email=email,
        normalized_email=email.casefold(),
        display_name="Profile Service",
        status="active",
        email_verified_at=now,
        password_hash=None,
        password_changed_at=None,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def profile_runtime(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'profile-service.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    with runtime.session() as session:
        first = _active_user("profile-first@example.test")
        second = _active_user("profile-second@example.test")
        session.add_all([first, second])
        session.commit()
        ids = (first.id, second.id)
    try:
        yield runtime, ids
    finally:
        runtime.dispose()


def _payload() -> dict:
    return {
        "headline": "Senior product manager",
        "summary": "Развиваю B2B-продукты и продуктовые команды.",
        "contacts": {
            "contact_email": "career@example.test",
            "phone": "+375 29 000-00-00",
            "telegram": "@career_owner",
            "portfolio_url": "https://portfolio.example.test/work",
            "linkedin_url": "https://profile.example.test/career",
        },
        "goals": {
            "target_roles": ["Head of Product", "Product Lead"],
            "industries": ["SaaS", "FinTech"],
            "employment_types": ["full"],
            "work_formats": ["remote", "hybrid"],
        },
        "geography": {
            "current_location": "Минск, Беларусь",
            "preferred_locations": ["Минск", "Удалённо"],
            "relocation": "consider",
        },
        "salary": {
            "minimum": "350000",
            "maximum": "500000",
            "currency": "RUB",
            "period": "month",
            "tax_mode": "net",
        },
        "skills": [
            {"name": "Product discovery", "level": "advanced"},
            {"name": "SQL", "level": "intermediate"},
        ],
        "employment": [
            {
                "company": "Example Labs",
                "position": "Product Lead",
                "start": "2023-02",
                "end": "",
                "current": "1",
                "description": "Запустил два продукта и выстроил discovery-процесс.",
            }
        ],
        "achievements": [
            {
                "title": "Рост выручки продукта",
                "year": "2025",
                "description": "Увеличил ARR на 45%.",
            }
        ],
        "education": [
            {
                "institution": "БГУ",
                "degree": "Бакалавр",
                "field": "Экономика",
                "start_year": "2014",
                "end_year": "2018",
                "description": "",
            }
        ],
        "languages": [
            {"name": "Русский", "level": "native"},
            {"name": "Английский", "level": "b2"},
        ],
    }


def test_profile_service_allows_partial_profiles_and_versions_material_changes(profile_runtime):
    runtime, (first_user_id, _second_user_id) = profile_runtime
    service = CareerProfileService(CareerProfileRepository(runtime))

    empty = service.get(first_user_id)
    assert empty.exists is False
    assert empty.version == 0
    assert empty.completion_percent == 0

    created = service.save(
        user_id=first_user_id,
        payload={"headline": "Data analyst"},
        expected_version=0,
        now=100,
    )
    assert created.changed is True
    assert created.profile.version == 1
    assert created.profile.headline == "Data analyst"
    assert created.profile.completion_percent == 10

    unchanged = service.save(
        user_id=first_user_id,
        payload={"headline": "Data analyst"},
        expected_version=1,
        now=101,
    )
    assert unchanged.changed is False
    assert unchanged.profile.version == 1

    updated = service.save(
        user_id=first_user_id,
        payload=_payload(),
        expected_version=1,
        now=102,
    )
    assert updated.changed is True
    assert updated.profile.version == 2
    assert updated.profile.completion_percent > 70
    assert updated.profile.goals["target_roles"] == ["Head of Product", "Product Lead"]
    assert updated.profile.employment[0]["current"] is True

    history = service.list_versions(user_id=first_user_id)
    assert [item.version for item in history] == [2, 1]
    assert "core" in history[1].changed_sections
    assert {"core", "contacts", "goals", "skills", "employment"}.issubset(
        set(history[0].changed_sections)
    )

    with runtime.session() as session:
        assert session.scalar(select(func.count()).select_from(CareerProfileVersion)) == 2


def test_profile_service_is_owner_scoped_and_rejects_stale_editor(profile_runtime):
    runtime, (first_user_id, second_user_id) = profile_runtime
    service = CareerProfileService(CareerProfileRepository(runtime))
    saved = service.save(
        user_id=first_user_id,
        payload={"headline": "QA lead"},
        expected_version=0,
    )
    assert saved.profile.version == 1

    assert service.get(second_user_id).exists is False
    assert service.get_version(user_id=second_user_id, version=1) is None

    service.save(
        user_id=first_user_id,
        payload={"headline": "QA director"},
        expected_version=1,
    )
    with pytest.raises(ProfileConflictError, match="изменён в другой сессии"):
        service.save(
            user_id=first_user_id,
            payload={"headline": "Stale overwrite"},
            expected_version=1,
        )


def test_profile_service_rejects_invalid_structured_facts(profile_runtime):
    runtime, (first_user_id, _second_user_id) = profile_runtime
    service = CareerProfileService(CareerProfileRepository(runtime))

    invalid_payloads = [
        {
            "salary": {
                "minimum": 500,
                "maximum": 100,
                "currency": "RUB",
            }
        },
        {
            "skills": [
                {"name": "Python", "level": "advanced"},
                {"name": "python", "level": "basic"},
            ]
        },
        {
            "employment": [
                {
                    "company": "Example",
                    "position": "Engineer",
                    "start": "2025-05",
                    "end": "2024-01",
                    "current": False,
                }
            ]
        },
        {"contacts": {"portfolio_url": "javascript:alert(1)"}},
    ]
    for payload in invalid_payloads:
        with pytest.raises(ProfileValidationError):
            service.save(
                user_id=first_user_id,
                payload=payload,
                expected_version=0,
            )
