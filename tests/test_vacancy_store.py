from datetime import datetime, timedelta, timezone

from services.vacancy_store import VacancyStore


def vacancy(
    external_id: str,
    *,
    title: str,
    currency: str = "RUB",
    remote: bool = False,
    salary_from: int | None = None,
    location: str = "Москва",
    employment: str = "Полная занятость",
    experience: str = "Без опыта",
    published_at: str | None = None,
):
    return {
        "source": "trudvsem",
        "external_id": external_id,
        "title": title,
        "company": "Test Company",
        "salary_from": salary_from,
        "salary_to": None,
        "currency": currency,
        "location": location,
        "remote": remote,
        "schedule": "Удалённая работа" if remote else "Полный день",
        "employment": employment,
        "experience": experience,
        "description": f"Описание {title}",
        "requirements": "Python SQL",
        "published_at": published_at or datetime.now(timezone.utc).isoformat(),
        "url": f"https://example.test/{external_id}",
    }


def make_store(tmp_path):
    store = VacancyStore(tmp_path / "vacancies.db")
    store.init()
    return store


def test_upsert_search_count_and_update(tmp_path):
    store = make_store(tmp_path)
    assert store.upsert_many(
        [
            vacancy("1", title="Python developer", remote=True, salary_from=150000),
            vacancy("2", title="Data analyst", currency="USD", salary_from=2500),
            {"source": "", "external_id": "missing-source", "title": "ignored"},
        ]
    ) == 2

    assert store.count(keyword="", sources=["trudvsem"], period_days=30) == 2
    python_items = store.search(
        keyword="Python",
        sources=["trudvsem"],
        remote_only=True,
        salary_from=100000,
        period_days=30,
    )
    assert [item["external_id"] for item in python_items] == ["1"]

    store.upsert_many([vacancy("1", title="Senior Python developer", remote=True, salary_from=180000)])
    assert store.count(keyword="", sources=["trudvsem"], period_days=30) == 2
    updated = store.search(keyword="Senior", sources=["trudvsem"], period_days=30)
    assert updated[0]["salary_from"] == 180000


def test_currency_aliases_and_salary_only_filter(tmp_path):
    store = make_store(tmp_path)
    store.upsert_many(
        [
            vacancy("rub", title="RUB vacancy", currency="RUR", salary_from=100000),
            vacancy("byn", title="BYN vacancy", currency="BYR", salary_from=3000),
            vacancy("none", title="No salary", currency="RUB", salary_from=None),
        ]
    )

    rub = store.search(keyword="", sources=["trudvsem"], currency="RUB", period_days=30)
    byn = store.search(keyword="", sources=["trudvsem"], currency="BYN", period_days=30)
    salaried = store.search(
        keyword="",
        sources=["trudvsem"],
        salary_only=True,
        period_days=30,
    )

    assert {item["external_id"] for item in rub} == {"rub", "none"}
    assert {item["external_id"] for item in byn} == {"byn"}
    assert {item["external_id"] for item in salaried} == {"rub", "byn"}


def test_period_region_employment_and_experience_filters(tmp_path):
    store = make_store(tmp_path)
    old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    store.upsert_many(
        [
            vacancy(
                "fresh",
                title="Инженер",
                location="Казань",
                employment="Полная занятость",
                experience="Опыт 1-3 года",
            ),
            vacancy("old", title="Старая вакансия", published_at=old_date),
        ]
    )

    items = store.search(
        keyword="",
        sources=["trudvsem"],
        region="Казань",
        employment="full",
        experience="between_1_and_3",
        period_days=30,
    )
    assert [item["external_id"] for item in items] == ["fresh"]
    assert store.source_age_seconds("trudvsem") is not None
    assert store.source_age_seconds("unknown") is None
