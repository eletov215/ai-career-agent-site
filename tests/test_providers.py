from datetime import datetime, timezone

import pytest
import requests

from services.hh_provider import HeadHunterProvider
from services.reed_provider import ReedProvider
from services.search_filters import VacancySearchFilters
from services.superjob_provider import SuperJobProvider
from services.trudvsem_provider import TrudvsemProvider
from tests.fakes import FakeResponse


def test_hh_success_normalizes_result_and_omits_empty_text(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse(
            200,
            {
                "items": [
                    {
                        "id": "hh-1",
                        "name": "Python developer",
                        "employer": {"name": "ACME"},
                        "salary": {"from": 150000, "to": 200000, "currency": "RUR"},
                        "area": {"name": "Москва"},
                        "schedule": {"id": "remote", "name": "Удалённая работа"},
                        "employment": {"name": "Полная занятость"},
                        "experience": {"name": "От 1 года до 3 лет"},
                        "snippet": {"requirement": "Python", "responsibility": "APIs"},
                        "published_at": "2026-08-03T08:00:00+00:00",
                        "alternate_url": "https://hh.test/1",
                    }
                ],
                "found": 1,
                "page": 0,
                "pages": 1,
            },
            request_headers=kwargs.get("headers"),
        )

    monkeypatch.setattr("services.hh_provider.requests.get", fake_get)
    provider = HeadHunterProvider(
        "https://hh.test/vacancies",
        lambda token: {"Authorization": f"Bearer {token}"},
        lambda: "app-token",
    )
    result = provider.search(filters=VacancySearchFilters(), page=0)

    assert result.error is None
    assert result.total == 1
    assert result.items[0]["currency"] == "RUB"
    assert result.items[0]["remote"] is True
    assert "text" not in captured["params"]


def test_hh_missing_token_returns_controlled_error():
    provider = HeadHunterProvider("https://hh.test", lambda token: {}, None)
    result = provider.search(filters=VacancySearchFilters(), page=0)
    assert result.items == []
    assert result.error == "HeadHunter временно недоступен."
    assert "HH_APP_TOKEN" not in result.error


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (requests.Timeout("secret-timeout-detail"), "временно не смог выполнить поиск"),
        (ValueError("secret-broken-json"), "некорректный ответ"),
    ],
)
def test_hh_transport_and_payload_errors_are_controlled(monkeypatch, failure, expected):
    if isinstance(failure, requests.RequestException):
        monkeypatch.setattr("services.hh_provider.requests.get", lambda *args, **kwargs: (_ for _ in ()).throw(failure))
    else:
        monkeypatch.setattr(
            "services.hh_provider.requests.get",
            lambda *args, **kwargs: FakeResponse(200, failure),
        )
    provider = HeadHunterProvider("https://hh.test", lambda token: {}, lambda: "token")
    result = provider.search(filters=VacancySearchFilters(keyword="python"), page=0)
    error = result.error or ""
    assert expected.casefold() in error.casefold()
    assert "secret-" not in error


def test_hh_403_includes_safe_diagnostic_context(monkeypatch):
    monkeypatch.setattr(
        "services.hh_provider.requests.get",
        lambda *args, **kwargs: FakeResponse(
            403,
            {"errors": [{"type": "forbidden"}]},
            headers={"Server": "ddos-guard", "X-Request-Id": "request-123"},
            text='{"errors":[{"type":"forbidden"}]}',
        ),
    )
    provider = HeadHunterProvider("https://hh.test", lambda token: {}, lambda: "sensitive-value-123")
    result = provider.search(filters=VacancySearchFilters(keyword="python"), page=0)
    assert "403" in result.error
    assert "ddos-guard" not in result.error
    assert "request-123" in result.error
    assert "sensitive-value-123" not in result.error


