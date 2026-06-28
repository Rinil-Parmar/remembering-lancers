import threading

from remembering_lancers.extensions import db
from remembering_lancers.models import DistinctObituary, Obituary, ScrapeState
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


def test_process_city_stops_when_existing_obituary_url_is_reached(app, monkeypatch):
    processed_urls = []
    existing_url = "https://test.local/obituary/test-alumni-1"
    existing_url_2 = "https://test.local/obituary/second-alumni"
    existing_url_3 = "https://test.local/obituary/non-alumni"
    later_url = "https://windsorstar.remembering.ca/obituary/newer-alumni"

    def fake_process_search_pagination(
        session,
        subdomain,
        search_keyword,
        visited_search_pages,
        visited_obituaries,
        stop_event,
    ):
        yield 1, [existing_url, existing_url_2, existing_url_3, later_url]

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "get_existing_url_stop_threshold", lambda: 3)
    monkeypatch.setattr(
        runner,
        "process_search_pagination",
        fake_process_search_pagination,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == []


def test_process_city_resumes_after_last_processed_url(app, monkeypatch):
    processed_urls = []
    previous_url = "https://windsorstar.remembering.ca/obituary/previous-alumni"
    next_url = "https://windsorstar.remembering.ca/obituary/next-alumni"

    db.session.add(
        ScrapeState(
            subdomain="windsorstar",
            search_keyword="University of Windsor",
            page_number=1,
            last_processed_url=previous_url,
            status="running",
        )
    )
    db.session.commit()

    def fake_process_search_pagination(
        session,
        subdomain,
        search_keyword,
        visited_search_pages,
        visited_obituaries,
        stop_event,
    ):
        yield 1, [previous_url, next_url]

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(
        runner,
        "process_search_pagination",
        fake_process_search_pagination,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [next_url]
