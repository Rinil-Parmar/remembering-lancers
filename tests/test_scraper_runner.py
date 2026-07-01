import threading

from bs4 import BeautifulSoup

from remembering_lancers.extensions import db
from remembering_lancers.models import (
    DistinctObituary,
    Obituary,
    ScrapeRun,
    ScrapeState,
)
from remembering_lancers.scraper import runner


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, html):
        self.html = html

    def get(self, url, **_kwargs):
        return FakeResponse(self.html)


class MappingSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append((url, timeout))
        return FakeResponse(self.responses[url])


def obituary_html(first_name="Test", last_name="ALUMNI", published_date="June 10, 2026"):
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
          <p>Published online {published_date}</p>
        </div>
        <span class="details-copy">
          Proud graduate of the University of Windsor.
        </span>
        <span class="obit-fh">Test Home</span>
      </body>
    </html>
    """


def test_extract_obituary_content_uses_details_copy():
    soup = BeautifulSoup(
        '<span class="details-copy">University of Windsor graduate.</span>',
        "html.parser",
    )

    assert runner.extract_obituary_content(
        soup,
        "WINDSORSTAR",
        "https://example.test/obituary/1",
    ) == "University of Windsor graduate."


def test_extract_obituary_content_falls_back_to_article():
    soup = BeautifulSoup(
        "<article>UWindsor graduate and community member.</article>",
        "html.parser",
    )

    assert runner.extract_obituary_content(
        soup,
        "WINDSORSTAR",
        "https://example.test/obituary/1",
    ) == "UWindsor graduate and community member."


def test_extract_obituary_content_returns_empty_when_missing():
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")

    assert runner.extract_obituary_content(
        soup,
        "WINDSORSTAR",
        "https://example.test/obituary/1",
    ) == ""


def test_extract_obituary_name_uses_current_data_testid_markup():
    soup = BeautifulSoup(
        """
        <h1 data-testid="desktop-menu-fullname">Alan George Wildeman</h1>
        """,
        "html.parser",
    )

    assert runner.extract_obituary_name(soup) == ("Alan George", "Wildeman")


def test_extract_obituary_name_falls_back_to_page_title():
    soup = BeautifulSoup(
        """
        <title>Alan George Wildeman Obituary | 1953 - 2026 | Windsor Star</title>
        """,
        "html.parser",
    )

    assert runner.extract_obituary_name(soup) == ("Alan George", "Wildeman")


def test_process_search_pagination_deduplicates_page_links(monkeypatch):
    base_url = "https://windsorstar.remembering.ca"
    obit_url = f"{base_url}/obituary/test-alumni-1"
    search_url = (
        f"{base_url}/obituaries/all-categories/search"
        "?search_type=advanced&ap_search_keyword=UWindsor&sort_by=date&order=desc"
    )
    session = MappingSession(
        {
            search_url: """
                <a href="/obituary/test-alumni-1">One</a>
                <a href="/obituary/test-alumni-1">Duplicate</a>
            """,
            obit_url: """
                <div class="details-published">
                    Published online June 10, 2026
                </div>
            """,
        }
    )

    monkeypatch.setenv("SCRAPER_MAX_PAGES", "1")
    monkeypatch.setenv("SCRAPER_CURRENT_MONTH_ONLY", "false")
    monkeypatch.setenv("SCRAPER_REQUEST_TIMEOUT", "7")

    pages = list(
        runner.process_search_pagination(
            session,
            "windsorstar",
            "UWindsor",
            set(),
            set(),
            threading.Event(),
        )
    )

    assert pages == [(1, [obit_url])]
    assert session.calls.count((obit_url, 7)) == 1


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


def test_newly_scraped_obituary_is_tagged_new_even_when_old_publication_date(
    app,
    monkeypatch,
):
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(runner, "get_coordinates", lambda city, province: (1.0, 2.0))

    new_url = "https://windsorstar.remembering.ca/obituary/old-alumni-1"
    result = runner.process_obituary(
        FakeSession(obituary_html(published_date="January 10, 2025")),
        db.session,
        new_url,
        set(),
        threading.Event(),
    )

    assert result["tags"] == "new"
    assert Obituary.query.filter_by(obituary_url=new_url).first().tags == "new"
    assert DistinctObituary.query.filter_by(obituary_url=new_url).first().tags == "new"


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


def test_process_city_continues_existing_urls_when_threshold_disabled(
    app,
    monkeypatch,
):
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
    monkeypatch.setattr(runner, "get_existing_url_stop_threshold", lambda: 0)
    monkeypatch.setattr(
        runner,
        "process_search_pagination",
        fake_process_search_pagination,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [later_url]


def test_process_city_records_run_counts_when_threshold_disabled(app, monkeypatch):
    processed_urls = []
    existing_url = "https://test.local/obituary/test-alumni-1"
    later_url = "https://windsorstar.remembering.ca/obituary/newer-alumni"
    scrape_run = runner.create_scrape_run()

    def fake_process_search_pagination(
        session,
        subdomain,
        search_keyword,
        visited_search_pages,
        visited_obituaries,
        stop_event,
    ):
        yield 2, [existing_url, later_url]

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "get_existing_url_stop_threshold", lambda: 0)
    monkeypatch.setattr(
        runner,
        "process_search_pagination",
        fake_process_search_pagination,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(
        FakeSession(""),
        "windsorstar",
        threading.Event(),
        scrape_run,
    )

    db.session.refresh(scrape_run)
    assert processed_urls == [later_url]
    assert scrape_run.city == "windsorstar"
    assert scrape_run.search_keyword == "University of Windsor"
    assert scrape_run.page_number == 2
    assert scrape_run.saved_count == 1
    assert scrape_run.duplicate_count == 1


def test_process_city_skips_completed_state_without_force_rescan(app, monkeypatch):
    scrape_run = runner.create_scrape_run()
    db.session.add(
        ScrapeState(
            subdomain="windsorstar",
            search_keyword="University of Windsor",
            page_number=5,
            last_processed_url="https://windsorstar.remembering.ca/obituary/done",
            status="completed",
        )
    )
    db.session.commit()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("completed scrape state should be skipped")

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "process_search_pagination", fail_if_called)
    monkeypatch.delenv("SCRAPER_FORCE_RESCAN", raising=False)

    runner.process_city(
        FakeSession(""),
        "windsorstar",
        threading.Event(),
        scrape_run,
    )

    db.session.refresh(scrape_run)
    assert scrape_run.skipped_count == 1
    assert scrape_run.city == "windsorstar"
    assert scrape_run.search_keyword == "University of Windsor"


def test_process_city_scans_completed_state_when_force_rescan_enabled(
    app,
    monkeypatch,
):
    processed_urls = []
    scrape_run = runner.create_scrape_run()
    done_url = "https://windsorstar.remembering.ca/obituary/done"
    db.session.add(
        ScrapeState(
            subdomain="windsorstar",
            search_keyword="University of Windsor",
            page_number=1,
            last_processed_url=done_url,
            status="completed",
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
        yield 1, [done_url]

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": False}

    monkeypatch.setenv("SCRAPER_FORCE_RESCAN", "true")
    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "obituary_url_exists", lambda _url: False)
    monkeypatch.setattr(
        runner,
        "process_search_pagination",
        fake_process_search_pagination,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(
        FakeSession(""),
        "windsorstar",
        threading.Event(),
        scrape_run,
    )

    db.session.refresh(scrape_run)
    assert processed_urls == [done_url]
    assert scrape_run.skipped_count == 1


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


def test_process_city_ignores_previous_state_when_resume_disabled(app, monkeypatch):
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

    monkeypatch.setenv("SCRAPER_RESUME_FROM_STATE", "false")
    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "obituary_url_exists", lambda _url: False)
    monkeypatch.setattr(
        runner,
        "process_search_pagination",
        fake_process_search_pagination,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [previous_url, next_url]
