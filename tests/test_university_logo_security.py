from __future__ import annotations

import base64

import pytest

from services import university_logo


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        url: str = "https://public.example/resource",
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}
        self._body = body
        self.encoding = "utf-8"
        self.closed = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def close(self) -> None:
        self.closed = True

    def raise_for_status(self) -> None:
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, _chunk_size: int):
        if self._body:
            yield self._body


def test_safe_url_rejects_credentials_nonstandard_ports_and_private_hosts(monkeypatch):
    monkeypatch.setattr(university_logo, "_is_public_host", lambda host: host == "public.example")

    assert university_logo._safe_http_url("https://public.example/logo.png") is not None
    assert university_logo._safe_http_url("https://user:password@public.example/logo.png") is None
    assert university_logo._safe_http_url("https://public.example:8443/logo.png") is None
    assert university_logo._safe_http_url("http://127.0.0.1/logo.png") is None
    assert university_logo._safe_http_url("file:///etc/passwd") is None


def test_redirect_target_is_validated_before_following(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        university_logo,
        "_is_public_host",
        lambda host: host == "public.example",
    )

    def fake_get(url, **_kwargs):
        calls.append(url)
        return FakeResponse(
            status_code=302,
            url=url,
            headers={"Location": "http://127.0.0.1/internal"},
        )

    monkeypatch.setattr(university_logo.requests, "get", fake_get)

    with pytest.raises(ValueError, match="перенаправление"):
        university_logo._request("https://public.example/start", stream=True)

    assert calls == ["https://public.example/start"]


def test_image_data_url_requires_matching_safe_file_signature(monkeypatch):
    unsafe_svg = FakeResponse(
        headers={"Content-Type": "image/svg+xml"},
        body=b"<svg xmlns='http://www.w3.org/2000/svg'><script/></svg>",
    )
    monkeypatch.setattr(university_logo, "_request", lambda *_args, **_kwargs: unsafe_svg)

    with pytest.raises(ValueError, match="безопасным изображением"):
        university_logo._image_to_data_url("https://public.example/logo.svg")

    fake_png = FakeResponse(
        headers={"Content-Type": "image/png"},
        body=b"\x89PNG\r\n\x1a\n" + b"safe-test-image",
    )
    monkeypatch.setattr(university_logo, "_request", lambda *_args, **_kwargs: fake_png)

    data_url, final_url = university_logo._image_to_data_url(
        "https://public.example/logo.png"
    )

    assert final_url == fake_png.url
    assert data_url.startswith("data:image/png;base64,")
    assert base64.b64decode(data_url.split(",", 1)[1]).startswith(b"\x89PNG")


def test_limited_reader_closes_response_when_external_body_is_too_large():
    response = FakeResponse(body=b"x" * 17)

    with pytest.raises(ValueError, match="слишком большой"):
        university_logo._read_limited_body(response, 16)

    assert response.closed is True
