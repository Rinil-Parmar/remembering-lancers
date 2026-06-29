from datetime import datetime

import pytest

from remembering_lancers import create_app
from remembering_lancers.extensions import db
from remembering_lancers.models import DistinctObituary, Obituary


@pytest.fixture
def app(tmp_path):
    app = create_app("testing")
    app.config.update(
        CSV_EXPORT_PATH=str(tmp_path / "obituaries.csv"),
    )

    with app.app_context():
        db.create_all()
        seed_records()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def seed_records():
    records = [
        {
            "id": 1,
            "name": "Test Alumni",
            "first_name": "Test",
            "last_name": "Alumni",
            "birth_date": "January 01, 1950",
            "death_date": "June 01, 2026",
            "city": "Windsor",
            "province": "Ontario",
            "publication_date": datetime(2026, 6, 1),
            "obituary_url": "https://test.local/obituary/test-alumni-1",
            "family_information": "Graduated from University of Windsor.",
            "donation_information": "",
            "is_alumni": True,
            "funeral_home": "Test Home",
            "tags": "new",
            "latitude": 42.3149,
            "longitude": -83.0364,
        },
        {
            "id": 2,
            "name": "Second Alumni",
            "first_name": "Second",
            "last_name": "Alumni",
            "birth_date": None,
            "death_date": "May 01, 2024",
            "city": "Toronto",
            "province": "Ontario",
            "publication_date": datetime(2024, 5, 1),
            "obituary_url": "https://test.local/obituary/second-alumni",
            "family_information": "Proud UWindsor graduate.",
            "donation_information": "",
            "is_alumni": True,
            "funeral_home": "Test Home",
            "tags": "updated",
            "latitude": 43.6532,
            "longitude": -79.3832,
        },
        {
            "id": 3,
            "name": "Non Alumni",
            "first_name": "Non",
            "last_name": "Alumni",
            "birth_date": None,
            "death_date": "June 02, 2026",
            "city": "Windsor",
            "province": "Ontario",
            "publication_date": datetime(2026, 6, 2),
            "obituary_url": "https://test.local/obituary/non-alumni",
            "family_information": "No matching school text.",
            "donation_information": "",
            "is_alumni": False,
            "funeral_home": "Test Home",
            "tags": "new",
            "latitude": 42.3149,
            "longitude": -83.0364,
        },
    ]

    for record in records:
        db.session.add(Obituary(**record))
        db.session.add(DistinctObituary(**record))
    db.session.commit()
