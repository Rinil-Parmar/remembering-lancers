import csv

from flask import (
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from sqlalchemy import func

from . import web_bp
from ..extensions import db
from ..models import DistinctObituary, Obituary


@web_bp.route("/")
def dashboard():
    total_alumni = db.session.query(
        func.count(func.distinct(DistinctObituary.name))
    ).scalar()
    total_obituaries = DistinctObituary.query.count()
    total_cities = len(
        {
            obituary.city
            for obituary in DistinctObituary.query.all()
            if obituary.city
        }
    )

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
    return render_template("obituary_detail.html", obituary=obituary)


@web_bp.route("/about")
def about():
    return render_template("about.html")


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


def generate_csv():
    obituaries = DistinctObituary.query.order_by(
        DistinctObituary.publication_date.desc()
    ).all()
    if not obituaries:
        return None

    fieldnames = [
        "id",
        "name",
        "first_name",
        "last_name",
        "city",
        "province",
        "birth_date",
        "death_date",
        "obituary_url",
        "tags",
    ]
    csv_export_path = current_app.config["CSV_EXPORT_PATH"]
    with open(csv_export_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for obituary in obituaries:
            writer.writerow(
                {
                    "id": obituary.id,
                    "name": obituary.name,
                    "first_name": obituary.first_name,
                    "last_name": obituary.last_name,
                    "obituary_url": obituary.obituary_url,
                    "city": obituary.city,
                    "province": obituary.province,
                    "birth_date": obituary.birth_date,
                    "death_date": obituary.death_date,
                    "tags": obituary.tags,
                }
            )

    return csv_export_path


@web_bp.get("/download_csv")
def download_csv():
    csv_file = generate_csv()
    if not csv_file:
        return jsonify({"error": "No obituaries available to download"}), 404

    return send_file(
        csv_file,
        as_attachment=True,
        download_name="obituaries.csv",
        mimetype="text/csv",
    )
