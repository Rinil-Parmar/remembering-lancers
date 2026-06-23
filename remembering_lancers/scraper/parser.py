import re

from dateutil import parser as date_parser


def extract_dates(soup):
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
    try:
        parsed_date = date_parser.parse(date_str, fuzzy=True).date()
        return parsed_date.strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return None


def extract_year_from_date(date_string):
    year_match = re.search(r"\b(\d{4})\b", date_string)
    if year_match:
        return int(year_match.group(1))

    year_match_2digit = re.search(
        r"/(\d{2})$|[-](\d{2})$|,?\s+(\d{2})$", date_string
    )
    if year_match_2digit:
        year_str = next(
            (item for item in year_match_2digit.groups() if item is not None),
            None,
        )
        if year_str:
            year = int(year_str)
            if 0 <= year <= 99:
                return 2000 + year
    return None


def extract_birth_and_death_dates_from_obituary(text):
    dates_found = []
    date_patterns = [
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{1,2}-\d{1,2}-\d{2,4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\b",
        r"\b\d{4}\b",
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

    return None, death_date


def extract_text(tag):
    return tag.get_text(strip=True) if tag else "N/A"


def get_publication_date_from_soup(soup):
    candidate_selectors = [
        ("div", {"class": "details-published"}),
        ("span", {"class": "details-published"}),
        ("p", {"class": "details-published"}),
        ("div", {"class": "published"}),
        ("span", {"class": "published"}),
        ("time", {}),
    ]

    text_candidates = []
    for tag_name, attrs in candidate_selectors:
        for tag in soup.find_all(tag_name, attrs):
            text = tag.get_text(" ", strip=True)
            if text:
                text_candidates.append(text)

            datetime_value = tag.get("datetime")
            if datetime_value:
                text_candidates.append(datetime_value)

    page_text = soup.get_text(" ", strip=True)
    published_match = re.search(
        r"(Published(?:\s+online|\s+on)?\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})",
        page_text,
        re.IGNORECASE,
    )
    if published_match:
        text_candidates.append(published_match.group(1))

    for text_content in text_candidates:
        cleaned_text = re.sub(
            r"^Published(?:\s+online|\s+on)?\s+",
            "",
            text_content,
            flags=re.IGNORECASE,
        ).strip()

        try:
            parsed_date = date_parser.parse(cleaned_text, fuzzy=True).date()
            return parsed_date.strftime("%B %d, %Y")
        except (ValueError, TypeError, date_parser.ParserError):
            continue

    return None
