"""Consent-page layout and signed-form rendering regressions (no provider/DB)."""
from html.parser import HTMLParser
from pathlib import Path
import re

from jinja2 import Environment, DictLoader, FileSystemLoader, ChoiceLoader, select_autoescape
import pytest

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / 'static/legal001-consent.css'


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.main_classes = set()
        self.links = []
        self.forms = []
        self.form = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'main':
            self.main_classes = set(attrs.get('class', '').split())
        if tag == 'link':
            self.links.append(attrs)
        if tag == 'form':
            self.form = {'action': attrs.get('action'), 'method': attrs.get('method'), 'inputs': []}
            self.forms.append(self.form)
        if tag == 'input' and self.form is not None:
            self.form['inputs'].append(attrs)

    def handle_endtag(self, tag):
        if tag == 'form':
            self.form = None


@pytest.mark.parametrize('state', ['none', 'accepted', 'withdrawn', 'conflict'])
def test_page_loads_scoped_layout_without_changing_signed_forms(state):
    # Use the real child template and a minimal base; browser evidence separately
    # renders the full base and all shared CSS at the reported viewport widths.
    env = Environment(loader=ChoiceLoader([
        DictLoader({'base.html': '{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),
        FileSystemLoader(ROOT / 'templates'),
    ]), autoescape=select_autoescape(['html']))
    env.globals.update(csrf_token=lambda: 'synthetic-csrf',
        url_for=lambda endpoint, **kw: '/static/' + kw['filename'] if endpoint == 'static' else '/' + endpoint)
    record = {'id': '00000000-0000-0000-0000-000000000001', 'revision': 1, 'cycle': 1,
              'status': 'withdrawn' if state == 'withdrawn' else 'accepted',
              'accepted_at_iso': '2000-01-01T00:00:00+00:00',
              'withdrawn_at_iso': '2000-01-01T00:01:00+00:00' if state == 'withdrawn' else None}
    if state == 'withdrawn':
        record['revision'] = 2
    current = None if state == 'none' else record
    markup = env.get_template('privacy/ai_consent.html').render(
        current=current, history=[current] if current else [], consent_form_token='synthetic-form-signature',
        policy={'display_label': 'LEGAL-001 DRAFT / PLACEHOLDER REQUIRED', 'release_state': 'DRAFT',
                'version': 'synthetic-policy', 'document_hash': 'a' * 64, 'production_active': False},
        error='<script>not executable</script>' if state == 'conflict' else None,
    )
    doc = Document()
    doc.feed(markup)
    assert 'ai-consent-page' in doc.main_classes
    assert any(link.get('href') == '/static/legal001-consent.css?v=1' and
               link.get('rel') == 'stylesheet' for link in doc.links)
    assert len(doc.forms) == 1
    form = doc.forms[0]
    action = 'withdraw' if state in ('accepted', 'conflict') else 'accept'
    assert form['action'] == '/privacy_controls.' + action + '_ai_consent'
    assert form['method'] == 'post'
    inputs = form['inputs']
    assert len(inputs) == 4 and all(item['type'] == 'hidden' for item in inputs)
    assert {item['name']: item['value'] for item in inputs} == {
        'csrf_token': 'synthetic-csrf', 'consent_form_token': 'synthetic-form-signature',
        'expected_record_id': current['id'] if current else '',
        'expected_revision': str(current['revision']) if current else '0',
    }
    assert 'DRAFT / PLACEHOLDER REQUIRED' in markup
    if state == 'conflict':
        assert '<script>not executable</script>' not in markup
        assert '&lt;script&gt;not executable&lt;/script&gt;' in markup


def test_document_grid_is_single_column_and_long_tokens_wrap():
    css = CSS_PATH.read_text(encoding='utf-8')
    grid = re.search(r'\.ai-consent-page \.privacy-control-card,\s*'
                     r'\.ai-consent-page \.privacy-retention-card\s*\{([^}]+)\}', css).group(1)
    assert 'grid-template-columns: minmax(0, 1fr);' in grid
    assert 'align-items: start;' in grid
    assert 'min-width: 0;' in css and 'overflow-wrap: anywhere;' in css
    assert 'white-space: normal;' in css
    assert '!important' not in css and 'overflow: hidden' not in css


def test_every_style_rule_is_scoped_and_privacy_center_is_unchanged():
    css = re.sub(r'/\*.*?\*/', '', CSS_PATH.read_text(encoding='utf-8'), flags=re.S)
    selectors = re.findall(r'([^{}]+)\{', css)
    for group in selectors:
        group = group.strip()
        if group.startswith('@media'):
            continue
        assert all(selector.strip().startswith('.ai-consent-page ') for selector in group.split(',')), group
    center = (ROOT / 'templates/privacy/center.html').read_text(encoding='utf-8')
    assert 'legal001-consent.css' not in center and 'ai-consent-page' not in center
