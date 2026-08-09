from services.vacancy_presenter import (
    format_published_at,
    format_salary,
    localize_label,
    present_vacancy,
)


def test_format_salary_supports_ranges_and_currency_symbols():
    assert format_salary({"salary_from": 1000, "salary_to": 2000, "currency": "USD"}) == "$1 000–2 000"
    assert format_salary({"salary_from": 80000, "salary_to": None, "currency": "RUB"}) == "от 80 000 ₽"
    assert format_salary({"salary_from": None, "salary_to": None, "currency": "RUB"}) == ""


def test_localize_label_and_date_formatting():
    assert localize_label("Full-time") == "Полная занятость"
    assert localize_label("Hybrid") == "Гибрид"
    assert format_published_at("2026-08-03T08:30:00+00:00") == "03.08.2026"
    assert format_published_at("not-a-date") == ""


def test_present_vacancy_cleans_html_and_builds_unique_labels():
    result = present_vacancy(
        {
            "title": "<b>Python developer</b>",
            "company": " ACME &amp; Co ",
            "location": "Москва",
            "description": "<p>Develop APIs</p>",
            "requirements": "<ul><li>SQL</li></ul>",
            "schedule": "Remote",
            "employment": "Full time",
            "experience": "No experience",
            "remote": True,
            "salary_from": 100000,
            "currency": "RUB",
            "published_at": "2026-08-03T08:30:00Z",
        }
    )

    assert result["title"] == "Python developer"
    assert result["company"] == "ACME & Co"
    assert result["description"] == "Develop APIs"
    assert result["requirements"] == "SQL"
    assert result["meta_labels"] == [
        "Москва",
        "Удалённо",
        "Полная занятость",
        "Без опыта",
    ]


def test_present_vacancy_exposes_grouped_sources_and_stable_save_key():
    result = present_vacancy(
        {
            "source": "hh",
            "source_title": "HeadHunter",
            "external_id": "hh-1",
            "title": "Python developer",
            "company": "ACME",
            "url": "https://hh.test/1",
            "dedup_group_id": "dedup-v1-test",
            "source_records": [
                {
                    "source": "hh",
                    "source_title": "HeadHunter",
                    "external_id": "hh-1",
                    "url": "https://hh.test/1",
                    "published_at": "2026-08-08T10:00:00Z",
                },
                {
                    "source": "trudvsem",
                    "source_title": "Работа России",
                    "external_id": "tv-1",
                    "url": "https://trudvsem.test/1",
                    "published_at": "2026-08-08T09:00:00Z",
                },
            ],
        }
    )

    assert result["source_count"] == 2
    assert result["source_display"] == "2 источника"
    assert [row["source"] for row in result["source_links"]] == ["hh", "trudvsem"]
    assert result["save_key"] == "dedup-v1-test"


def test_present_vacancy_uses_correct_russian_source_count_form():
    source_records = [
        {
            "source": f"source-{index}",
            "source_title": f"Источник {index}",
            "external_id": str(index),
            "url": f"https://example.test/{index}",
        }
        for index in range(5)
    ]
    result = present_vacancy(
        {
            "source": "source-0",
            "title": "Role",
            "company": "ACME",
            "source_records": source_records,
        }
    )
    assert result["source_display"] == "5 источников"
