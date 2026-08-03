from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import requests


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        payload: Any = None,
        *,
        text: str | None = None,
        headers: dict[str, str] | None = None,
        url: str = "https://example.test/api",
        request_headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.url = url
        self.request = SimpleNamespace(headers=request_headers or {})
        if text is not None:
            self.text = text
        else:
            try:
                self.text = json.dumps(payload, ensure_ascii=False)
            except TypeError:
                self.text = ""
        self.content = self.text.encode("utf-8")

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} response",
                response=self,
            )
