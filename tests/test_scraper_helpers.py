from bs4 import BeautifulSoup

import scrapper
from remembering_lancers.scraper.locations import extract_city_and_province
from remembering_lancers.scraper.parser import (
    extract_dates,
    get_publication_date_from_soup,
)
from remembering_lancers.scraper.runner import (
    SEARCH_KEYWORD,
    current_month_only_enabled,
    force_rescan_enabled,
    get_existing_url_stop_threshold,
    get_search_keywords,
    get_target_city,
    get_matching_alumni_keyword,
    get_request_timeout,
    get_retry_total,
    is_alumni_obituary,
    order_subdomains,
    resume_from_state_enabled,
)


def test_extract_city_and_province_from_known_subdomain():
    assert extract_city_and_province(
        "https://windsorstar.remembering.ca/obituary/example-123"
    ) == ("Windsor", "Ontario")


def test_extract_city_and_province_returns_none_for_unknown_subdomain():
    assert (
        extract_city_and_province(
            "https://unknown.remembering.ca/obituary/example-123"
        )
        is None
    )


def test_get_publication_date_from_soup_supports_details_published_markup():
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <div class="details-published">
              <p>Published online June 10, 2026</p>
            </div>
          </body>
        </html>
        """,
        "html.parser",
    )

    assert get_publication_date_from_soup(soup) == "June 10, 2026"


def test_extract_dates_from_obit_dates_tag():
    soup = BeautifulSoup(
        '<h2 class="obit-dates"><span>January 01, 1950</span><span>June 01, 2026</span></h2>',
        "html.parser",
    )

    assert extract_dates(soup) == (
        "January 01, 1950",
        "June 01, 2026",
    )


def test_scrapper_exports_package_helper_functions_for_compatibility():
    assert scrapper.extract_city_and_province is extract_city_and_province
    assert scrapper.get_publication_date_from_soup is get_publication_date_from_soup


def test_search_keyword_is_encoded_as_a_single_search_phrase():
    assert SEARCH_KEYWORD == "Windsor University"
    assert isinstance(scrapper.SEARCH_KEYWORD, str)


def test_alumni_detection_is_case_insensitive():
    assert is_alumni_obituary("A proud graduate of the university of windsor.")
    assert is_alumni_obituary("He loved UWindsor and the local community.")
    assert not is_alumni_obituary("A long-time Windsor resident.")


def test_matching_alumni_keyword_returns_keyword():
    assert (
        get_matching_alumni_keyword("A proud graduate of the university of windsor.")
        == "University of Windsor"
    )
    assert get_matching_alumni_keyword("A long-time Windsor resident.") is None


def test_scraper_configuration_helpers_read_environment(monkeypatch):
    monkeypatch.setenv("SCRAPER_SEARCH_KEYWORDS", "Alpha, Beta,, Gamma ")
    monkeypatch.setenv("SCRAPER_CURRENT_MONTH_ONLY", "false")
    monkeypatch.setenv("SCRAPER_CITY", "WindsorStar")

    assert get_search_keywords() == ["Alpha", "Beta", "Gamma"]
    assert current_month_only_enabled() is False
    assert get_target_city() == "windsorstar"


def test_get_search_keywords_defaults_when_env_missing(monkeypatch):
    monkeypatch.delenv("SCRAPER_SEARCH_KEYWORDS", raising=False)

    assert get_search_keywords() == [
        "University of Windsor",
        "UWindsor",
        "Windsor University",
    ]


def test_current_month_only_enabled_defaults_to_true(monkeypatch):
    monkeypatch.delenv("SCRAPER_CURRENT_MONTH_ONLY", raising=False)

    assert current_month_only_enabled() is True


def test_current_month_only_enabled_accepts_truthy_values(monkeypatch):
    for value in ["1", "true", "yes", "on"]:
        monkeypatch.setenv("SCRAPER_CURRENT_MONTH_ONLY", value)
        assert current_month_only_enabled() is True


def test_current_month_only_enabled_accepts_false_values(monkeypatch):
    for value in ["0", "false", "no", "off"]:
        monkeypatch.setenv("SCRAPER_CURRENT_MONTH_ONLY", value)
        assert current_month_only_enabled() is False


def test_resume_from_state_enabled_defaults_to_true(monkeypatch):
    monkeypatch.delenv("SCRAPER_RESUME_FROM_STATE", raising=False)

    assert resume_from_state_enabled() is True


def test_resume_from_state_enabled_accepts_false_values(monkeypatch):
    for value in ["0", "false", "no", "off"]:
        monkeypatch.setenv("SCRAPER_RESUME_FROM_STATE", value)
        assert resume_from_state_enabled() is False


def test_force_rescan_enabled_defaults_to_false(monkeypatch):
    monkeypatch.delenv("SCRAPER_FORCE_RESCAN", raising=False)

    assert force_rescan_enabled() is False


def test_force_rescan_enabled_accepts_truthy_values(monkeypatch):
    for value in ["1", "true", "yes", "on"]:
        monkeypatch.setenv("SCRAPER_FORCE_RESCAN", value)
        assert force_rescan_enabled() is True


def test_request_timeout_defaults_and_reads_environment(monkeypatch):
    monkeypatch.delenv("SCRAPER_REQUEST_TIMEOUT", raising=False)
    assert get_request_timeout() == 10

    monkeypatch.setenv("SCRAPER_REQUEST_TIMEOUT", "5")
    assert get_request_timeout() == 5


def test_retry_total_defaults_and_reads_environment(monkeypatch):
    monkeypatch.delenv("SCRAPER_RETRY_TOTAL", raising=False)
    assert get_retry_total() == 3

    monkeypatch.setenv("SCRAPER_RETRY_TOTAL", "5")
    assert get_retry_total() == 5


def test_existing_url_stop_threshold_defaults_and_reads_environment(monkeypatch):
    monkeypatch.delenv("SCRAPER_EXISTING_URL_STOP_THRESHOLD", raising=False)
    assert get_existing_url_stop_threshold() == 3

    monkeypatch.setenv("SCRAPER_EXISTING_URL_STOP_THRESHOLD", "5")
    assert get_existing_url_stop_threshold() == 5


def test_existing_url_stop_threshold_zero_disables_stop(monkeypatch):
    monkeypatch.setenv("SCRAPER_EXISTING_URL_STOP_THRESHOLD", "0")

    assert get_existing_url_stop_threshold() == 0


def test_order_subdomains_prioritizes_windsor_and_nearby_locations(monkeypatch):
    monkeypatch.delenv("SCRAPER_CITY", raising=False)

    ordered = order_subdomains(
        [
            "ottawa",
            "calgary",
            "windsorstar",
            "lfpress",
            "theobserver",
        ]
    )

    assert ordered[:4] == [
        "windsorstar",
        "theobserver",
        "lfpress",
        "ottawa",
    ]
    assert ordered[-1] == "calgary"


def test_order_subdomains_uses_single_target_city(monkeypatch):
    monkeypatch.setenv("SCRAPER_CITY", "windsorstar")

    assert order_subdomains(["calgary", "windsorstar", "ottawa"]) == [
        "windsorstar"
    ]


def test_order_subdomains_returns_empty_when_target_city_missing(monkeypatch):
    monkeypatch.setenv("SCRAPER_CITY", "missingcity")

    assert order_subdomains(["calgary", "windsorstar", "ottawa"]) == []
