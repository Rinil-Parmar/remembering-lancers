import re


EMPTY_VALUES = {"", "N/A", "None", "null"}


def _normalize_text(value):
    if value is None:
        return ""

    text = str(value).strip()
    if text in EMPTY_VALUES:
        return ""

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?<=[a-z0-9,;:])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[.!?])(?=[A-Z])", " ", text)
    return text.strip()


def clean_obituary_body(text, obituary_name=None):
    cleaned = _normalize_text(text)
    if not cleaned:
        return ""

    cleaned = re.sub(
        r"\bObituary\s+Events\s+Guestbook\s+Share\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    if obituary_name:
        name = re.escape(obituary_name.strip())
        header_pattern = (
            rf"^(?:{name}\s*)?"
            rf"(?:[A-Za-z]+\s+\d{{1,2}},\s+\d{{4}}\s*-\s*"
            rf"[A-Za-z]+\s+\d{{1,2}},\s+\d{{4}}\s*)?"
            rf"(?:{name}\s*)+"
        )
        cleaned = re.sub(header_pattern, "", cleaned, flags=re.IGNORECASE).strip()

        title = f"{obituary_name} Obituary"
        title_index = cleaned.casefold().find(title.casefold())
        if 0 <= title_index < 500:
            cleaned = cleaned[title_index + len(title) :].strip()

    cleaned = re.sub(r"^(Obituary|Events|Guestbook|Share)\b", "", cleaned).strip()
    return cleaned


def split_obituary_paragraphs(text, obituary_name=None):
    cleaned = clean_obituary_body(text, obituary_name)
    if not cleaned:
        return []

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", cleaned)
        if sentence.strip()
    ]
    if len(sentences) <= 1:
        return [cleaned]

    paragraphs = []
    for index in range(0, len(sentences), 2):
        paragraphs.append(" ".join(sentences[index : index + 2]))
    return paragraphs


def split_donation_items(text):
    cleaned = _normalize_text(text)
    if not cleaned:
        return []

    return [
        item.strip().rstrip(".")
        for item in re.split(r";|\n", cleaned)
        if item.strip()
    ]
