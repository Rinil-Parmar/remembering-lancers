import os
import random
import time
import logging
from datetime import datetime
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from geopy.geocoders import Nominatim
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from ..extensions import db
from ..models import DistinctObituary, Obituary, ScrapeState
from .locations import CITY_PROVINCE_MAPPING, extract_city_and_province
from .parser import (
    extract_birth_and_death_dates_from_obituary,
    extract_dates,
    extract_text,
    get_publication_date_from_soup,
)


BASE_DOMAIN = "remembering.ca"
DEFAULT_SEARCH_KEYWORDS = [
    "University of Windsor",
    "UWindsor",
    "Windsor University",
]

DEFAULT_ALUMNI_KEYWORDS = {
    "University of Windsor",
    "UWindsor",
    "Windsor University",
    "Assumption University",
    "Assumption College",
    "Windsor Law",
}

PRIORITY_SUBDOMAINS = [
    "windsorstar",
    "chathamdailynews",
    "theobserver",
    "lfpress",
    "stratfordbeaconherald",
    "stthomastimesjournal",
    "woodstocksentinelreview",
    "brantfordexpositor",
    "thewhig",
    "ottawa",
    "torontosun",
]

# Backward-compatible names for older imports and tests.
SEARCH_KEYWORD = "Windsor University"
ALUMNI_KEYWORDS = DEFAULT_ALUMNI_KEYWORDS

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) "
    "Gecko/20100101 Firefox/89.0",
]

geolocator = Nominatim(user_agent="obituary_mapper")


def get_search_keywords():
    raw_keywords = os.environ.get("SCRAPER_SEARCH_KEYWORDS")
    if not raw_keywords:
        return DEFAULT_SEARCH_KEYWORDS

    return [
        keyword.strip()
        for keyword in raw_keywords.split(",")
        if keyword.strip()
    ]


