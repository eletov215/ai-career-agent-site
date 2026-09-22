"""Provider-neutral LEGAL-001 consent policy contract."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AIConsentPolicy:
    consent_type: str
    scope: str
    version: str
    document_hash: str
    provider: str
    purpose: str
    release_state: str
    data_categories: tuple[str, ...]
    display_label: str

    @property
    def production_active(self) -> bool:
        return self.release_state == "ACTIVE"
