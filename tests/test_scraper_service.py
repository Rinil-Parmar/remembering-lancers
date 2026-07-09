import time
from datetime import datetime

from remembering_lancers.extensions import db
from remembering_lancers.models import ScrapeRun
from remembering_lancers.scraper import runner
from remembering_lancers.scraper.service import ScraperService


def test_scraper_service_lifecycle(client, app):
    service = app.extensions["scraper_service"]
    service.runner = lambda stop_event: stop_event.wait(2)

    initial = client.get("/scrape_status")
    assert initial.get_json() == {
        "scraping_active": False,
        "last_scrape_time": None,
        "current_run": None,
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


def test_scrape_status_includes_latest_run(client, app):
    with app.app_context():
        db.session.add(
            ScrapeRun(
                status="running",
                started_at=datetime(2026, 7, 1, 11, 30),
                city="windsorstar",
                search_keyword="UWindsor",
                page_number=4,
                saved_count=7,
                skipped_count=12,
                duplicate_count=3,
            )
        )
        db.session.commit()

    status = client.get("/scrape_status").get_json()

    assert status["scraping_active"] is False
    assert status["current_run"]["status"] == "running"
    assert status["current_run"]["city"] == "windsorstar"
    assert status["current_run"]["search_keyword"] == "UWindsor"
    assert status["current_run"]["page_number"] == 4
    assert status["current_run"]["saved_count"] == 7
    assert status["current_run"]["skipped_count"] == 12
    assert status["current_run"]["duplicate_count"] == 3


def test_scrape_status_displays_listing_scan_label(client, app):
    with app.app_context():
        db.session.add(
            ScrapeRun(
                status="running",
                started_at=datetime(2026, 7, 1, 13, 1),
                city="windsorstar",
                search_keyword="__listing__",
                page_number=18,
            )
        )
        db.session.commit()

    status = client.get("/scrape_status").get_json()

    assert status["current_run"]["search_keyword"] == "Listing scan"
    assert status["current_run"]["search_keyword_raw"] == "__listing__"


def test_scraper_service_finishes_background_run(client, app):
    service = app.extensions["scraper_service"]
    service.runner = lambda stop_event: None

    response = client.post("/start_scrape")
    time.sleep(0.1)
    status = client.get("/scrape_status").get_json()

    assert response.status_code == 200
    assert status["scraping_active"] is False
    assert status["last_scrape_time"] is not None


def test_scraper_service_loads_packaged_runner():
    assert ScraperService._load_runner() is runner.main
