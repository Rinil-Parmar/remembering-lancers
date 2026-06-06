from flask import current_app, render_template

from . import web_bp
from ..models import DistinctObituary


@web_bp.route("/")
def dashboard():
    total_alumni = DistinctObituary.query.distinct(DistinctObituary.name).count()
    total_obituaries = DistinctObituary.query.count()
    total_cities = len(
        {
            obituary.city
            for obituary in DistinctObituary.query.all()
            if obituary.city
        }
    )

    scraper_state = current_app.extensions.get("scraper_state")
    scraping_active = (
        not scraper_state["stop_event"].is_set()
        if scraper_state
        else False
    )

    return render_template(
        "dashboard.html",
        total_alumni=total_alumni,
        total_obituaries=total_obituaries,
        total_cities=total_cities,
        scraping_active=scraping_active,
    )


@web_bp.route("/obituary/<int:obituary_id>")
def obituary_detail(obituary_id):
    obituary = DistinctObituary.query.get_or_404(obituary_id)
    return render_template("obituary_detail.html", obituary=obituary)


@web_bp.route("/about")
def about():
    return render_template("about.html")
