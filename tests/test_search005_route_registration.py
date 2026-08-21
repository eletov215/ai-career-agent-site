import pytest


def test_search005_routes_registered():
    pytest.importorskip("flask")
    from app import app

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/admin/sources" in rules
    assert "/api/admin/sources" in rules
