import time
import random
import logging
import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import spacy
import re
from datetime import datetime
from dateutil import parser

from requests.adapters import HTTPAdapter
from urllib3 import Retry

from urllib.parse import urlparse

from models import Obituary, DistinctObituary, db # Import DistinctObituary model
from geopy.geocoders import Nominatim
# from app import scraping_active

# Load spaCy NLP Model for Named Entity Recognition (NER)
nlp = spacy.load("en_core_web_sm")

import json

# STATE_FILE = "state.json"  <- Removed STATE_FILE constant

# def load_state():  <- Removed load_state function
#     """Load the saved state from a file"""
#     if os.path.exists(STATE_FILE):
#         with open(STATE_FILE, 'r') as file:
#             return json.load(file)
#     return {}

# def save_state(state):  <- Removed save_state function
#     """Save the current state to a file"""
#     with open(STATE_FILE, 'w') as file:
#         json.dump(state, file, indent=4)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Constants
BASE_DOMAIN = "remembering.ca"
SEARCH_KEYWORD = "Windsor", "University"
ALUMNI_KEYWORDS = {"University of Windsor", "UWindsor", "Windsor University"}
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
]

def configure_session():
    """Configure HTTP session with retries and user-agent rotation"""
    session = requests.Session()
    retries = Retry(total=100, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return session

CITY_PROVINCE_MAPPING = {
"airdrieecho": ("Airdrie", "Alberta"),
"thecragandcanyon": ("Banff", "Alberta"),
"thebeaumontnews": ("Beaumont", "Alberta"),
"calgary": ("Calgary", "Alberta"),
"cochranetimes": ("Cochrane", "Alberta"),
"coldlakesun": ("Cold Lake", "Alberta"),
"devondispatch": ("Edmonton", "Alberta"),
"draytonvalleywesternreview": ("Edmonton", "Alberta"),
"edmonton": ("Edmonton", "Alberta"),
"edmontonjournal": ("Edmonton", "Alberta"),
"edmontonsun": ("Edmonton", "Alberta"),
"edson": ("Edson", "Alberta"),
"fairviewpost": ("Grande Prairie", "Alberta"),
"fortmcmurraytoday": ("Fort McMurray", "Alberta"),
"fortsaskatchewanrecord": ("Fort Saskatchewan", "Alberta"),
"peacecountrysun": ("Grande Prairie", "Alberta"),
"hannaherald": ("Drumheller", "Alberta"),
"highrivertimes": ("High River", "Alberta"),
"hinton": ("Edmonton", "Alberta"),
"lacombe": ("Lacombe", "Alberta"),
"leducrep": ("Leduc", "Alberta"),
"mayerthorpefreelancer": ("Edmonton", "Alberta"),
"nantonnews": ("Calgary", "Alberta"),
"prrecordgazette": ("Grande Prairie", "Alberta"),
"pinchercreekecho": ("Lethbridge", "Alberta"),
"sherwoodparknews": ("Edmonton", "Alberta"),
"sprucestony": ("Spruce Grove", "Alberta"),
"vermilionstandard": ("Lloydminster", "Alberta"),
"vulcanadvocate": ("Lethbridge", "Alberta"),
"wetaskiwintimes": ("Wetaskiwin", "Alberta"),
"whitecourtstar": ("Whitecourt", "Alberta"),
"princegeorgepost": ("Prince George", "British Columbia"),
"vancouversunandprovince": ("Vancouver", "British Columbia"),
"altona": ("Altona", "Manitoba"),
"beausejour": ("Beausejour", "Manitoba"),
"carman": ("Carman", "Manitoba"),
"gimli": ("Winnipeg", "Manitoba"),
"lacdubonnet": ("Lac du Bonnet", "Manitoba"),
"morden": ("Morden", "Manitoba"),
"thegraphicleader": ("Portage la Prairie", "Manitoba"),
"selkirk": ("Selkirk", "Manitoba"),
"stonewall": ("Stonewall", "Manitoba"),
"winkler": ("Winkler", "Manitoba"),
"winnipegsun": ("Winnipeg", "Manitoba"),
"northernlight": ("Bathurst", "New Brunswick"),
"thetribune": ("Campbellton", "New Brunswick"),
"dailygleaner": ("Fredericton", "New Brunswick"),
"tjnews": ("Grand Falls & Edmundston", "New Brunswick"),
"miramichileader": ("Miramichi", "New Brunswick"),
"timesandtranscript": ("Moncton", "New Brunswick"),
"letoile": ("Régions Acadiennes", "New Brunswick"),
"telegraph-journal": ("Saint John", "New Brunswick"),
"kingscountyrecord": ("Sussex", "New Brunswick"),
"bugleobserver": ("Woodstock", "New Brunswick"),
"thetelegram": ("St. John's", "Newfoundland and Labrador"),
"thenewglasgownews": ("New Glasgow", "Nova Scotia"),
"intelligencer": ("Belleville", "Ontario"),
"thechronicleherald": ("Halifax", "Nova Scotia"),
"brantfordexpositor": ("Brantford", "Ontario"),
"recorder": ("Brockville", "Ontario"),
"chathamdailynews": ("Chatham", "Ontario"),
"clintonnewsrecord": ("Clinton", "Ontario"),
"cochranetimespost": ("Cochrane", "Ontario"),
"standard-freeholder": ("Cornwall", "Ontario"),
"norfolkandtillsonburgnews": ("Delhi", "Ontario"),
"elliotlakestandard": ("Elliot Lake", "Ontario"),
"midnorthmonitor": ("Sudbury", "Ontario"),
"lakeshoreadvance": ("London", "Ontario"),
"gananoquereporter": ("Kingston", "Ontario"),
"goderichsignalstar": ("Goderich", "Ontario"),
"thepost": ("Durham", "Ontario"),
"kenoraminerandnews": ("Kenora", "Ontario"),
"kincardinenews": ("Port Elgin", "Ontario"),
"thewhig": ("Kingston", "Ontario"),
"northernnews": ("Kirkland Lake", "Ontario"),
"lfpress": ("London", "Ontario"),
"lucknowsentinel": ("Lucknow", "Ontario"),
"mitchelladvocate": ("Mitchell", "Ontario"),
"napaneeguide": ("Kingston", "Ontario"),
"nationalpost": ("National Post", "Ontario"),
"nugget": ("North Bay", "Ontario"),
"ottawa": ("Ottawa", "Ontario"),
"owensoundsuntimes": ("Owen Sound", "Ontario"),
"parisstaronline": ("Brantford", "Ontario"),
"pembrokeobserver": ("Pembroke", "Ontario"),
"countyweeklynews": ("Belleville", "Ontario"),
"shorelinebeacon": ("Port Elgin", "Ontario"),
"theobserver": ("Sarnia", "Ontario"),
"saultstar": ("Sault Ste. Marie", "Ontario"),
"seaforthhuronexpositor": ("Huron County", "Ontario"),
"simcoereformer": ("Simcoe", "Ontario"),
"stthomastimesjournal": ("St. Thomas", "Ontario"),
"communitypress": ("Stirling", "Ontario"),
"stratfordbeaconherald": ("Stratford", "Ontario"),
"strathroyagedispatch": ("London", "Ontario"),
"thesudburystar": ("Sudbury", "Ontario"),
"timminspress": ("Timmins", "Ontario"),
"torontosun": ("Toronto", "Ontario"),
"trentonian": ("Trenton", "Ontario"),
"wallaceburgcourierpress": ("Wallaceburg", "Ontario"),
"thechronicle-online": ("St. Thomas", "Ontario"),
"wiartonecho": ("Wiarton", "Ontario"),
"windsorstar": ("Windsor", "Ontario"),
"woodstocksentinelreview": ("Woodstock", "Ontario"),
"theguardian": ("Charlottetown", "Prince Edward Island"),
"thejournalpioneer": ("Summerside", "Prince Edward Island"),
"montrealgazette": ("Montreal", "Quebec"),
"melfortnipawinjournal": ("Melfort", "Saskatchewan"),
"leaderpost": ("Regina", "Saskatchewan"),
"thestarphoenix": ("Saskatoon", "Saskatchewan"),
}

def extract_city_and_province(url):
    """
    Extracts city and province from the subdomain of the given URL.
    Example URL: 'windsor.remembering.ca'
    """
    # Parse the URL to get the subdomain
    parsed_url = urlparse(url)
    subdomain = parsed_url.hostname.split('.')[0]

    # Look up city and province based on the subdomain
    city_province = CITY_PROVINCE_MAPPING.get(subdomain.lower())

    if city_province:
        city, province = city_province
        return city, province
    else:
        return None  # Return None if subdomain is not found in mapping



def get_city_subdomains(session):
    """Fetch all city subdomains"""
    logging.info("Fetching city subdomains...")
    try:
        response = session.get(f"https://www.{BASE_DOMAIN}/location")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        subdomains = set()
        for link in soup.find_all("a", href=True):
            parsed = urlparse(link["href"])
            if parsed.netloc.endswith(BASE_DOMAIN):
                parts = parsed.netloc.split('.')
                if parts[0].lower() != "www" and len(parts) > 2:
                    subdomains.add(parts[0].lower())
        return sorted(subdomains)
    except Exception as e:
        logging.error(f"Error fetching city subdomains: {e}")
        return []


def process_search_pagination(session, subdomain, visited_search_pages, visited_obituaries, stop_event):
    """Fetch obituary pages with first obituary check and stop on non-current dates"""
    base_url = f"https://{subdomain}.{BASE_DOMAIN}"
    search_url = f"{base_url}/obituaries/all-categories/search?search_type=advanced&ap_search_keyword={SEARCH_KEYWORD}&sort_by=date&order=desc"

    page = 1
    # max_pages = 200
    max_pages = int(os.environ.get("SCRAPER_MAX_PAGES", "2"))
    first_page_processed = False

    while page <= max_pages and not stop_event.is_set():
        logging.info(f"[{subdomain.upper()}] Pagination - Starting page {page}")
        current_url = f"{search_url}&p={page}" if page > 1 else search_url

        if current_url in visited_search_pages:
            logging.info(f"[{subdomain.upper()}] Page {page} already visited, stopping pagination.")
            break
        visited_search_pages.add(current_url)

        try:
            response = session.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            obit_links = soup.select('a[href^="/obituary/"]')
            if not obit_links:
                logging.info(f"[{subdomain.upper()}] Page {page}: No obituary links found, stopping pagination.")
                break

            # Check first obituary's date on the first page
            if page == 1 and not first_page_processed:
                first_obit_url = urljoin(base_url, obit_links[0]['href'])
                pub_date_str, _ = get_publication_date_and_soup(session, first_obit_url)
                if not is_current_month_and_year(pub_date_str):
                    logging.info(f"[{subdomain.upper()}] First obituary is not current. Skipping city.")
                    return
                first_page_processed = True

            # Extract and sort obituaries by date
            obituary_data = []
            for link in obit_links:
                url = urljoin(base_url, link['href'])
                pub_date_str, _ = get_publication_date_and_soup(session, url)
                if pub_date_str:
                    try:
                        pub_date = parser.parse(pub_date_str, fuzzy=True)
                        obituary_data.append({'url': url, 'pub_date': pub_date})
                    except Exception as e:
                        logging.error(f"[{subdomain.upper()}] Error parsing date {pub_date_str}: {e}")
                        continue

            # Sort by date descending
            obituary_data.sort(key=lambda x: x['pub_date'], reverse=True)

            current_page_urls = []
            for item in obituary_data:
                if is_current_month_and_year(item['pub_date'].strftime("%B %d, %Y")):
                    current_page_urls.append(item['url'])
                else:
                    logging.info(f"[{subdomain.upper()}] Non-current obituary found. Stopping city processing.")
                    if current_page_urls:
                        yield current_page_urls
                    return  # Exit entire city processing

            if not current_page_urls:
                logging.info(f"[{subdomain.upper()}] No current obituaries on page {page}. Stopping.")
                return

            yield current_page_urls

            page += 1
            time.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            logging.error(f"[{subdomain.upper()}] Error processing page {page}: {e}")
            break

def get_publication_date_and_soup(session, url):
    soup_for_debug = None
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        soup_for_debug = soup
        publication_date = get_publication_date_from_soup(soup)
        logging.info(f"Fetched publication date for {url}: {publication_date}")
        return publication_date, soup_for_debug
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None, soup_for_debug

def process_city(session, subdomain, stop_event):
    """Process a single city subdomain"""
    logging.info(f"\n{'='*50}\nProcessing city: {subdomain.upper()}\n{'='*50}")
    logging.info(f"[{subdomain.upper()}] Starting city processing.")

    total_alumni = 0
    visited_search_pages = set()
    visited_obituaries = set()

    try:
        # Get pagination generator
        page_generator = process_search_pagination(
            session, subdomain, visited_search_pages, visited_obituaries, stop_event
        )
        logging.info(f"[{subdomain.upper()}] Pagination generator created.")

        for page_urls in page_generator:
            logging.info(f"[{subdomain.upper()}] Received page_urls from generator: {len(page_urls)} urls")
            logging.info(f"[{subdomain.upper()}] Starting loop to process {len(page_urls)} obituary URLs.")
            if stop_event.is_set():
                logging.info(f"[{subdomain.upper()}] Stop event detected during page URL processing.")
                break

            for url in page_urls:
                if stop_event.is_set():
                    logging.info(f"[{subdomain.upper()}] Stop event detected during obituary URL loop.")
                    break

                if url in visited_obituaries:
                    logging.debug(f"[{subdomain.upper()}] Obituary URL already visited: {url}. Skipping.")
                    continue

                # Process obituary with retries
                success = False
                for attempt in range(3):
                    try:
                        logging.info(f"[{subdomain.upper()}] Attempt {attempt+1} to process obituary: {url}")
                        result = process_obituary(session, db.session, url, visited_obituaries, stop_event)
                        if result and result["is_alumni"]:
                            total_alumni += 1
                        success = True
                        break
                    except requests.exceptions.RequestException as e:
                        logging.warning(f"[{subdomain.upper()}] Attempt {attempt + 1} failed for {url}: {e}")
                        time.sleep(2 ** attempt)

                if not success:
                    logging.error(f"[{subdomain.upper()}] Failed to process obituary after 3 attempts: {url}")

                time.sleep(random.uniform(0.7, 1.3))

    except Exception as e:
        logging.error(f"[{subdomain.upper()}] Critical error processing city: {e}")
    finally:
        logging.info(f"[{subdomain.upper()}] City processing finally block reached.")
        logging.info(f"[{subdomain.upper()}] Completed. Alumni found: {total_alumni}")
    logging.info(f"[{subdomain.upper()}] process_city function ending.\n{'='*50}\n")


def is_current_publication_date(publication_date_str):
    if not publication_date_str:
        return False
    try:
        now = datetime.now()
        pub_date = parser.parse(publication_date_str, fuzzy=True).date()
        return pub_date.year == now.year and pub_date.month == now.month
    except Exception as e:
        logging.error(f"Date check error: {e}")
        return False

def is_current_month_and_year(publication_date_str):
    if not publication_date_str:
        return False
    try:
        now = datetime.now()
        pub_date = parser.parse(publication_date_str, fuzzy=True).date()
        return pub_date.year == now.year and pub_date.month == now.month
    except Exception as e:
        logging.error(f"Date check error: {e}")
        return False


def extract_dates(soup):
    """Extracts birth and death dates from obituary details."""
    birth_date = None
    death_date = None

    obit_dates_tag = soup.find("h2", class_="obit-dates")
    if obit_dates_tag:
        date_strings = [s.strip() for s in obit_dates_tag.strings if s.strip()]

        if len(date_strings) == 1:
            death_date = date_strings[0]
        elif len(date_strings) >= 2:
            birth_date = date_strings[0]
            death_date = date_strings[-1]

        if birth_date == "N/A" or not birth_date:
            birth_date = None
        if death_date == "N/A" or not death_date:
            death_date = None

    return birth_date, death_date

def parse_date(date_str):
    """Parse date using dateutil.parser and return 'Month dd, yyyy' format."""
    try:
        parsed_date = parser.parse(date_str, fuzzy=True).date()
        return parsed_date.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return None

def extract_year_from_date(date_string):
    """Extracts the year from a date string."""
    year_match = re.search(r'\b(\d{4})\b', date_string)
    if year_match:
        return int(year_match.group(1))
    else:
        year_match_2digit = re.search(r'/(\d{2})$|[-](\d{2})$|,?\s+(\d{2})$', date_string)
        if year_match_2digit:
            year_str = next((item for item in year_match_2digit.groups() if item is not None), None)
            if year_str:
                year = int(year_str)
                if 0 <= year <= 99:
                    return 2000 + year
        return None


def extract_birth_and_death_dates_from_obituary(text):
    """Extracts death date from obituary text if year > 2000."""
    dates_found = []
    date_patterns = [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b',
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\b',
        r'\b\d{4}\b'
    ]

    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            dates_found.append(match.group(0))
            if len(dates_found) == 1:
                break
        if len(dates_found) == 1:
            break

    death_date = None
    if dates_found:
        first_date_found = dates_found[0]
        year = extract_year_from_date(first_date_found)
        if year and year > 2000:
            death_date = first_date_found
        else:
            death_date = None

    return None, death_date

def extract_text(tag):
    return tag.get_text(strip=True) if tag else "N/A"


# def get_publication_date_from_soup(soup):
#     """Extract publication date from BeautifulSoup object."""
#     publication_date = None
#     published_div = soup.find('div', class_='details-published')
#     if published_div:
#         p_tag = published_div.find('p')
#         if p_tag:
#             text_content = p_tag.text.strip()
#             prefixes = ["Published online ", "Published on "]
#             date_string_to_parse = None

#             for prefix in prefixes:
#                 if text_content.startswith(prefix):
#                     date_string_to_parse = text_content[len(prefix):].strip()
#                     break
#             if date_string_to_parse is None:
#                 date_string_to_parse = text_content

#             if date_string_to_parse:
#                 try:
#                     parsed_date = parser.parse(date_string_to_parse, fuzzy=True).date()
#                     publication_date = parsed_date.strftime("%B %d, %Y")
#                 except (ValueError, TypeError):
#                     logging.warning(f"Could not parse date from text: '{text_content}'")
#                     publication_date = None
#     return publication_date

def get_publication_date_from_soup(soup):
    """Extract publication date from BeautifulSoup object."""
    candidate_selectors = [
        ('div', {'class': 'details-published'}),
        ('span', {'class': 'details-published'}),
        ('p', {'class': 'details-published'}),
        ('div', {'class': 'published'}),
        ('span', {'class': 'published'}),
        ('time', {}),
    ]

    text_candidates = []

    for tag_name, attrs in candidate_selectors:
        for tag in soup.find_all(tag_name, attrs):
            text = tag.get_text(" ", strip=True)
            if text:
                text_candidates.append(text)

            datetime_value = tag.get('datetime')
            if datetime_value:
                text_candidates.append(datetime_value)

    page_text = soup.get_text(" ", strip=True)
    published_match = re.search(
        r'(Published(?:\s+online|\s+on)?\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})',
        page_text,
        re.IGNORECASE
    )
    if published_match:
        text_candidates.append(published_match.group(1))

    for text_content in text_candidates:
        cleaned_text = re.sub(
            r'^Published(?:\s+online|\s+on)?\s+',
            '',
            text_content,
            flags=re.IGNORECASE
        ).strip()

        try:
            parsed_date = parser.parse(cleaned_text, fuzzy=True).date()
            return parsed_date.strftime("%B %d, %Y")
        except (ValueError, TypeError, parser.ParserError):
            continue

    return None

def process_obituary(session, db_session, url, visited_obituaries, stop_event):
    """Extract obituary details, check for alumni keywords, and store in DB."""
    time.sleep(0.2)
    if stop_event.is_set():
        logging.info("Scraping stopped by user request (obituary level - before processing).")
        return None

    subdomain = urlparse(url).hostname.split('.')[0].upper() # Extract subdomain for logging
    logging.info(f"[{subdomain}] Obituary Processing - Starting process_obituary for URL: {url}")
    if url in visited_obituaries:
        logging.debug(f"[{subdomain}] Obituary already visited: {url}. Skipping.")
        return None
    visited_obituaries.add(url)

    try:
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        publication_date_str = get_publication_date_from_soup(soup)
        try:
            publication_date = parser.parse(publication_date_str) if publication_date_str else None
        except Exception as e:
            logging.error(f"[{subdomain}] Failed to parse publication date: {e}")
            publication_date = None

        current_month_year = datetime.now().strftime("%B %Y")
        try:
            pub_date = parser.parse(publication_date_str)
            pub_month_year = pub_date.strftime("%B %Y")
            tags = 'new' if pub_month_year == current_month_year else 'updated'
        except Exception as e:
            logging.error(f"[{subdomain}] Date parsing error: {e}")
            tags = 'updated'
            pub_date = None


        obit_name_tag = soup.find("h1", class_="obit-name")
        last_name_tag = soup.find("span", class_="obit-lastname-upper")

        if not obit_name_tag or not last_name_tag:
            logging.warning(f"[{subdomain}] Could not find name components for obituary: {url}. Skipping.")
            return None

        first_name = extract_text(obit_name_tag).replace(extract_text(last_name_tag), "").strip()
        last_name = extract_text(last_name_tag).capitalize()

        content = soup.select_one("span.details-copy")
        content_text = extract_text(content)

        donation_keywords = ["donation", "charity", "memorial fund", "contributions"]
        donation_mentions = [sentence for sentence in content_text.split(". ") if
                             any(keyword in sentence.lower() for keyword in donation_keywords)]
        donation_info = "; ".join(donation_mentions)

        funeral_home_tag = soup.find("span", class_="obit-fh")
        funeral_home = extract_text(funeral_home_tag)


        obit_dates_tag = soup.find("h2", class_="obit-dates")
        if obit_dates_tag:
            tag_content = obit_dates_tag.get_text(strip=True)
            if tag_content:
                birth_date, death_date = extract_dates(soup)
            else:
                birth_date, death_date = extract_birth_and_death_dates_from_obituary(content_text)
        else:
            birth_date, death_date = extract_birth_and_death_dates_from_obituary(content_text)

        city_province_result = extract_city_and_province(url)
        if not city_province_result:
            logging.warning(f"[{subdomain}] City and province not found for URL: {url}. Skipping obituary.")
            return None

        city, province = city_province_result
        latitude, longitude = get_coordinates(city, province)

        is_alumni = any(keyword in content_text for keyword in ALUMNI_KEYWORDS)

        if is_alumni:
            from app import app
            with app.app_context():
                obituary_entry = Obituary(**{
                    'name': f"{first_name} {last_name}", 'first_name': first_name, 'last_name': last_name,
                    'birth_date': birth_date, 'death_date': death_date,
                    'donation_information': donation_info, 'obituary_url': url, 'city': city,
                    'province': province, 'is_alumni': is_alumni, 'family_information': content_text,
                    'funeral_home': funeral_home,
                    'tags': tags,  # Update this line
                    'publication_date': pub_date if publication_date_str else None,
                    'latitude': latitude,
                    'longitude' : longitude,
                })
                db.session.add(obituary_entry)
                db.session.flush()

                distinct_entry_exists = DistinctObituary.query.filter_by(name=f"{first_name} {last_name}").first()
                if not distinct_entry_exists:
                    distinct_obituary_entry = DistinctObituary(**{
                        'name': f"{first_name} {last_name}", 'first_name': first_name, 'last_name': last_name,
                        'birth_date': birth_date, 'death_date': death_date,
                        'donation_information': donation_info, 'obituary_url': url, 'city': city,
                        'province': province, 'is_alumni': is_alumni, 'family_information': content_text,
                        'funeral_home': funeral_home,
                        'tags': tags,  # Update this line
                        'publication_date': pub_date if publication_date_str else None,
                        'latitude': latitude,
                        'longitude' : longitude,
                    })
                    db.session.add(distinct_obituary_entry)
                    db.session.commit()
                    logging.info(f"[{subdomain}] Distinct Alumni Obituary saved: {first_name} {last_name}")
                else:
                    logging.info(f"[{subdomain}] Duplicate alumni obituary found: {first_name} {last_name}. Skipping DistinctObituary entry.")

        logging.info(f"[{subdomain}] Obituary saved: {first_name} {last_name} {'✅ (Alumni)' if is_alumni else '❌ (Not Alumni)'}")
        return {"name": f"{first_name} {last_name}", "is_alumni": is_alumni, "url": url,"publication_date": publication_date, "tags": tags}

    except Exception as e:
        logging.error(f"[{subdomain}] Error processing obituary {url}: {e}")
        return None

geolocator = Nominatim(user_agent="obituary_mapper")

def get_coordinates(city, province):
    try:
        location = geolocator.geocode(f"{city}, {province}, Canada", timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        logging.error(f"Geocoding error for {city}, {province}: {e}")
    return None, None

def main(stop_event):
    logging.info("Starting obituary scraping process.")
    session = configure_session()

    subdomains = get_city_subdomains(session)
    if not subdomains:
        logging.error("No city subdomains found. Aborting.")
        return

    logging.info(f"Found {len(subdomains)} city subdomains to process.")

    for idx, subdomain in enumerate(subdomains, 1):
        if stop_event.is_set():
            logging.info("Scraping stopped by system request")
            break

        process_city(session, subdomain, stop_event)

    logging.info("Obituary scraping process completed or stopped.")
    

if __name__ == "__main__":
    pass