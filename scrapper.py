"""Backward-compatible imports for the packaged scraper.

New code should import from ``remembering_lancers.scraper`` modules directly.
This wrapper keeps older commands/tests that import ``scrapper`` working.
"""

from remembering_lancers.scraper.locations import (
    CITY_PROVINCE_MAPPING,
    extract_city_and_province,
)
from remembering_lancers.scraper.parser import (
    extract_birth_and_death_dates_from_obituary,
    extract_dates,
    extract_text,
    extract_year_from_date,
    get_publication_date_from_soup,
    parse_date,
)
from remembering_lancers.scraper.runner import (
    ALUMNI_KEYWORDS,
    BASE_DOMAIN,
    SEARCH_KEYWORD,
    USER_AGENTS,
    configure_session,
    get_city_subdomains,
    get_coordinates,
    get_publication_date_and_soup,
    is_alumni_obituary,
    is_current_month_and_year,
    is_current_publication_date,
    main,
    process_city,
    process_obituary,
    process_search_pagination,
)

__all__ = [
    "ALUMNI_KEYWORDS",
    "BASE_DOMAIN",
    "CITY_PROVINCE_MAPPING",
    "SEARCH_KEYWORD",
    "USER_AGENTS",
    "configure_session",
    "extract_birth_and_death_dates_from_obituary",
    "extract_city_and_province",
    "extract_dates",
    "extract_text",
    "extract_year_from_date",
    "get_city_subdomains",
    "get_coordinates",
    "get_publication_date_and_soup",
    "get_publication_date_from_soup",
    "is_alumni_obituary",
    "is_current_month_and_year",
    "is_current_publication_date",
    "main",
    "parse_date",
    "process_city",
    "process_obituary",
    "process_search_pagination",
]


if __name__ == "__main__":
    pass
