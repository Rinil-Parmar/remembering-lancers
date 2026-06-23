import logging
from datetime import datetime

from flask import jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import aliased

from . import api_bp
from ..extensions import db
from ..models import DistinctObituary


def serialize_obituary(obituary):
    return {
        "id": obituary.id,
        "name": obituary.name,
        "first_name": obituary.first_name,
        "last_name": obituary.last_name,
        "obituary_url": obituary.obituary_url,
        "city": obituary.city,
        "province": obituary.province,
        "birth_date": obituary.birth_date,
        "death_date": obituary.death_date,
        "publication_date": obituary.publication_date,
        "is_alumni": obituary.is_alumni,
        "tags": obituary.tags,
        "latitude": obituary.latitude,
        "longitude": obituary.longitude,
    }


@api_bp.route("/search_obituaries")
def search_obituaries():
    first_name_query = request.args.get("firstName", "").strip()
    last_name_query = request.args.get("lastName", "").strip()
    city_query = request.args.get("city", "").strip()
    province_query = request.args.get("province", "").strip()
    query_string = request.args.get("query", "").strip()

    query_filter = DistinctObituary.query.filter(
        DistinctObituary.is_alumni.is_(True)
    )

    if first_name_query:
        query_filter = query_filter.filter(
            DistinctObituary.first_name.ilike(f"%{first_name_query}%")
        )
    if last_name_query:
        query_filter = query_filter.filter(
            DistinctObituary.last_name.ilike(f"%{last_name_query}%")
        )
    if city_query:
        query_filter = query_filter.filter(
            DistinctObituary.city.ilike(f"%{city_query}%")
        )
    if province_query:
        query_filter = query_filter.filter(
            DistinctObituary.province == province_query
        )
    if query_string:
        query_filter = query_filter.filter(
            DistinctObituary.first_name.ilike(f"%{query_string}%")
            | DistinctObituary.last_name.ilike(f"%{query_string}%")
            | DistinctObituary.family_information.ilike(f"%{query_string}%")
        )

    logging.info("Search query: %s", query_filter)
    obituaries = query_filter.order_by(DistinctObituary.last_name).all()
    logging.info("Search query returned %s obituaries", len(obituaries))

    return jsonify([serialize_obituary(obituary) for obituary in obituaries])


@api_bp.route("/get_obituaries")
def get_obituaries():
    subquery = db.session.query(
        DistinctObituary,
        func.row_number()
        .over(
            partition_by=DistinctObituary.name,
            order_by=DistinctObituary.publication_date.desc(),
        )
        .label("row_num"),
    ).subquery()

    obituary_alias = aliased(DistinctObituary, subquery)
    obituaries = (
        db.session.query(obituary_alias)
        .filter(subquery.c.row_num == 1)
        .filter(obituary_alias.is_alumni.is_(True))
        .order_by(obituary_alias.publication_date.desc())
        .all()
    )

    return jsonify([serialize_obituary(obituary) for obituary in obituaries])


@api_bp.route("/api/publications/grouped-by-year")
def get_publications_by_year_endpoint():
    publications_by_year = get_publications_grouped_by_year()
    if publications_by_year is None:
        return jsonify({"error": "Failed to fetch publications by year"}), 500
    return jsonify(publications_by_year)


def get_publications_grouped_by_year():
    try:
        obituaries = (
            DistinctObituary.query.filter(DistinctObituary.is_alumni.is_(True))
            .order_by(DistinctObituary.publication_date.desc())
            .all()
        )

        current_year = datetime.now().year
        grouped_data = {
            str(year): [] for year in range(current_year, 2021, -1)
        }
        grouped_data["Before 2022"] = []

        for obituary in obituaries:
            year = (
                obituary.publication_date.year
                if obituary.publication_date
                else None
            )
            if year and year >= 2022:
                grouped_data.setdefault(str(year), []).append(
                    serialize_obituary(obituary)
                )
            elif year:
                grouped_data["Before 2022"].append(serialize_obituary(obituary))

        return grouped_data
    except Exception:
        logging.exception("Database error fetching publications by year")
        return None
