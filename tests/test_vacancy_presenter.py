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
