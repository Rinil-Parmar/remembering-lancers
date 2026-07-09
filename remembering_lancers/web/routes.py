import csv
from datetime import datetime
from io import StringIO

from flask import (
    current_app,
    jsonify,
    redirect,
    Response,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func, text

from . import web_bp
from .formatting import split_donation_items, split_obituary_paragraphs
from ..extensions import db
from ..models import DistinctObituary, Obituary


@web_bp.route("/")
def dashboard():
    total_alumni = db.session.query(
        func.count(func.distinct(DistinctObituary.name))
    ).scalar()
    total_obituaries = DistinctObituary.query.count()
    total_cities = db.session.query(
        func.count(func.distinct(DistinctObituary.city))
    ).filter(
        DistinctObituary.city.isnot(None),
        DistinctObituary.city != "",
    ).scalar()

    scraper_service = current_app.extensions["scraper_service"]

    return render_template(
        "dashboard.html",
        total_alumni=total_alumni,
        total_obituaries=total_obituaries,
        total_cities=total_cities,
        scraping_active=scraper_service.is_active,
    )


@web_bp.route("/obituary/<int:obituary_id>")
def obituary_detail(obituary_id):
    obituary = db.get_or_404(DistinctObituary, obituary_id)
    family_paragraphs = split_obituary_paragraphs(
        obituary.family_information,
        obituary.name,
    )
    donation_items = split_donation_items(obituary.donation_information)
    return render_template(
        "obituary_detail.html",
        obituary=obituary,
        family_paragraphs=family_paragraphs,
        donation_items=donation_items,
    )


@web_bp.route("/about")
def about():
    return render_template("about.html")


@web_bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        current_app.logger.exception("Health check failed")
        return jsonify({"status": "unhealthy", "database": "unavailable"}), 503

    return jsonify({"status": "ok", "database": "ok"}), 200


@web_bp.post("/update_tags/<int:obituary_id>")
def update_tags(obituary_id):
    new_tags = request.form.get("tags")
    if new_tags not in {"new", "updated"}:
        return jsonify({"error": "Invalid tag value"}), 400

    distinct_obituary = db.get_or_404(DistinctObituary, obituary_id)
    distinct_obituary.tags = new_tags
    Obituary.query.filter_by(
        obituary_url=distinct_obituary.obituary_url
    ).update({Obituary.tags: new_tags})
    db.session.commit()

    return redirect(url_for("web.obituary_detail", obituary_id=obituary_id))


CSV_FIELDNAMES = [
    "id",
    "name",
    "first_name",
    "last_name",
    "birth_date",
    "death_date",
    "publication_date",
    "city",
    "province",
    "funeral_home",
    "obituary_url",
    "tags",
    "is_alumni",
    "latitude",
    "longitude",
    "family_information",
    "donation_information",
]


def format_csv_date(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d")


def normalize_csv_text(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def serialize_obituary_for_csv(obituary):
    return {
        "id": obituary.id,
        "name": normalize_csv_text(obituary.name),
        "first_name": normalize_csv_text(obituary.first_name),
        "last_name": normalize_csv_text(obituary.last_name),
        "birth_date": normalize_csv_text(obituary.birth_date),
        "death_date": normalize_csv_text(obituary.death_date),
        "publication_date": format_csv_date(obituary.publication_date),
        "city": normalize_csv_text(obituary.city),
        "province": normalize_csv_text(obituary.province),
        "funeral_home": normalize_csv_text(obituary.funeral_home),
        "obituary_url": normalize_csv_text(obituary.obituary_url),
        "tags": normalize_csv_text(obituary.tags),
        "is_alumni": "true" if obituary.is_alumni else "false",
        "latitude": "" if obituary.latitude is None else obituary.latitude,
        "longitude": "" if obituary.longitude is None else obituary.longitude,
        "family_information": normalize_csv_text(obituary.family_information),
        "donation_information": normalize_csv_text(obituary.donation_information),
    }


def generate_csv():
    obituaries = DistinctObituary.query.filter(
        DistinctObituary.is_alumni.is_(True)
    ).order_by(
        DistinctObituary.publication_date.desc()
    ).all()
    if not obituaries:
        return None

    csv_buffer = StringIO()
    csv_buffer.write("\ufeff")
    writer = csv.DictWriter(csv_buffer, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for obituary in obituaries:
        writer.writerow(serialize_obituary_for_csv(obituary))

    return csv_buffer.getvalue()


@web_bp.get("/download_csv")
def download_csv():
    csv_data = generate_csv()
    if not csv_data:
        return jsonify({"error": "No obituaries available to download"}), 404

    filename = f"remembering_lancers_obituaries_{datetime.now():%Y-%m-%d}.csv"
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