def test_reed_success_empty_and_error_paths(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    responses = iter(
        [
            FakeResponse(
                200,
                {
                    "results": [
                        {
                            "jobId": 1,
                            "jobTitle": "Data analyst",
                            "employerName": "ACME",
                            "minimumSalary": 30000,
                            "maximumSalary": 40000,
                            "currency": "GBP",
                            "locationName": "London",
                            "jobDescription": "Hybrid analytics role",
                            "date": now,
                            "jobUrl": "https://reed.test/1",
                        }
                    ],
                    "totalResults": 1,
                },
            ),
            FakeResponse(200, {"results": [], "totalResults": 0}),
            FakeResponse(500, {"error": "server"}),
            FakeResponse(200, ValueError("bad json")),
        ]
    )
    monkeypatch.setattr("services.reed_provider.requests.get", lambda *args, **kwargs: next(responses))
    provider = ReedProvider("key", api_url="https://reed.test")

    success = provider.search(filters=VacancySearchFilters(work_format="hybrid", currency="GBP"), page=0)
    empty = provider.search(filters=VacancySearchFilters(), page=0)
    server_error = provider.search(filters=VacancySearchFilters(), page=0)
    malformed = provider.search(filters=VacancySearchFilters(), page=0)

    assert success.items[0]["source"] == "reed"
    assert empty.items == [] and empty.error is None
    assert "временно не смог выполнить поиск" in server_error.error
    assert "500" not in server_error.error
    assert "некорректный ответ" in malformed.error
    assert "bad json" not in malformed.error


def test_reed_timeout_is_returned_as_source_error(monkeypatch):
    monkeypatch.setattr(
        "services.reed_provider.requests.get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("slow")),
    )
    result = ReedProvider("key", api_url="https://reed.test").search(
        filters=VacancySearchFilters(),
        page=0,
    )
    assert result.error == "Reed.co.uk временно не смог выполнить поиск."
    assert "slow" not in result.error


def test_superjob_success_and_failure(monkeypatch):
    response = FakeResponse(
        200,
        {
            "objects": [
                {
                    "id": 10,
                    "profession": "Инженер",
                    "firm_name": "Завод",
                    "payment_from": 100000,
                    "payment_to": 0,
                    "currency": "rub",
                    "town": {"title": "Самара"},
                    "is_remote_work": False,
                    "experience": {"title": "Без опыта"},
                    "link": "https://sj.test/10",
                }
            ],
            "total": 1,
            "more": False,
        },
    )
    monkeypatch.setattr("services.superjob_provider.requests.get", lambda *args, **kwargs: response)
    provider = SuperJobProvider("https://sj.test", lambda token: {}, lambda: "token")
    success = provider.search(filters=VacancySearchFilters(), page=0)
    assert success.items[0]["currency"] == "RUB"

    monkeypatch.setattr(
        "services.superjob_provider.requests.get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("timeout")),
    )
    failed = provider.search(filters=VacancySearchFilters(), page=0)
    assert failed.error == "SuperJob временно не смог выполнить поиск."
    assert "timeout" not in failed.error


def test_trudvsem_fetch_batch_normalizes_valid_and_empty_payloads(monkeypatch):
    provider = TrudvsemProvider("test-agent", request_attempts=1)
    responses = iter(
        [
            FakeResponse(
                200,
                {
                    "status": "200",
                    "results": {
                        "vacancies": [
                            {
                                "vacancy": {
                                    "id": "tv-1",
                                    "job-name": "Инженер",
                                    "company": {"name": "Завод"},
                                    "region": {"name": "Самара"},
                                    "salary_min": 80000,
                                    "currency": "RUB",
                                    "schedule": "Полный рабочий день",
                                    "creation-date": "2026-08-03T08:00:00Z",
                                }
                            }
                        ]
                    },
                },
            ),
            FakeResponse(200, {"status": "200", "results": {"vacancies": []}}),
        ]
    )
    monkeypatch.setattr(provider.session, "get", lambda *args, **kwargs: next(responses))

    items = provider.fetch_batch(offset=1, limit=10)
    empty = provider.fetch_batch(offset=2, limit=10)

    assert items[0]["external_id"] == "tv-1"
    assert items[0]["url"].endswith("/tv-1")
    assert empty == []


@pytest.mark.parametrize(
    "response_or_error",
    [
        requests.Timeout("timeout"),
        FakeResponse(500, {"error": "server"}),
        FakeResponse(200, ValueError("bad json")),
    ],
)
def test_trudvsem_errors_propagate_to_background_controller(monkeypatch, response_or_error):
    provider = TrudvsemProvider("test-agent", request_attempts=1)

    def fake_get(*args, **kwargs):
        if isinstance(response_or_error, BaseException):
            raise response_or_error
        return response_or_error

    monkeypatch.setattr(provider.session, "get", fake_get)
    with pytest.raises((requests.RequestException, ValueError)):
        provider.fetch_batch(offset=1, limit=1)


def test_trudvsem_direct_search_is_blocked():
    provider = TrudvsemProvider("test-agent", request_attempts=1)
    result = provider.search(filters=VacancySearchFilters(), page=0)
    assert result.items == []
    assert "локального кэша" in result.error
