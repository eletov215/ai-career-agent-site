"""Narrow settings view for the fixed-source, admin-only SITE QA runtime."""
from __future__ import annotations

from dataclasses import dataclass

from services.ai.settings import AISettings


@dataclass(frozen=True, slots=True)
class SiteQASettingsGate:
    """Preserve every shared gate except the historical 24-hour wait."""

    settings: AISettings

    @property
    def api_key(self) -> str:
        return self.settings.api_key

    @property
    def folder_id(self) -> str:
        return self.settings.folder_id

    @property
    def model_uri(self) -> str:
        return self.settings.model_uri

    def gate(self, now: int) -> str | None:
        reason = self.settings.gate(now)
        return None if reason == "no_logging_wait" else reason
