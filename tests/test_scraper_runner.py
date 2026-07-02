import threading

import pytest
import requests
from bs4 import BeautifulSoup

from remembering_lancers.extensions import db
from remembering_lancers.models import (
    DistinctObituary,
    Obituary,
    ScrapeRun,
    ScrapeState,
)
from remembering_lancers.scraper import runner


@pytest.fixture(autouse=True)
def default_keyword_search_mode(monkeypatch):
    monkeypatch.setenv("SCRAPER_MODE", "keyword_search")
    monkeypatch.setenv("SCRAPER_FORCE_RESCAN", "false")


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


def test_build_search_url_uses_page_limit(monkeypatch):
    monkeypatch.setenv("SCRAPER_PAGE_LIMIT", "125")

    assert runner.build_search_url("windsorstar", "UWindsor", 2) == (
        "https://windsorstar.remembering.ca/obituaries/obituaries/search"
        "?limit=125&search_type=advanced&ap_search_keyword=UWindsor"
        "&sort_by=date&order=desc&p=2"
    )


def test_build_listing_url_uses_page_limit(monkeypatch):
    monkeypatch.setenv("SCRAPER_PAGE_LIMIT", "125")

    assert runner.build_listing_url("windsorstar", 2) == (
        "https://windsorstar.remembering.ca/obituaries/obituaries/search"
        "?limit=125&p=2"
    )


