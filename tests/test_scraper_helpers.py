from bs4 import BeautifulSoup

import scrapper


def test_extract_city_and_province_from_known_subdomain():
    assert scrapper.extract_city_and_province(
        "https://windsorstar.remembering.ca/obituary/example-123"
    ) == ("Windsor", "Ontario")


def test_extract_city_and_province_returns_none_for_unknown_subdomain():
    assert (
        scrapper.extract_city_and_province(
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

    assert scrapper.get_publication_date_from_soup(soup) == "June 10, 2026"


def test_extract_dates_from_obit_dates_tag():
    soup = BeautifulSoup(
        '<h2 class="obit-dates"><span>January 01, 1950</span><span>June 01, 2026</span></h2>',
        "html.parser",
    )

    assert scrapper.extract_dates(soup) == (
        "January 01, 1950",
        "June 01, 2026",
    )
