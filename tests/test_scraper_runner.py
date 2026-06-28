import threading

from remembering_lancers.extensions import db
from remembering_lancers.models import DistinctObituary, Obituary
from remembering_lancers.scraper import runner


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, html):
        self.html = html

    def get(self, url):
        return FakeResponse(self.html)


def obituary_html(first_name="Test", last_name="ALUMNI"):
    return f"""
    <html>
      <body>
        <h1 class="obit-name">{first_name} {last_name}</h1>
        <span class="obit-lastname-upper">{last_name}</span>
        <h2 class="obit-dates">
          <span>January 01, 1950</span>
          <span>June 01, 2026</span>
        </h2>
        <div class="details-published">
          <p>Published online June 10, 2026</p>
        </div>
        <span class="details-copy">
          Proud graduate of the University of Windsor.
        </span>
        <span class="obit-fh">Test Home</span>
      </body>
    </html>
    """


def test_process_obituary_skips_existing_obituary_url(app, monkeypatch):
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(runner, "get_coordinates", lambda city, province: (1.0, 2.0))

    existing_url = "https://test.local/obituary/test-alumni-1"
    result = runner.process_obituary(
        FakeSession(obituary_html()),
        db.session,
        existing_url,
        set(),
        threading.Event(),
    )

    assert result["url"] == existing_url
    assert Obituary.query.filter_by(obituary_url=existing_url).count() == 1
    assert DistinctObituary.query.filter_by(obituary_url=existing_url).count() == 1


def test_process_obituary_allows_same_name_with_different_url(app, monkeypatch):
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(runner, "get_coordinates", lambda city, province: (1.0, 2.0))

    new_url = "https://windsorstar.remembering.ca/obituary/test-alumni-2"
    result = runner.process_obituary(
        FakeSession(obituary_html()),
        db.session,
        new_url,
        set(),
        threading.Event(),
    )

    assert result["is_alumni"] is True
    assert Obituary.query.filter_by(name="Test Alumni").count() == 2
    assert DistinctObituary.query.filter_by(name="Test Alumni").count() == 2
    assert DistinctObituary.query.filter_by(obituary_url=new_url).count() == 1
