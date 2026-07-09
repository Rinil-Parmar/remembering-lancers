from flask import current_app, jsonify

from ..models import ScrapeRun
from . import scraper_bp

LISTING_SCAN_STATE_KEYWORD = "__listing__"
LISTING_SCAN_DISPLAY_LABEL = "Listing scan"


def get_scraper_service():
    return current_app.extensions["scraper_service"]


def display_search_keyword(search_keyword):
    if search_keyword == LISTING_SCAN_STATE_KEYWORD:
        return LISTING_SCAN_DISPLAY_LABEL
    return search_keyword


def serialize_scrape_run(scrape_run):
    if not scrape_run:
        return None

    return {
        "id": scrape_run.id,
        "status": scrape_run.status,
        "started_at": (
            scrape_run.started_at.isoformat() if scrape_run.started_at else None
        ),
        "finished_at": (
            scrape_run.finished_at.isoformat() if scrape_run.finished_at else None
        ),
        "city": scrape_run.city,
        "search_keyword": display_search_keyword(scrape_run.search_keyword),
        "search_keyword_raw": scrape_run.search_keyword,
        "page_number": scrape_run.page_number,
        "saved_count": scrape_run.saved_count,
        "skipped_count": scrape_run.skipped_count,
        "duplicate_count": scrape_run.duplicate_count,
        "error_message": scrape_run.error_message,
    }


def latest_scrape_run():
    return ScrapeRun.query.order_by(ScrapeRun.id.desc()).first()


@scraper_bp.post("/start_scrape")
def start_scrape():
    result, status_code = get_scraper_service().start()
    return jsonify(result), status_code


@scraper_bp.post("/stop_scrape")
def stop_scrape():
    result, status_code = get_scraper_service().stop()
    return jsonify(result), status_code


@scraper_bp.get("/scrape_status")
def scrape_status():
    status = get_scraper_service().status()
    status["current_run"] = serialize_scrape_run(latest_scrape_run())
    return jsonify(status)
