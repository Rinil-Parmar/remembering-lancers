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
from ..models import DistinctObituary, Obituary, ScrapeRun, ScrapeState
from .locations import CITY_PROVINCE_MAPPING, extract_city_and_province
from .parser import (
    extract_birth_and_death_dates_from_obituary,
    extract_dates,
    extract_text,
    get_publication_date_from_soup,
)


BASE_DOMAIN = "remembering.ca"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_RETRY_TOTAL = 3
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

SCRAPER_MODE_KEYWORD_SEARCH = "keyword_search"
SCRAPER_MODE_LISTING_SCAN = "listing_scan"
LISTING_SCAN_STATE_KEYWORD = "__listing__"

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


def get_scraper_mode():
    mode = os.environ.get("SCRAPER_MODE", SCRAPER_MODE_KEYWORD_SEARCH).strip().lower()
    if mode in {SCRAPER_MODE_KEYWORD_SEARCH, SCRAPER_MODE_LISTING_SCAN}:
        return mode

    logging.warning("Invalid SCRAPER_MODE=%s; using keyword_search.", mode)
    return SCRAPER_MODE_KEYWORD_SEARCH


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


def force_rescan_enabled():
    return os.environ.get("SCRAPER_FORCE_RESCAN", "false").lower() in {
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
        return max(0, int(os.environ.get("SCRAPER_EXISTING_URL_STOP_THRESHOLD", "3")))
    except ValueError:
        logging.warning("Invalid SCRAPER_EXISTING_URL_STOP_THRESHOLD; using 3.")
        return 3


def get_request_timeout():
    try:
        return max(
            1,
            int(
                os.environ.get(
                    "SCRAPER_REQUEST_TIMEOUT",
                    str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
                )
            ),
        )
    except ValueError:
        logging.warning("Invalid SCRAPER_REQUEST_TIMEOUT; using 10 seconds.")
        return DEFAULT_REQUEST_TIMEOUT_SECONDS


def get_retry_total():
    try:
        return max(
            0,
            int(os.environ.get("SCRAPER_RETRY_TOTAL", str(DEFAULT_RETRY_TOTAL))),
        )
    except ValueError:
        logging.warning("Invalid SCRAPER_RETRY_TOTAL; using 3.")
        return DEFAULT_RETRY_TOTAL


def get_max_pages():
    try:
        return max(1, int(os.environ.get("SCRAPER_MAX_PAGES", "2")))
    except ValueError:
        logging.warning("Invalid SCRAPER_MAX_PAGES; using 2.")
        return 2


def log_scraper_configuration():
    logging.info(
        (
            "Scraper configuration: mode=%s city=%s current_month_only=%s max_pages=%s "
            "keywords=%s existing_url_stop_threshold=%s "
            "resume_from_state=%s force_rescan=%s request_timeout=%s retry_total=%s"
        ),
        get_scraper_mode(),
        get_target_city() or "all",
        current_month_only_enabled(),
        get_max_pages(),
        ", ".join(get_search_keywords()),
        get_existing_url_stop_threshold(),
        resume_from_state_enabled(),
        force_rescan_enabled(),
        get_request_timeout(),
        get_retry_total(),
    )


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
    retries = Retry(
        total=get_retry_total(),
        backoff_factor=1,
        status_forcelist=[429, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session


def get_city_subdomains(session):
    logging.info("Fetching city subdomains...")
    try:
        response = session.get(
            f"https://www.{BASE_DOMAIN}/location",
            timeout=get_request_timeout(),
        )
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
    publication_date_cache = {}
    for page in range(1, get_max_pages() + 1):
        page_urls, stop_keyword = fetch_search_page_urls(
            session,
            subdomain,
            search_keyword,
            page,
            visited_search_pages,
            visited_obituaries,
            publication_date_cache,
            stop_event,
        )
        if page_urls:
            yield page, page_urls
        if stop_keyword or stop_event.is_set():
            break
        time.sleep(random.uniform(0.5, 1.5))


def build_search_url(subdomain, search_keyword, page):
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    search_path = "/obituaries/all-categories/search"
    search_params = (
        f"search_type=advanced&ap_search_keyword={quote_plus(search_keyword)}"
        "&sort_by=date&order=desc"
    )
    search_url = f"{base_url}{search_path}?{search_params}"
    return f"{search_url}&p={page}" if page > 1 else search_url


def build_listing_url(subdomain, page):
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    listing_url = f"{base_url}/obituaries/all-categories"
    return f"{listing_url}?p={page}" if page > 1 else listing_url


def fetch_listing_page_urls(session, subdomain, page, visited_listing_pages, stop_event):
    logging.info("[%s] Listing scan fetching page %s", subdomain.upper(), page)

    if stop_event.is_set():
        return [], True

    listing_url = build_listing_url(subdomain, page)
    if listing_url in visited_listing_pages:
        logging.info(
            "[%s] Listing page %s already visited, stopping city.",
            subdomain.upper(),
            page,
        )
        return [], True
    visited_listing_pages.add(listing_url)

    try:
        response = session.get(listing_url, timeout=get_request_timeout())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        base_url = f"https://{subdomain}.{BASE_DOMAIN}"
        page_obituary_urls = list(
            dict.fromkeys(
                urljoin(base_url, link["href"])
                for link in soup.select('a[href^="/obituary/"]')
            )
        )
        if not page_obituary_urls:
            logging.info(
                "[%s] Listing page %s has no obituary links; stopping city.",
                subdomain.upper(),
                page,
            )
            return [], True

        logging.info(
            "[%s] Listing page %s collected %s obituary URLs.",
            subdomain.upper(),
            page,
            len(page_obituary_urls),
        )
        return page_obituary_urls, False
    except Exception as exc:
        logging.error(
            "[%s] Error fetching listing page %s: %s",
            subdomain.upper(),
            page,
            exc,
        )
        return [], True


def fetch_search_page_urls(
    session,
    subdomain,
    search_keyword,
    page,
    visited_search_pages,
    visited_obituaries,
    publication_date_cache,
    stop_event,
):
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    logging.info(
        "[%s] Searching keyword: %s page=%s",
        subdomain.upper(),
        search_keyword,
        page,
    )

    if stop_event.is_set():
        return [], True

    current_url = build_search_url(subdomain, search_keyword, page)
    if current_url in visited_search_pages:
        logging.info(
            "[%s] Keyword '%s' page %s already visited, stopping keyword.",
            subdomain.upper(),
            search_keyword,
            page,
        )
        return [], True
    visited_search_pages.add(current_url)

    try:
        response = session.get(current_url, timeout=get_request_timeout())
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        page_obituary_urls = list(
            dict.fromkeys(
                urljoin(base_url, link["href"])
                for link in soup.select('a[href^="/obituary/"]')
            )
        )
        if not page_obituary_urls:
            logging.info(
                "[%s] Keyword '%s' page %s: no obituary links found.",
                subdomain.upper(),
                search_keyword,
                page,
            )
            return [], True

        if page == 1:
            first_obit_url = page_obituary_urls[0]
            pub_date_str, _ = get_publication_date_and_soup(session, first_obit_url)
            publication_date_cache[first_obit_url] = pub_date_str
            if current_month_only_enabled() and not is_current_month_and_year(
                pub_date_str
            ):
                logging.info(
                    (
                        "[%s] First obituary is not current for keyword '%s'. "
                        "Stopping keyword. url=%s publication_date=%s"
                    ),
                    subdomain.upper(),
                    search_keyword,
                    first_obit_url,
                    pub_date_str,
                )
                return [], True

        obituary_data = []
        for url in page_obituary_urls:
            if url in visited_obituaries:
                continue
            pub_date_str = publication_date_cache.get(url)
            if pub_date_str is None:
                pub_date_str, _ = get_publication_date_and_soup(session, url)
                publication_date_cache[url] = pub_date_str
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
        stop_keyword = False
        for item in obituary_data:
            pub_date_text = item["pub_date"].strftime("%B %d, %Y")

            if current_month_only_enabled() and not is_current_month_and_year(
                pub_date_text
            ):
                logging.info(
                    (
                        "[%s] Non-current obituary found for keyword '%s'. "
                        "Stopping keyword. url=%s publication_date=%s"
                    ),
                    subdomain.upper(),
                    search_keyword,
                    item["url"],
                    pub_date_text,
                )
                stop_keyword = True
                break

            current_page_urls.append(item["url"])

        if not current_page_urls:
            logging.info(
                "[%s] Keyword '%s' has no matching obituaries on page %s.",
                subdomain.upper(),
                search_keyword,
                page,
            )
            return [], True

        return current_page_urls, stop_keyword

    except Exception as exc:
        logging.error(
            "[%s] Error processing keyword '%s' page %s: %s",
            subdomain.upper(),
            search_keyword,
            page,
            exc,
        )
        return [], True


def get_publication_date_and_soup(session, url):
    soup_for_debug = None
    try:
        response = session.get(url, timeout=get_request_timeout())
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


def create_scrape_run():
    run = ScrapeRun(status="running", started_at=datetime.now())
    db.session.add(run)
    db.session.commit()
    logging.info("Scrape run started: run_id=%s", run.id)
    return run


def update_scrape_run(
    run,
    city=None,
    search_keyword=None,
    page_number=None,
    saved_delta=0,
    skipped_delta=0,
    duplicate_delta=0,
    status=None,
    error_message=None,
):
    if not run:
        return

    if city is not None:
        run.city = city
    if search_keyword is not None:
        run.search_keyword = search_keyword
    if page_number is not None:
        run.page_number = page_number
    if status is not None:
        run.status = status
    if error_message:
        run.error_message = error_message[:4000]

    run.saved_count = (run.saved_count or 0) + saved_delta
    run.skipped_count = (run.skipped_count or 0) + skipped_delta
    run.duplicate_count = (run.duplicate_count or 0) + duplicate_delta
    db.session.commit()


def finish_scrape_run(run, status, error_message=None):
    if not run:
        return

    run.status = status
    run.finished_at = datetime.now()
    if error_message:
        run.error_message = error_message[:4000]
    db.session.commit()
    logging.info(
        (
            "Scrape run finished: run_id=%s status=%s "
            "saved=%s skipped=%s duplicates=%s"
        ),
        run.id,
        run.status,
        run.saved_count,
        run.skipped_count,
        run.duplicate_count,
    )


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


def process_city(session, subdomain, stop_event, scrape_run=None):
    if get_scraper_mode() == SCRAPER_MODE_LISTING_SCAN:
        return process_city_listing_scan(session, subdomain, stop_event, scrape_run)

    return process_city_keyword_search(session, subdomain, stop_event, scrape_run)


def process_city_listing_scan(session, subdomain, stop_event, scrape_run=None):
    logging.info("\n%s\nProcessing city: %s\n%s", "=" * 50, subdomain.upper(), "=" * 50)

    total_alumni = 0
    visited_listing_pages = set()
    visited_obituaries = set()
    existing_url_count = 0
    resume_enabled = resume_from_state_enabled()
    force_rescan = force_rescan_enabled()
    existing_url_stop_threshold = get_existing_url_stop_threshold()

    try:
        scrape_state = get_or_create_scrape_state(
            subdomain,
            LISTING_SCAN_STATE_KEYWORD,
        )
        update_scrape_run(
            scrape_run,
            city=subdomain,
            search_keyword=LISTING_SCAN_STATE_KEYWORD,
        )

        if resume_enabled and not force_rescan and scrape_state.status == "completed":
            logging.info(
                (
                    "[%s] Listing scan state is completed; skipping. "
                    "Set SCRAPER_FORCE_RESCAN=true to scan again."
                ),
                subdomain.upper(),
            )
            update_scrape_run(scrape_run, skipped_delta=1)
            return

        if not resume_enabled:
            logging.info(
                "[%s] SCRAPER_RESUME_FROM_STATE=false; listing scan starts page 1.",
                subdomain.upper(),
            )
        elif force_rescan:
            logging.info(
                "[%s] SCRAPER_FORCE_RESCAN=true; listing scan starts from page 1.",
                subdomain.upper(),
            )

        if existing_url_stop_threshold == 0:
            logging.info(
                (
                    "[%s] Existing URL stop threshold is disabled; "
                    "duplicates will be skipped without stopping listing scan."
                ),
                subdomain.upper(),
            )

        for page_number in range(1, get_max_pages() + 1):
            if stop_event.is_set():
                break

            if (
                resume_enabled
                and not force_rescan
                and scrape_state.status == "running"
                and scrape_state.page_number is not None
                and page_number < scrape_state.page_number
            ):
                logging.info(
                    "[%s] Listing resume state skipping page %s.",
                    subdomain.upper(),
                    page_number,
                )
                continue

            update_scrape_run(
                scrape_run,
                city=subdomain,
                search_keyword=LISTING_SCAN_STATE_KEYWORD,
                page_number=page_number,
            )
            page_urls, stop_city = fetch_listing_page_urls(
                session,
                subdomain,
                page_number,
                visited_listing_pages,
                stop_event,
            )

            if resume_enabled and not force_rescan:
                page_urls = resume_page_urls(
                    page_number,
                    page_urls,
                    scrape_state,
                    subdomain,
                )

            for url in page_urls:
                if stop_event.is_set():
                    logging.info(
                        "[%s] Stop event detected during listing URL loop.",
                        subdomain.upper(),
                    )
                    break

                if url in visited_obituaries:
                    continue

                if obituary_url_exists(url):
                    visited_obituaries.add(url)
                    existing_url_count += 1
                    update_scrape_run(scrape_run, duplicate_delta=1)
                    if existing_url_stop_threshold > 0:
                        logging.info(
                            "[%s] Existing obituary reached %s/%s: %s",
                            subdomain.upper(),
                            existing_url_count,
                            existing_url_stop_threshold,
                            url,
                        )
                    else:
                        logging.info(
                            "[%s] Existing obituary duplicate skipped: %s",
                            subdomain.upper(),
                            url,
                        )
                    update_scrape_state(scrape_state, page_number, url)
                    if (
                        existing_url_stop_threshold > 0
                        and existing_url_count >= existing_url_stop_threshold
                    ):
                        logging.info(
                            "[%s] Existing obituary threshold reached, stopping listing scan: %s",
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
                result = None
                for attempt in range(3):
                    try:
                        logging.info(
                            "[%s] Listing scan attempt %s to process obituary: %s",
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
                            update_scrape_run(scrape_run, saved_delta=1)
                        else:
                            update_scrape_run(scrape_run, skipped_delta=1)
                        success = True
                        break
                    except requests.exceptions.RequestException as exc:
                        logging.warning(
                            "[%s] Listing scan attempt %s failed for %s: %s",
                            subdomain.upper(),
                            attempt + 1,
                            url,
                            exc,
                        )
                        time.sleep(2**attempt)

                if not success:
                    logging.error(
                        "[%s] Failed to process listing obituary after 3 attempts: %s",
                        subdomain.upper(),
                        url,
                    )
                    update_scrape_run(
                        scrape_run,
                        skipped_delta=1,
                        error_message=f"Failed to process obituary: {url}",
                    )

                update_scrape_state(scrape_state, page_number, url)
                time.sleep(random.uniform(0.7, 1.3))

            if stop_city or stop_event.is_set():
                if stop_city:
                    update_scrape_state(
                        scrape_state,
                        page_number,
                        scrape_state.last_processed_url,
                        status="completed",
                    )
                break

            time.sleep(random.uniform(0.5, 1.5))

    except Exception as exc:
        logging.error("[%s] Critical error processing listing scan: %s", subdomain.upper(), exc)
        update_scrape_run(
            scrape_run,
            city=subdomain,
            status="failed",
            error_message=f"{subdomain}: {exc}",
        )
    finally:
        logging.info("[%s] Completed. Alumni found: %s", subdomain.upper(), total_alumni)


def process_city_keyword_search(session, subdomain, stop_event, scrape_run=None):
    logging.info("\n%s\nProcessing city: %s\n%s", "=" * 50, subdomain.upper(), "=" * 50)

    total_alumni = 0
    visited_search_pages = set()
    visited_obituaries = set()
    publication_date_cache = {}

    try:
        resume_enabled = resume_from_state_enabled()
        force_rescan = force_rescan_enabled()
        existing_url_stop_threshold = get_existing_url_stop_threshold()
        search_keywords = get_search_keywords()
        keyword_states = {}
        active_keywords = []
        existing_url_counts = {}
        update_scrape_run(scrape_run, city=subdomain)

        for search_keyword in search_keywords:
            scrape_state = get_or_create_scrape_state(subdomain, search_keyword)
            keyword_states[search_keyword] = scrape_state
            existing_url_counts[search_keyword] = 0

            if (
                resume_enabled
                and not force_rescan
                and scrape_state.status == "completed"
            ):
                logging.info(
                    (
                        "[%s] Scrape state is completed for keyword '%s'; "
                        "skipping. Set SCRAPER_FORCE_RESCAN=true to scan again."
                    ),
                    subdomain.upper(),
                    search_keyword,
                )
                update_scrape_run(
                    scrape_run,
                    city=subdomain,
                    search_keyword=search_keyword,
                    skipped_delta=1,
                )
                continue

            active_keywords.append(search_keyword)

        if not resume_enabled:
            logging.info(
                "[%s] SCRAPER_RESUME_FROM_STATE=false; starting from page 1.",
                subdomain.upper(),
            )
        elif force_rescan:
            logging.info(
                "[%s] SCRAPER_FORCE_RESCAN=true; scanning completed state again.",
                subdomain.upper(),
            )

        if existing_url_stop_threshold == 0:
            logging.info(
                (
                    "[%s] Existing URL stop threshold is disabled; "
                    "duplicates will be skipped without stopping the scan."
                ),
                subdomain.upper(),
            )

        for page_number in range(1, get_max_pages() + 1):
            if stop_event.is_set() or not active_keywords:
                break

            logging.info("[%s] Page-first scan starting page %s", subdomain.upper(), page_number)
            page_url_sources = {}
            keywords_to_stop_after_page = set()

            for search_keyword in list(active_keywords):
                if stop_event.is_set():
                    break

                update_scrape_run(
                    scrape_run,
                    city=subdomain,
                    search_keyword=search_keyword,
                    page_number=page_number,
                )
                if stop_event.is_set():
                    logging.info(
                        "[%s] Stop event detected during page URL processing.",
                        subdomain.upper(),
                    )
                    break

                scrape_state = keyword_states[search_keyword]
                if (
                    resume_enabled
                    and not force_rescan
                    and scrape_state.status == "running"
                    and scrape_state.page_number is not None
                    and page_number < scrape_state.page_number
                ):
                    logging.info(
                        "[%s] Resume state skipping keyword '%s' page %s.",
                        subdomain.upper(),
                        search_keyword,
                        page_number,
                    )
                    continue

                page_urls, stop_keyword = fetch_search_page_urls(
                    session,
                    subdomain,
                    search_keyword,
                    page_number,
                    visited_search_pages,
                    visited_obituaries,
                    publication_date_cache,
                    stop_event,
                )

                if resume_enabled and not force_rescan:
                    page_urls = resume_page_urls(
                        page_number,
                        page_urls,
                        scrape_state,
                        subdomain,
                    )

                for url in page_urls:
                    page_url_sources.setdefault(url, set()).add(search_keyword)

                if stop_keyword:
                    keywords_to_stop_after_page.add(search_keyword)

            if stop_event.is_set():
                break

            if not page_url_sources:
                for search_keyword in keywords_to_stop_after_page:
                    if search_keyword in active_keywords:
                        active_keywords.remove(search_keyword)
                if not active_keywords:
                    break
                continue

            logging.info(
                "[%s] Page %s collected %s unique obituary URLs from keywords.",
                subdomain.upper(),
                page_number,
                len(page_url_sources),
            )

            for url, source_keywords in page_url_sources.items():
                if stop_event.is_set():
                    logging.info(
                        "[%s] Stop event detected during obituary URL loop.",
                        subdomain.upper(),
                    )
                    break

                source_keywords = {
                    search_keyword
                    for search_keyword in source_keywords
                    if search_keyword in active_keywords
                }
                if not source_keywords:
                    continue

                if url in visited_obituaries:
                    logging.debug(
                        "[%s] Obituary URL already visited: %s. Skipping.",
                        subdomain.upper(),
                        url,
                    )
                    continue

                if obituary_url_exists(url):
                    visited_obituaries.add(url)
                    update_scrape_run(scrape_run, duplicate_delta=1)
                    for search_keyword in source_keywords:
                        scrape_state = keyword_states[search_keyword]
                        existing_url_counts[search_keyword] += 1
                        if existing_url_stop_threshold > 0:
                            logging.info(
                                (
                                    "[%s] Existing obituary reached %s/%s "
                                    "for keyword '%s': %s"
                                ),
                                subdomain.upper(),
                                existing_url_counts[search_keyword],
                                existing_url_stop_threshold,
                                search_keyword,
                                url,
                            )
                        else:
                            logging.info(
                                "[%s] Existing obituary duplicate skipped: %s",
                                subdomain.upper(),
                                url,
                            )
                        update_scrape_state(scrape_state, page_number, url)
                        if (
                            existing_url_stop_threshold > 0
                            and existing_url_counts[search_keyword]
                            >= existing_url_stop_threshold
                            and search_keyword in active_keywords
                        ):
                            logging.info(
                                (
                                    "[%s] Existing obituary threshold reached, "
                                    "stopping keyword '%s': %s"
                                ),
                                subdomain.upper(),
                                search_keyword,
                                url,
                            )
                            update_scrape_state(
                                scrape_state,
                                page_number,
                                url,
                                status="completed",
                            )
                            active_keywords.remove(search_keyword)
                    continue

                for search_keyword in source_keywords:
                    existing_url_counts[search_keyword] = 0

                success = False
                result = None
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
                            update_scrape_run(scrape_run, saved_delta=1)
                        else:
                            update_scrape_run(scrape_run, skipped_delta=1)
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
                    update_scrape_run(
                        scrape_run,
                        skipped_delta=1,
                        error_message=f"Failed to process obituary: {url}",
                    )

                for search_keyword in source_keywords:
                    update_scrape_state(
                        keyword_states[search_keyword],
                        page_number,
                        url,
                    )
                time.sleep(random.uniform(0.7, 1.3))

            for search_keyword in keywords_to_stop_after_page:
                if search_keyword in active_keywords:
                    active_keywords.remove(search_keyword)

            time.sleep(random.uniform(0.5, 1.5))

    except Exception as exc:
        logging.error("[%s] Critical error processing city: %s", subdomain.upper(), exc)
        update_scrape_run(
            scrape_run,
            city=subdomain,
            status="failed",
            error_message=f"{subdomain}: {exc}",
        )
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
        response = session.get(url, timeout=get_request_timeout())
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
    log_scraper_configuration()
    scrape_run = create_scrape_run()
    session = configure_session()

    try:
        subdomains = get_city_subdomains(session)
        if not subdomains:
            logging.error("No city subdomains found. Aborting.")
            finish_scrape_run(scrape_run, "failed", "No city subdomains found.")
            return

        subdomains = order_subdomains(subdomains)
        if not subdomains:
            logging.error("No matching city subdomains to process. Aborting.")
            finish_scrape_run(
                scrape_run,
                "failed",
                "No matching city subdomains to process.",
            )
            return

        logging.info("City scrape order: %s", ", ".join(subdomains))
        logging.info("Found %s city subdomains to process.", len(subdomains))

        for subdomain in subdomains:
            if stop_event.is_set():
                logging.info("Scraping stopped by system request")
                break

            process_city(session, subdomain, stop_event, scrape_run)

        db.session.refresh(scrape_run)
        if scrape_run.status == "failed":
            finish_scrape_run(scrape_run, "failed", scrape_run.error_message)
        elif stop_event.is_set():
            finish_scrape_run(scrape_run, "stopped")
        else:
            finish_scrape_run(scrape_run, "success")
    except Exception as exc:
        logging.exception("Obituary scraping process failed.")
        finish_scrape_run(scrape_run, "failed", str(exc))
    finally:
        logging.info("Obituary scraping process completed or stopped.")
