from flask import current_app, jsonify

from . import scraper_bp


def get_scraper_service():
    return current_app.extensions["scraper_service"]


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
    return jsonify(get_scraper_service().status())
