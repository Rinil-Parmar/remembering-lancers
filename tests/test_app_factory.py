def test_app_factory_registers_expected_routes(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}

    assert "web.dashboard" in endpoints
    assert "web.download_csv" in endpoints
    assert "api.get_obituaries" in endpoints
    assert "scraper.start_scrape" in endpoints
    assert app.extensions["scraper_service"].status() == {
        "scraping_active": False,
        "last_scrape_time": None,
    }
