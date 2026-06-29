from remembering_lancers.models import DistinctObituary, Obituary
from remembering_lancers.extensions import db
from remembering_lancers.web.formatting import (
    split_donation_items,
    split_obituary_paragraphs,
)


def test_dashboard_about_detail_and_csv_routes(client):
    assert client.get("/").status_code == 200
    assert client.get("/about").status_code == 200
    assert client.get("/obituary/1").status_code == 200

    csv_response = client.get("/download_csv")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.content_type
    assert b"Test Alumni" in csv_response.data


def test_update_tags_updates_distinct_and_source_rows(client, app):
    response = client.post("/update_tags/1", data={"tags": "updated"})
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(DistinctObituary, 1).tags == "updated"
        assert db.session.get(Obituary, 1).tags == "updated"


def test_update_tags_rejects_invalid_value(client):
    response = client.post("/update_tags/1", data={"tags": "bad"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid tag value"}


def test_obituary_body_formatter_removes_page_header_noise():
    paragraphs = split_obituary_paragraphs(
        (
            "Alan MetcalfeMarch 16, 1933-June 16, 2026"
            "Alan MetcalfeObituaryEventsGuestbookShare"
            "Alan Metcalfe ObituaryIt was time to say goodbye. "
            "He served students at the University of Windsor.He loved family."
        ),
        "Alan Metcalfe",
    )

    assert paragraphs[0] == (
        "It was time to say goodbye. "
        "He served students at the University of Windsor."
    )
    assert paragraphs[1] == "He loved family."


def test_donation_formatter_splits_semicolon_separated_items():
    assert split_donation_items("Donate to charity.; Memorial fund welcome.") == [
        "Donate to charity",
        "Memorial fund welcome",
    ]
