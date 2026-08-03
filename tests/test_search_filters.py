from services.search_filters import VacancySearchFilters, canonical_currency


def test_canonical_currency_aliases_and_empty_values():
    assert canonical_currency("rur") == "RUB"
    assert canonical_currency("BYR") == "BYN"
    assert canonical_currency(" usd ") == "USD"
    assert canonical_currency(None) == ""


def test_from_query_normalizes_supported_values():
    filters = VacancySearchFilters.from_query(
        {
            "keyword": "  Python developer ",
            "region": " Москва ",
            "experience": "between_1_and_3",
            "employment": "full",
            "work_format": "remote",
            "currency": "rur",
            "salary_from": "120000",
            "salary_only": "1",
            "period": "14",
            "sort": "salary_desc",
        }
    )

    assert filters.keyword == "Python developer"
    assert filters.region == "Москва"
    assert filters.remote_only is True
    assert filters.work_format == "remote"
    assert filters.currency == "RUB"
    assert filters.salary_from == 120000
    assert filters.salary_only is True
    assert filters.period_days == 14
    assert filters.sort == "salary_desc"


def test_from_query_falls_back_for_invalid_values():
    filters = VacancySearchFilters.from_query(
        {
            "experience": "invalid",
            "employment": "invalid",
            "work_format": "invalid",
            "currency": "XYZ",
            "salary_from": "not-a-number",
            "period": "999",
            "sort": "unknown",
        }
    )

    assert filters.experience == ""
    assert filters.employment == ""
    assert filters.work_format == ""
    assert filters.currency == ""
    assert filters.salary_from is None
    assert filters.period_days == 7
    assert filters.sort == "date"


def test_legacy_remote_flag_selects_remote_work_format():
    filters = VacancySearchFilters.from_query({"remote": "1"})
    assert filters.remote_only is True
    assert filters.work_format == "remote"


def test_negative_salary_becomes_unset():
    filters = VacancySearchFilters.from_query({"salary_from": "-100"})
    assert filters.salary_from is None


def test_query_pairs_preserve_active_filters():
    filters = VacancySearchFilters(
        keyword="аналитик",
        region="Казань",
        experience="between_3_and_6",
        employment="full",
        work_format="hybrid",
        currency="RUB",
        salary_from=90000,
        salary_only=True,
        period_days=30,
        sort="relevance",
    )

    pairs = dict(filters.query_pairs())
    assert pairs == {
        "search": "1",
        "keyword": "аналитик",
        "period": "30",
        "sort": "relevance",
        "region": "Казань",
        "experience": "between_3_and_6",
        "employment": "full",
        "work_format": "hybrid",
        "currency": "RUB",
        "salary_from": "90000",
        "salary_only": "1",
    }