def test_process_search_pagination_deduplicates_page_links(monkeypatch):
    base_url = "https://windsorstar.remembering.ca"
    obit_url = f"{base_url}/obituary/test-alumni-1"
    search_url = (
        f"{base_url}/obituaries/obituaries/search"
        "?limit=125&search_type=advanced&ap_search_keyword=UWindsor"
        "&sort_by=date&order=desc"
    )
    session = MappingSession(
        {
            search_url: """
                <a href="/obituary/test-alumni-1">One</a>
                <a href="/obituary/test-alumni-1">Duplicate</a>
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
    assert session.calls == [(search_url, 7)]


def test_fetch_search_page_urls_stops_repeated_page_content(monkeypatch):
    base_url = "https://windsorstar.remembering.ca"
    first_search_url = (
        f"{base_url}/obituaries/obituaries/search"
        "?limit=125&search_type=advanced&ap_search_keyword=UWindsor"
        "&sort_by=date&order=desc"
    )
    second_search_url = f"{first_search_url}&p=2"
    obit_url = f"{base_url}/obituary/test-alumni-1"
    page_html = '<a href="/obituary/test-alumni-1">One</a>'
    session = MappingSession(
        {
            first_search_url: page_html,
            second_search_url: page_html,
        }
    )
    visited_search_pages = set()

    monkeypatch.setenv("SCRAPER_CURRENT_MONTH_ONLY", "false")
    monkeypatch.setenv("SCRAPER_REQUEST_TIMEOUT", "7")

    first_urls, first_stop = runner.fetch_search_page_urls(
        session,
        "windsorstar",
        "UWindsor",
        1,
        visited_search_pages,
        set(),
        {},
        threading.Event(),
    )
    second_urls, second_stop = runner.fetch_search_page_urls(
        session,
        "windsorstar",
        "UWindsor",
        2,
        visited_search_pages,
        set(),
        {},
        threading.Event(),
    )

    assert first_urls == [obit_url]
    assert first_stop is False
    assert second_urls == []
    assert second_stop is True


def test_fetch_listing_page_urls_deduplicates_links(monkeypatch):
    base_url = "https://windsorstar.remembering.ca"
    listing_url = f"{base_url}/obituaries/obituaries/search?limit=125"
    obit_url = f"{base_url}/obituary/test-alumni-1"
    session = MappingSession(
        {
            listing_url: """
                <a href="/obituary/test-alumni-1">One</a>
                <a href="/obituary/test-alumni-1">Duplicate</a>
            """,
        }
    )

    monkeypatch.setenv("SCRAPER_REQUEST_TIMEOUT", "7")

    urls, stop_city, stop_reason = runner.fetch_listing_page_urls(
        session,
        "windsorstar",
        1,
        set(),
        {},
        threading.Event(),
    )

    assert urls == [obit_url]
    assert stop_city is False
    assert stop_reason is None
    assert session.calls == [(listing_url, 7)]


def test_fetch_listing_page_urls_stops_on_repeated_page_content(monkeypatch):
    base_url = "https://windsorstar.remembering.ca"
    first_listing_url = f"{base_url}/obituaries/obituaries/search?limit=125"
    second_listing_url = f"{base_url}/obituaries/obituaries/search?limit=125&p=2"
    page_html = """
        <a href="/obituary/test-alumni-1">One</a>
        <a href="/obituary/test-alumni-2">Two</a>
    """
    session = MappingSession(
        {
            first_listing_url: page_html,
            second_listing_url: page_html,
        }
    )
    visited_listing_pages = set()
    visited_listing_signatures = {}

    monkeypatch.setenv("SCRAPER_REQUEST_TIMEOUT", "7")
    monkeypatch.setenv("SCRAPER_REPEATED_PAGE_STOP_THRESHOLD", "1")

    first_urls, first_stop, first_reason = runner.fetch_listing_page_urls(
        session,
        "windsorstar",
        1,
        visited_listing_pages,
        visited_listing_signatures,
        threading.Event(),
    )
    second_urls, second_stop, second_reason = runner.fetch_listing_page_urls(
        session,
        "windsorstar",
        2,
        visited_listing_pages,
        visited_listing_signatures,
        threading.Event(),
    )

    assert first_urls == [
        f"{base_url}/obituary/test-alumni-1",
        f"{base_url}/obituary/test-alumni-2",
    ]
    assert first_stop is False
    assert first_reason is None
    assert second_urls == []
    assert second_stop is True
    assert second_reason == runner.FETCH_STOP_REPEATED_PAGE


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


def test_process_city_skips_existing_urls_and_continues(app, monkeypatch):
    processed_urls = []
    existing_url = "https://test.local/obituary/test-alumni-1"
    existing_url_2 = "https://test.local/obituary/second-alumni"
    existing_url_3 = "https://test.local/obituary/non-alumni"
    later_url = "https://windsorstar.remembering.ca/obituary/newer-alumni"

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        return [existing_url, existing_url_2, existing_url_3, later_url], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(
        runner,
        "fetch_search_page_urls",
        fake_fetch_search_page_urls,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [later_url]


def test_process_city_duplicate_urls_do_not_block_next_keyword(app, monkeypatch):
    processed_urls = []
    existing_url = "https://test.local/obituary/test-alumni-1"
    existing_url_2 = "https://test.local/obituary/second-alumni"
    existing_url_3 = "https://test.local/obituary/non-alumni"
    next_keyword_url = "https://windsorstar.remembering.ca/obituary/next-keyword"

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        if search_keyword == "first keyword":
            return [existing_url, existing_url_2, existing_url_3], True
        return [next_keyword_url], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: [
        "first keyword",
        "second keyword",
    ])
    monkeypatch.setattr(
        runner,
        "fetch_search_page_urls",
        fake_fetch_search_page_urls,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner, "obituary_url_exists", lambda url: url != next_keyword_url)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [next_keyword_url]


def test_process_city_scans_pages_before_advancing_keyword_batches(app, monkeypatch):
    calls = []

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        calls.append((page, search_keyword))
        return [], page == 2

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["alpha", "beta"])
    monkeypatch.setattr(runner, "get_max_pages", lambda: 2)
    monkeypatch.setattr(runner, "fetch_search_page_urls", fake_fetch_search_page_urls)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert calls == [
        (1, "alpha"),
        (1, "beta"),
        (2, "alpha"),
        (2, "beta"),
    ]


def test_process_city_continues_after_existing_urls(
    app,
    monkeypatch,
):
    processed_urls = []
    existing_url = "https://test.local/obituary/test-alumni-1"
    existing_url_2 = "https://test.local/obituary/second-alumni"
    existing_url_3 = "https://test.local/obituary/non-alumni"
    later_url = "https://windsorstar.remembering.ca/obituary/newer-alumni"

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        return [existing_url, existing_url_2, existing_url_3, later_url], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(
        runner,
        "fetch_search_page_urls",
        fake_fetch_search_page_urls,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [later_url]


def test_process_city_records_run_counts_for_duplicates_and_saved_urls(app, monkeypatch):
    processed_urls = []
    existing_url = "https://test.local/obituary/test-alumni-1"
    later_url = "https://windsorstar.remembering.ca/obituary/newer-alumni"
    scrape_run = runner.create_scrape_run()

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        if page == 2:
            return [existing_url, later_url], True
        return [], False

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "get_max_pages", lambda: 2)
    monkeypatch.setattr(
        runner,
        "fetch_search_page_urls",
        fake_fetch_search_page_urls,
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


def test_create_scrape_run_marks_stale_running_runs_stopped(app):
    stale_run = ScrapeRun(status="running", started_at=runner.datetime.now())
    db.session.add(stale_run)
    db.session.commit()

    new_run = runner.create_scrape_run()

    db.session.refresh(stale_run)
    assert stale_run.status == "stopped"
    assert stale_run.finished_at is not None
    assert new_run.status == "running"


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
    monkeypatch.setattr(runner, "fetch_search_page_urls", fail_if_called)
    monkeypatch.setenv("SCRAPER_FORCE_RESCAN", "false")

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

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        return [done_url], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": False}

    monkeypatch.setenv("SCRAPER_FORCE_RESCAN", "true")
    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "obituary_url_exists", lambda _url: False)
    monkeypatch.setattr(
        runner,
        "fetch_search_page_urls",
        fake_fetch_search_page_urls,
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

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        return [previous_url, next_url], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setenv("SCRAPER_FORCE_RESCAN", "false")
    monkeypatch.setattr(
        runner,
        "fetch_search_page_urls",
        fake_fetch_search_page_urls,
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

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        return [previous_url, next_url], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        return {"is_alumni": True}

    monkeypatch.setenv("SCRAPER_RESUME_FROM_STATE", "false")
    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "obituary_url_exists", lambda _url: False)
    monkeypatch.setattr(
        runner,
        "fetch_search_page_urls",
        fake_fetch_search_page_urls,
    )
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [previous_url, next_url]


def test_keyword_state_is_completed_when_keyword_stops(app, monkeypatch):
    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        return [], True

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "fetch_search_page_urls", fake_fetch_search_page_urls)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    state = ScrapeState.query.filter_by(
        subdomain="windsorstar",
        search_keyword="University of Windsor",
    ).one()
    assert state.status == runner.SCRAPE_STATE_COMPLETED


def test_configured_alumni_keywords_are_used(monkeypatch):
    monkeypatch.setenv("SCRAPER_ALUMNI_KEYWORDS", "Custom Alumni Phrase")

    assert (
        runner.get_matching_alumni_keyword(
            "This obituary mentions a custom alumni phrase."
        )
        == "Custom Alumni Phrase"
    )


def test_process_city_retries_obituary_after_request_failure(app, monkeypatch):
    new_url = "https://windsorstar.remembering.ca/obituary/flaky-alumni"
    scrape_run = runner.create_scrape_run()

    class FlakySession:
        def __init__(self):
            self.obituary_calls = 0

        def get(self, url, **_kwargs):
            if url == new_url:
                self.obituary_calls += 1
                if self.obituary_calls == 1:
                    raise requests.exceptions.Timeout("temporary timeout")
                return FakeResponse(obituary_html())
            return FakeResponse("")

    session = FlakySession()

    def fake_fetch_search_page_urls(
        session,
        subdomain,
        search_keyword,
        page,
        visited_search_pages,
        visited_obituaries,
        publication_date_cache,
        stop_event,
    ):
        return [new_url], True

    monkeypatch.setattr(runner, "get_search_keywords", lambda: ["University of Windsor"])
    monkeypatch.setattr(runner, "fetch_search_page_urls", fake_fetch_search_page_urls)
    monkeypatch.setattr(runner, "get_coordinates", lambda city, province: (1.0, 2.0))
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(session, "windsorstar", threading.Event(), scrape_run)

    db.session.refresh(scrape_run)
    assert session.obituary_calls == 2
    assert scrape_run.saved_count == 1
    assert Obituary.query.filter_by(obituary_url=new_url).count() == 1


def test_listing_scan_processes_each_obituary_once(app, monkeypatch):
    processed_urls = []
    first_url = "https://windsorstar.remembering.ca/obituary/listing-one"
    second_url = "https://windsorstar.remembering.ca/obituary/listing-two"

    def fake_fetch_listing_page_urls(
        session,
        subdomain,
        page,
        visited_listing_pages,
        visited_listing_signatures,
        stop_event,
    ):
        if page == 1:
            return [first_url, first_url, second_url], False
        return [], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        visited_obituaries.add(url)
        return {"is_alumni": url == second_url}

    monkeypatch.setenv("SCRAPER_MODE", "listing_scan")
    monkeypatch.setenv("SCRAPER_FORCE_RESCAN", "true")
    monkeypatch.setattr(runner, "get_max_pages", lambda: 2)
    monkeypatch.setattr(runner, "fetch_listing_page_urls", fake_fetch_listing_page_urls)
    monkeypatch.setattr(runner, "obituary_url_exists", lambda _url: False)
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [first_url, second_url]


def test_listing_scan_resumes_after_last_processed_url(app, monkeypatch):
    processed_urls = []
    previous_url = "https://windsorstar.remembering.ca/obituary/listing-previous"
    next_url = "https://windsorstar.remembering.ca/obituary/listing-next"

    db.session.add(
        ScrapeState(
            subdomain="windsorstar",
            search_keyword=runner.LISTING_SCAN_STATE_KEYWORD,
            page_number=1,
            last_processed_url=previous_url,
            status="running",
        )
    )
    db.session.commit()

    def fake_fetch_listing_page_urls(
        session,
        subdomain,
        page,
        visited_listing_pages,
        visited_listing_signatures,
        stop_event,
    ):
        return [previous_url, next_url], True

    def fake_process_obituary(session, db_session, url, visited_obituaries, stop_event):
        processed_urls.append(url)
        visited_obituaries.add(url)
        return {"is_alumni": True}

    monkeypatch.setenv("SCRAPER_MODE", "listing_scan")
    monkeypatch.setenv("SCRAPER_FORCE_RESCAN", "false")
    monkeypatch.setattr(runner, "fetch_listing_page_urls", fake_fetch_listing_page_urls)
    monkeypatch.setattr(runner, "obituary_url_exists", lambda _url: False)
    monkeypatch.setattr(runner, "process_obituary", fake_process_obituary)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    runner.process_city(FakeSession(""), "windsorstar", threading.Event())

    assert processed_urls == [next_url]
