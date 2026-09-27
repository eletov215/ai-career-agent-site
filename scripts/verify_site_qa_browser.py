#!/usr/bin/env python3
"""Localhost-only mock-transport component/browser evidence, never live QA."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('APP_ENV') != 'test':
        raise SystemExit('APP_ENV=test is required')
    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server
    from tests.site_qa_support import build_case
    from routes.letter_site_qa import BASE
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checks = []
    with tempfile.TemporaryDirectory(prefix='aca-site-qa-browser-') as tmp:
        case = build_case(tmp)
        server = make_server('127.0.0.1', 0, case.app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = 'http://127.0.0.1:' + str(server.server_port)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for width in (1348, 1280, 768, 390, 360):
                    page = browser.new_page(viewport={'width': width, 'height': 900})
                    page.route('**/*', lambda route: route.continue_() if urlsplit(route.request.url).hostname == '127.0.0.1' else route.abort())
                    page.goto(origin + BASE)
                    def capture(name):
                        page.locator('.site-qa-shell').wait_for()
                        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                        for box in page.locator('.site-qa-card, .site-qa-notice, .site-qa-warning').all():
                            rect = box.bounding_box()
                            assert rect and rect['x'] >= 0 and rect['x'] + rect['width'] <= width + 1
                        page.screenshot(path=str(args.output_dir / f'{width}-{name}.png'), full_page=True)
                        checks.append({'viewport': width, 'page': name, 'overflow': False})
                    capture('home')
                    page.select_option('[name=language]', 'en')
                    page.locator('form[action$="/prepare"] button').click()
                    path = page.url
                    page.locator('form[action$="/preview"] button').click()
                    assert page.locator('input[type=checkbox]').count() == 0
                    capture('preview')
                    page.locator('#site-qa-generate button').click()
                    page.locator('textarea[name=body]').fill('A manually reviewed synthetic browser test letter.')
                    capture('proposal')
                    page.locator('input[name=confirm]').first.check()
                    page.locator('form[action$="/save"] button').first.click()
                    page.locator('a[href$="/versions/1"]').click()
                    capture('version')
                    with page.expect_download() as download_info:
                        page.locator('a[href$="/export.txt"]').click()
                    download = download_info.value
                    output = args.output_dir / f'{width}-reviewed.txt'
                    download.save_as(output)
                    assert 'A manually reviewed synthetic browser test letter.' in output.read_text(encoding='utf-8-sig')
                    page.goto(path)
                    page.reload()
                    page.close()
                assert len(case.transport.calls) == 5
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            case.db.dispose()
    report = {'scope':'local_component_browser_mock_transport', 'full_application_template':False,
        'production_fonts_verified':False, 'paid_provider_calls':0, 'provider_http_requests':0,
        'adapter_mock_dispatches':5, 'github_sha':os.environ.get('GITHUB_SHA'), 'checks':checks}
    (args.output_dir/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
