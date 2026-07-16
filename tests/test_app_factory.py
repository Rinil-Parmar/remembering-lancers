import pytest

from remembering_lancers import create_app


def test_app_factory_registers_expected_routes(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}

    assert "web.dashboard" in endpoints
    assert "web.health" in endpoints
    assert "web.download_csv" in endpoints
    assert "api.get_obituaries" in endpoints
    assert "scraper.start_scrape" in endpoints
    assert app.extensions["scraper_service"].status() == {
        "scraping_active": False,
        "last_scrape_time": None,
    }


def test_production_config_requires_secret_and_database_url(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="Missing required production"):
        create_app("production")


def test_production_config_rejects_placeholder_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "replace-with-a-secure-random-secret")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/remembering_lancers",
    )

    with pytest.raises(RuntimeError, match="default placeholder"):
        create_app("production")
