from bs4 import BeautifulSoup

import scrapper
from remembering_lancers.scraper.locations import extract_city_and_province
from remembering_lancers.scraper.parser import (
    extract_dates,
    get_publication_date_from_soup,
)
from remembering_lancers.scraper.runner import SEARCH_KEYWORD, is_alumni_obituary


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
