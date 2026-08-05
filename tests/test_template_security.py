from __future__ import annotations

import re
from pathlib import Path


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
SCRIPT_OPENING_TAG = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
POST_FORM = re.compile(
    r"<form\b(?=[^>]*\bmethod=[\"']post[\"'])[^>]*>(.*?)</form>",
    re.IGNORECASE | re.DOTALL,
)
INLINE_EVENT_HANDLER = re.compile(
    r"<[^>]+\son(?:click|change|submit|load|error|input|focus|blur|mouseover|mouseout|keydown|keyup|touchstart|touchend)\s*=",
    re.IGNORECASE,
)


def _templates() -> list[Path]:
    return sorted(TEMPLATES_DIR.rglob("*.html"))


def test_every_script_tag_uses_the_request_nonce():
    failures: list[str] = []
    for path in _templates():
        text = path.read_text(encoding="utf-8")
        for tag in SCRIPT_OPENING_TAG.findall(text):
            if 'nonce="{{ csp_nonce }}"' not in tag:
                failures.append(f"{path.relative_to(TEMPLATES_DIR)}: {tag}")

    assert not failures, "Script tags without CSP nonce:\n" + "\n".join(failures)


def test_post_forms_include_a_csrf_token():
    failures: list[str] = []
    for path in _templates():
        text = path.read_text(encoding="utf-8")
        for form_body in POST_FORM.findall(text):
            if 'name="csrf_token"' not in form_body:
                failures.append(str(path.relative_to(TEMPLATES_DIR)))

    assert not failures, "POST forms without CSRF token: " + ", ".join(failures)


def test_templates_do_not_use_inline_event_handlers():
    failures: list[str] = []
    for path in _templates():
        text = path.read_text(encoding="utf-8")
        if INLINE_EVENT_HANDLER.search(text):
            failures.append(str(path.relative_to(TEMPLATES_DIR)))

    assert not failures, "Inline event handlers violate CSP: " + ", ".join(failures)
