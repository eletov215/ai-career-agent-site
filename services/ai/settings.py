"""Deployment gates. Safe defaults require no provider secrets at startup."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping
import re

@dataclass(frozen=True, slots=True)
class AISettings:
    enabled: bool = False
    kill_switch: bool = True
    synthetic_access_enabled: bool = False
    api_key: str = field(default="", repr=False)
    folder_id: str = field(default="", repr=False)
    model_uri: str = field(default="", repr=False)
    no_logging_disabled_at: int | None = None

    @classmethod
    def from_environ(cls, source: Mapping[str, str]) -> "AISettings":
        def flag(key: str, default: bool) -> bool:
            raw = source.get(key, "1" if default else "0").strip().lower()
            if raw not in {"1", "0", "true", "false"}:
                raise ValueError(f"Invalid boolean configuration: {key}")
            return raw in {"1", "true"}
        stamp = source.get("AI_NO_LOGGING_DISABLED_AT", "").strip()
        disabled_at = None
        if stamp:
            try:
                value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if value.tzinfo is None:
                    raise ValueError
                disabled_at = int(value.astimezone(timezone.utc).timestamp())
            except (ValueError, OverflowError):
                raise ValueError("AI_NO_LOGGING_DISABLED_AT must be an aware ISO timestamp") from None
        settings = cls(flag("AI_ENABLED", False), flag("AI_KILL_SWITCH", True),
                       flag("AI_SYNTHETIC_ACCESS_ENABLED", False),
                       source.get("AI_YANDEX_API_KEY", ""), source.get("AI_YANDEX_FOLDER_ID", ""),
                       source.get("AI_YANDEX_MODEL_URI", ""), disabled_at)
        # These values must be safe for HTTP headers. Reject without echoing values.
        for value in (settings.api_key, settings.folder_id, settings.model_uri):
            if len(value) > 4096 or any(ord(c) < 32 or ord(c) > 126 for c in value):
                raise ValueError("Invalid AI provider credential configuration")
        return settings

    def gate(self, now: int) -> str | None:
        if not self.enabled or self.kill_switch:
            return "runtime_not_activated"
        if not self.synthetic_access_enabled:
            return "synthetic_access_disabled"
        if not self.api_key or not re.fullmatch(r"[A-Za-z0-9_-]{3,128}", self.folder_id):
            return "provider_not_configured"
        # Pin the qualified family and folder; no arbitrary endpoint/model from clients.
        if self.model_uri != f"gpt://{self.folder_id}/aliceai-llm/latest":
            return "provider_not_configured"
        if self.no_logging_disabled_at is None or not 86400 <= now-self.no_logging_disabled_at:
            return "no_logging_wait"
        return None
