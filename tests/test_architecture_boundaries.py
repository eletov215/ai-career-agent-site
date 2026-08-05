from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_flask_routes_depend_on_storage_services_not_orm_or_repositories():
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "StorageServices" in source
    assert "from repositories" not in source
    assert "from sqlalchemy" not in source
    assert "import sqlalchemy" not in source
    assert "DATABASE.session(" not in source
    assert "DATABASE.connect(" not in source
    assert "SuperJobAccount" not in source
    assert "HeadHunterAccount" not in source


def test_vacancy_service_delegates_queries_to_repository_layer():
    source = (ROOT / "services" / "vacancy_store.py").read_text(encoding="utf-8")

    assert "VacancyRepository" in source
    assert "select(" not in source
    assert "session.execute" not in source


def test_repository_layer_is_the_only_application_layer_importing_models():
    application_files = [
        ROOT / "app.py",
        *sorted((ROOT / "services").glob("*.py")),
        *sorted((ROOT / "domain").glob("*.py")),
    ]
    violations: list[str] = []
    for path in application_files:
        source = path.read_text(encoding="utf-8")
        if "from models" in source or "import models" in source:
            violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_inline_scripts_are_nonce_protected_and_event_handlers_are_absent():
    import re

    violations: list[str] = []
    event_handler_pattern = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
    for path in sorted((ROOT / "templates").glob("*.html")):
        source = path.read_text(encoding="utf-8")
        for tag in re.findall(r"<script\b[^>]*>", source, flags=re.IGNORECASE):
            if 'nonce="{{ csp_nonce }}"' not in tag:
                violations.append(f"{path.name}: missing nonce in {tag}")
        if event_handler_pattern.search(source):
            violations.append(f"{path.name}: inline event handler")

    assert violations == []