def current_month_only_enabled():
    return os.environ.get("SCRAPER_CURRENT_MONTH_ONLY", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def resume_from_state_enabled():
    return os.environ.get("SCRAPER_RESUME_FROM_STATE", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_target_city():
    city = os.environ.get("SCRAPER_CITY", "").strip().lower()
    return city or None


def get_existing_url_stop_threshold():
    try:
        return max(1, int(os.environ.get("SCRAPER_EXISTING_URL_STOP_THRESHOLD", "3")))
    except ValueError:
        logging.warning("Invalid SCRAPER_EXISTING_URL_STOP_THRESHOLD; using 3.")
        return 3


def order_subdomains(subdomains):
    target_city = get_target_city()
    available_subdomains = list(dict.fromkeys(subdomains))

    if target_city:
        if target_city in available_subdomains:
            return [target_city]

        logging.warning(
            "SCRAPER_CITY=%s was not found in available subdomains.",
            target_city,
        )
        return []

    priority = [
        subdomain
        for subdomain in PRIORITY_SUBDOMAINS
        if subdomain in available_subdomains
    ]
    remaining = [
        subdomain
        for subdomain in available_subdomains
        if subdomain not in priority
    ]

    return priority + remaining


def configure_session():
    session = requests.Session()
    retries = Retry(total=100, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session


def get_city_subdomains(session):
    logging.info("Fetching city subdomains...")
    try:
        response = session.get(f"https://www.{BASE_DOMAIN}/location")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        subdomains = set()
        for link in soup.find_all("a", href=True):
            parsed = urlparse(link["href"])
            if parsed.netloc.endswith(BASE_DOMAIN):
                parts = parsed.netloc.split(".")
                if parts[0].lower() != "www" and len(parts) > 2:
                    subdomains.add(parts[0].lower())
        return sorted(subdomains)
    except Exception as exc:
        logging.error("Error fetching city subdomains: %s", exc)
        return []


def process_search_pagination(
    session,
    subdomain,
    search_keyword,
    visited_search_pages,
    visited_obituaries,
    stop_event,
):
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    search_path = "/obituaries/all-categories/search"
    search_params = (
        f"search_type=advanced&ap_search_keyword={quote_plus(search_keyword)}"
        "&sort_by=date&order=desc"
    )
    search_url = f"{base_url}{search_path}?{search_params}"
    logging.info("[%s] Searching keyword: %s", subdomain.upper(), search_keyword)

    page = 1
    max_pages = int(os.environ.get("SCRAPER_MAX_PAGES", "2"))
    first_page_processed = False

    while page <= max_pages and not stop_event.is_set():
        logging.info("[%s] Pagination - Starting page %s", subdomain.upper(), page)
        current_url = f"{search_url}&p={page}" if page > 1 else search_url

        if current_url in visited_search_pages:
            logging.info(
                "[%s] Page %s already visited, stopping pagination.",
                subdomain.upper(),
                page,
            )
            break
        visited_search_pages.add(current_url)

        try:
            response = session.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            obit_links = soup.select('a[href^="/obituary/"]')
            if not obit_links:
                logging.info(
                    "[%s] Page %s: No obituary links found, stopping pagination.",
                    subdomain.upper(),
                    page,
                )
                break

            if page == 1 and not first_page_processed:
                first_obit_url = urljoin(base_url, obit_links[0]["href"])
                pub_date_str, _ = get_publication_date_and_soup(session, first_obit_url)
                if current_month_only_enabled() and not is_current_month_and_year(
                    pub_date_str
                ):
                    logging.info(
                        (
                            "[%s] First obituary is not current. "
                            "Skipping city. url=%s publication_date=%s"
                        ),
                        subdomain.upper(),
                        first_obit_url,
                        pub_date_str,
                    )
                    return
                first_page_processed = True

            obituary_data = []
            for link in obit_links:
                url = urljoin(base_url, link["href"])
                if url in visited_obituaries:
                    continue
                pub_date_str, _ = get_publication_date_and_soup(session, url)
                if not pub_date_str:
                    continue
                try:
                    pub_date = date_parser.parse(pub_date_str, fuzzy=True)
                    obituary_data.append({"url": url, "pub_date": pub_date})
                except Exception as exc:
                    logging.error(
                        "[%s] Error parsing date %s: %s",
                        subdomain.upper(),
                        pub_date_str,
                        exc,
                    )

            obituary_data.sort(key=lambda item: item["pub_date"], reverse=True)

            current_page_urls = []
            for item in obituary_data:
                pub_date_text = item["pub_date"].strftime("%B %d, %Y")

                if current_month_only_enabled() and not is_current_month_and_year(
                    pub_date_text
                ):
                    logging.info(
                        (
                            "[%s] Non-current obituary found. "
                            "Stopping city processing. url=%s publication_date=%s"
                        ),
                        subdomain.upper(),
                        item["url"],
                        pub_date_text,
                    )
                    if current_page_urls:
                        yield page, current_page_urls
                    return

                current_page_urls.append(item["url"])

            if not current_page_urls:
                logging.info(
                    "[%s] No matching obituaries on page %s. Stopping.",
                    subdomain.upper(),
                    page,
                )
                return

            yield page, current_page_urls

            page += 1
            time.sleep(random.uniform(0.5, 1.5))

        except Exception as exc:
            logging.error(
                "[%s] Error processing page %s: %s", subdomain.upper(), page, exc
            )
            break


def get_publication_date_and_soup(session, url):
    soup_for_debug = None
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup_for_debug = BeautifulSoup(response.text, "html.parser")
        publication_date = get_publication_date_from_soup(soup_for_debug)
        logging.info("Fetched publication date for %s: %s", url, publication_date)
        return publication_date, soup_for_debug
    except Exception as exc:
        logging.error("Error fetching %s: %s", url, exc)
        return None, soup_for_debug


def obituary_url_exists(url):
    return Obituary.query.filter_by(obituary_url=url).first() is not None


def get_or_create_scrape_state(subdomain, search_keyword):
    state = ScrapeState.query.filter_by(
        subdomain=subdomain,
        search_keyword=search_keyword,
    ).first()
    if state:
        return state

    state = ScrapeState(
        subdomain=subdomain,
        search_keyword=search_keyword,
        status="running",
    )
    db.session.add(state)
    db.session.commit()
    return state


def update_scrape_state(state, page_number, obituary_url, status="running"):
    state.page_number = page_number
    state.last_processed_url = obituary_url
    state.status = status
    state.updated_at = datetime.now()
    db.session.commit()


def resume_page_urls(page_number, page_urls, state, subdomain):
    if (
        state.status != "running"
        or state.page_number is None
        or not state.last_processed_url
    ):
        return page_urls

    if page_number < state.page_number:
        logging.info(
            "[%s] Resume state skipping previously processed page %s.",
            subdomain.upper(),
            page_number,
        )
        return []

    if page_number != state.page_number:
        return page_urls

    if state.last_processed_url not in page_urls:
        logging.info(
            "[%s] Resume URL not found on page %s; processing full page.",
            subdomain.upper(),
            page_number,
        )
        return page_urls

    resume_index = page_urls.index(state.last_processed_url) + 1
    logging.info(
        "[%s] Resuming page %s after URL: %s",
        subdomain.upper(),
        page_number,
        state.last_processed_url,
    )
    return page_urls[resume_index:]


def process_city(session, subdomain, stop_event):
    logging.info("\n%s\nProcessing city: %s\n%s", "=" * 50, subdomain.upper(), "=" * 50)

    total_alumni = 0
    visited_search_pages = set()
    visited_obituaries = set()

    try:
        for search_keyword in get_search_keywords():
            if stop_event.is_set():
                break

            resume_enabled = resume_from_state_enabled()
            scrape_state = get_or_create_scrape_state(subdomain, search_keyword)
            if not resume_enabled:
                logging.info(
                    "[%s] SCRAPER_RESUME_FROM_STATE=false; starting from page 1.",
                    subdomain.upper(),
                )
            existing_url_count = 0
            existing_url_stop_threshold = get_existing_url_stop_threshold()

            page_generator = process_search_pagination(
                session,
                subdomain,
                search_keyword,
                visited_search_pages,
                visited_obituaries,
                stop_event,
            )

            for page_number, page_urls in page_generator:
                if stop_event.is_set():
                    logging.info(
                        "[%s] Stop event detected during page URL processing.",
                        subdomain.upper(),
                    )
                    break

                if resume_enabled:
                    page_urls = resume_page_urls(
                        page_number,
                        page_urls,
                        scrape_state,
                        subdomain,
                    )

                for url in page_urls:
                    if stop_event.is_set():
                        logging.info(
                            "[%s] Stop event detected during obituary URL loop.",
                            subdomain.upper(),
                        )
                        break

                    if url in visited_obituaries:
                        logging.debug(
                            "[%s] Obituary URL already visited: %s. Skipping.",
                            subdomain.upper(),
                            url,
                        )
                        continue

                    if obituary_url_exists(url):
                        existing_url_count += 1
                        logging.info(
                            (
                                "[%s] Existing obituary reached %s/%s: %s"
                            ),
                            subdomain.upper(),
                            existing_url_count,
                            existing_url_stop_threshold,
                            url,
                        )
                        update_scrape_state(
                            scrape_state,
                            page_number,
                            url,
                        )
                        if existing_url_count >= existing_url_stop_threshold:
                            logging.info(
                                (
                                    "[%s] Existing obituary reached, "
                                    "stopping city: %s"
                                ),
                                subdomain.upper(),
                                url,
                            )
                            update_scrape_state(
                                scrape_state,
                                page_number,
                                url,
                                status="completed",
                            )
                            return
                        continue

                    existing_url_count = 0

                    success = False
                    for attempt in range(3):
                        try:
                            logging.info(
                                "[%s] Attempt %s to process obituary: %s",
                                subdomain.upper(),
                                attempt + 1,
                                url,
                            )
                            result = process_obituary(
                                session,
                                db.session,
                                url,
                                visited_obituaries,
                                stop_event,
                            )
                            if result and result["is_alumni"]:
                                total_alumni += 1
                            success = True
                            break
                        except requests.exceptions.RequestException as exc:
                            logging.warning(
                                "[%s] Attempt %s failed for %s: %s",
                                subdomain.upper(),
                                attempt + 1,
                                url,
                                exc,
                            )
                            time.sleep(2**attempt)

                    if not success:
                        logging.error(
                            "[%s] Failed to process obituary after 3 attempts: %s",
                            subdomain.upper(),
                            url,
                        )

                    update_scrape_state(scrape_state, page_number, url)
                    time.sleep(random.uniform(0.7, 1.3))

    except Exception as exc:
        logging.error("[%s] Critical error processing city: %s", subdomain.upper(), exc)
    finally:
        logging.info("[%s] Completed. Alumni found: %s", subdomain.upper(), total_alumni)


def is_current_publication_date(publication_date_str):
    return is_current_month_and_year(publication_date_str)


def is_current_month_and_year(publication_date_str):
    if not publication_date_str:
        return False
    try:
        now = datetime.now()
        pub_date = date_parser.parse(publication_date_str, fuzzy=True).date()
        return pub_date.year == now.year and pub_date.month == now.month
    except Exception as exc:
        logging.error("Date check error: %s", exc)
        return False


def get_matching_alumni_keyword(content_text):
    normalized_content = (content_text or "").casefold()

    for keyword in DEFAULT_ALUMNI_KEYWORDS:
        if keyword.casefold() in normalized_content:
            return keyword

    return None


def is_alumni_obituary(content_text):
    return get_matching_alumni_keyword(content_text) is not None


def extract_obituary_content(soup, subdomain, url):
    selectors = [
        "span.details-copy",
        ".details-copy",
        "article",
        "main",
    ]

    for selector in selectors:
        content = soup.select_one(selector)
        content_text = extract_text(content)
        if content_text and content_text != "N/A":
            logging.info(
                "[%s] Obituary content extracted with selector: %s",
                subdomain,
                selector,
            )
            return content_text

    logging.warning("[%s] Obituary content missing for URL: %s", subdomain, url)
    return ""


def clean_obituary_name(name_text):
    if not name_text:
        return ""

    cleaned_name = " ".join(name_text.split())
    for suffix in (" Obituary", " obituary"):
        if cleaned_name.endswith(suffix):
            cleaned_name = cleaned_name[: -len(suffix)]
    return cleaned_name.strip()


def split_obituary_name(full_name):
    cleaned_name = clean_obituary_name(full_name)
    name_parts = cleaned_name.split()

    if len(name_parts) < 2:
        return None, None

    return " ".join(name_parts[:-1]), name_parts[-1].capitalize()


def extract_obituary_name(soup):
    old_name_tag = soup.find("h1", class_="obit-name")
    old_last_name_tag = soup.find("span", class_="obit-lastname-upper")
    if old_name_tag and old_last_name_tag:
        raw_full_name = extract_text(old_name_tag)
        raw_last_name = extract_text(old_last_name_tag)
        first_name = raw_full_name.replace(raw_last_name, "").strip()
        last_name = raw_last_name.capitalize()
        if first_name and last_name:
            return first_name, last_name

    selectors = [
        '[data-testid="desktop-menu-fullname"]',
        '[data-testid="mobile-menu-fullname"]',
        '[data-testid="main-fullname"]',
        "h1",
    ]
    for selector in selectors:
        element = soup.select_one(selector)
        first_name, last_name = split_obituary_name(extract_text(element))
        if first_name and last_name:
            return first_name, last_name

    meta_selectors = [
        ('meta[property="og:title"]', "content"),
        ('meta[name="twitter:title"]', "content"),
        ("title", None),
    ]
    for selector, attribute in meta_selectors:
        element = soup.select_one(selector)
        if not element:
            continue

        raw_value = element.get(attribute, "") if attribute else element.get_text()
        title_name = raw_value.split(" Obituary", 1)[0]
        first_name, last_name = split_obituary_name(title_name)
        if first_name and last_name:
            return first_name, last_name

    return None, None


def build_obituary_payload(
    url,
    first_name,
    last_name,
    birth_date,
    death_date,
    city,
    province,
    publication_date,
    content_text,
    donation_info,
    funeral_home,
    tags,
    latitude,
    longitude,
):
    return {
        "name": f"{first_name} {last_name}",
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": birth_date,
        "death_date": death_date,
        "donation_information": donation_info,
        "obituary_url": url,
        "city": city,
        "province": province,
        "is_alumni": True,
        "family_information": content_text,
        "funeral_home": funeral_home,
        "tags": tags,
        "publication_date": publication_date,
        "latitude": latitude,
        "longitude": longitude,
    }


def process_obituary(session, db_session, url, visited_obituaries, stop_event):
    time.sleep(0.2)
    if stop_event.is_set():
        logging.info("Scraping stopped by user request before obituary processing.")
        return None

    parsed = urlparse(url)
    subdomain = parsed.hostname.split(".")[0].upper() if parsed.hostname else "UNKNOWN"
    logging.info("[%s] Processing obituary URL: %s", subdomain, url)

    if url in visited_obituaries:
        logging.debug("[%s] Obituary already visited: %s. Skipping.", subdomain, url)
        return None
    visited_obituaries.add(url)

    try:
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        first_name, last_name = extract_obituary_name(soup)
        if not first_name or not last_name:
            logging.warning(
                "[%s] Could not find name components for obituary: %s. Skipping.",
                subdomain,
                url,
            )
            return None

        content_text = extract_obituary_content(soup, subdomain, url)
        matched_alumni_keyword = get_matching_alumni_keyword(content_text)
        alumni = matched_alumni_keyword is not None

        publication_date_str = get_publication_date_from_soup(soup)
        logging.info(
            "[%s] Publication date for obituary url=%s publication_date=%s",
            subdomain,
            url,
            publication_date_str,
        )
        try:
            publication_date = (
                date_parser.parse(publication_date_str) if publication_date_str else None
            )
        except Exception as exc:
            logging.error("[%s] Failed to parse publication date: %s", subdomain, exc)
            publication_date = None

        tags = "new"

        if not alumni:
            logging.info(
                (
                    "[%s] Obituary skipped as non-alumni, "
                    "no alumni keyword matched: %s"
                ),
                subdomain,
                url,
            )
            return {
                "name": f"{first_name} {last_name}",
                "is_alumni": False,
                "url": url,
                "publication_date": publication_date,
                "tags": tags,
            }

        existing_obituary = Obituary.query.filter_by(obituary_url=url).first()
        if existing_obituary:
            logging.info(
                (
                    "[%s] Duplicate obituary URL found, skipping insert. "
                    "id=%s name=%s url=%s"
                ),
                subdomain,
                existing_obituary.id,
                existing_obituary.name,
                url,
            )
            return {
                "name": existing_obituary.name,
                "is_alumni": existing_obituary.is_alumni,
                "url": url,
                "publication_date": existing_obituary.publication_date,
                "tags": existing_obituary.tags,
            }

        logging.info(
            "[%s] Alumni keyword matched: %s url=%s",
            subdomain,
            matched_alumni_keyword,
            url,
        )

        donation_keywords = ["donation", "charity", "memorial fund", "contributions"]
        donation_mentions = [
            sentence
            for sentence in content_text.split(". ")
            if any(keyword in sentence.lower() for keyword in donation_keywords)
        ]
        donation_info = "; ".join(donation_mentions)

        funeral_home = extract_text(soup.find("span", class_="obit-fh"))

        obit_dates_tag = soup.find("h2", class_="obit-dates")
        if obit_dates_tag and obit_dates_tag.get_text(strip=True):
            birth_date, death_date = extract_dates(soup)
        else:
            birth_date, death_date = extract_birth_and_death_dates_from_obituary(
                content_text
            )

        city_province_result = extract_city_and_province(url)
        if not city_province_result:
            logging.warning(
                "[%s] City and province not found for URL: %s. Skipping obituary.",
                subdomain,
                url,
            )
            return None

        city, province = city_province_result
        latitude, longitude = get_coordinates(city, province)

        payload = build_obituary_payload(
            url,
            first_name,
            last_name,
            birth_date,
            death_date,
            city,
            province,
            publication_date,
            content_text,
            donation_info,
            funeral_home,
            tags,
            latitude,
            longitude,
        )

        obituary_entry = Obituary(**payload)
        db_session.add(obituary_entry)
        db_session.flush()

        distinct_exists = DistinctObituary.query.filter_by(
            obituary_url=url
        ).first()
        if not distinct_exists:
            distinct_entry = DistinctObituary(**payload)
            db_session.add(distinct_entry)
            db_session.flush()
        else:
            distinct_entry = distinct_exists

        db_session.commit()
        logging.info(
            "[%s] Alumni obituary saved: obituary_id=%s distinct_id=%s name=%s",
            subdomain,
            obituary_entry.id,
            distinct_entry.id,
            payload["name"],
        )
        return {
            "name": payload["name"],
            "is_alumni": True,
            "url": url,
            "publication_date": publication_date,
            "tags": tags,
        }

    except Exception as exc:
        db_session.rollback()
        logging.error("[%s] Error processing obituary %s: %s", subdomain, url, exc)
        return None


def get_coordinates(city, province):
    try:
        location = geolocator.geocode(f"{city}, {province}, Canada", timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as exc:
        logging.error("Geocoding error for %s, %s: %s", city, province, exc)
    return None, None


def main(stop_event):
    logging.info("Starting obituary scraping process.")
    session = configure_session()

    subdomains = get_city_subdomains(session)
    if not subdomains:
        logging.error("No city subdomains found. Aborting.")
        return

    subdomains = order_subdomains(subdomains)
    if not subdomains:
        logging.error("No matching city subdomains to process. Aborting.")
        return

    logging.info("City scrape order: %s", ", ".join(subdomains))
    logging.info("Found %s city subdomains to process.", len(subdomains))

    for subdomain in subdomains:
        if stop_event.is_set():
            logging.info("Scraping stopped by system request")
            break

        process_city(session, subdomain, stop_event)

    logging.info("Obituary scraping process completed or stopped.")
