import time


def test_scraper_service_lifecycle(client, app):
    service = app.extensions["scraper_service"]
    service.runner = lambda stop_event: stop_event.wait(2)

    initial = client.get("/scrape_status")
    assert initial.get_json() == {
        "scraping_active": False,
        "last_scrape_time": None,
    }

    started = client.post("/start_scrape")
    duplicate = client.post("/start_scrape")
    dashboard = client.get("/").get_data(as_text=True)
    stopped = client.post("/stop_scrape")
    time.sleep(0.1)
    final = client.get("/scrape_status")

    assert started.status_code == 200
    assert started.get_json()["scraping_active"] is True
    assert duplicate.status_code == 400
    assert "let scrapingActive = true" in dashboard
    assert stopped.status_code == 200
    assert final.get_json()["scraping_active"] is False
    assert "+00:00" in final.get_json()["last_scrape_time"]


def test_scraper_service_finishes_background_run(client, app):
    service = app.extensions["scraper_service"]
    service.runner = lambda stop_event: None

    response = client.post("/start_scrape")
    time.sleep(0.1)
    status = client.get("/scrape_status").get_json()

    assert response.status_code == 200
    assert status["scraping_active"] is False
    assert status["last_scrape_time"] is not None
