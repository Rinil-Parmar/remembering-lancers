# Remembering Lancers

Remembering Lancers is a Flask-based obituary scraping and management dashboard for identifying Remembering.ca obituary records that mention the University of Windsor. It stores alumni records in PostgreSQL and displays them through a searchable dashboard, CSV export, and location map.

> This project is being upgraded from a student prototype into a production-ready application.

## Features

- Search and filter alumni obituary records
- Store data with Flask-SQLAlchemy and PostgreSQL
- Start and stop the scraper from the dashboard
- Detect University of Windsor alumni mentions
- Resume scraper progress by city and search keyword
- Export alumni records to CSV
- Show obituary locations on a Leaflet map
- Run with Flask locally or Waitress for a production-style WSGI server
- Run with Docker Compose using Flask and PostgreSQL

## Tech Stack

- Python 3.13
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- PostgreSQL
- Beautiful Soup
- Requests
- APScheduler
- Geopy
- Leaflet
- Waitress
- Pytest

## Project Structure

```text
remembering-lancers/
├── app.py                         # Local Flask development entrypoint
├── wsgi.py                        # Production-style WSGI entrypoint
├── Dockerfile                     # Flask image definition
├── docker-compose.yml             # Flask + PostgreSQL local stack
├── models.py                      # Compatibility wrapper for old imports
├── scrapper.py                    # Compatibility wrapper for old scraper imports
├── requirements.txt               # Runtime dependencies
├── requirements-dev.txt           # Test/development dependencies
├── pytest.ini                     # Pytest configuration
├── remembering_lancers/
│   ├── __init__.py                # Flask app factory
│   ├── config.py                  # Environment-based configuration
│   ├── extensions.py              # Flask extension instances
│   ├── models.py                  # SQLAlchemy models and scraper state
│   ├── api/                       # JSON API routes
│   ├── web/                       # HTML page routes
│   └── scraper/                   # Scraper routes, service, parser, runner
├── migrations/                    # Flask-Migrate/Alembic files
├── templates/                     # Jinja templates
├── static/                        # CSS, JavaScript, images
└── tests/                         # Regression tests
```

## Local Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/Rinil-Parmar/remembering-lancers.git
cd remembering-lancers
git checkout test/scraper-logic
```

### 2. Create and activate a virtual environment

Git Bash:

```bash
py -3.13 -m venv .venv
source .venv/Scripts/activate
```

PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Create PostgreSQL database

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -c "CREATE DATABASE remembering_lancers_dev;"
```

If the database already exists, continue to the next step.

### 5. Configure environment variables

Copy the example file:

```bash
cp .env.example .env
```

PowerShell alternative:

```powershell
Copy-Item .env.example .env
```

Update `.env`:

```env
FLASK_APP=app.py
FLASK_DEBUG=1
SECRET_KEY=replace-with-a-secure-secret
DATABASE_URL=postgresql://postgres:your-password@localhost:5432/remembering_lancers_dev
APP_ENV=development
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
SCRAPER_MODE=keyword_search
SCRAPER_CITY=
SCRAPER_CURRENT_MONTH_ONLY=true
SCRAPER_MAX_PAGES=1
SCRAPER_PAGE_LIMIT=125
SCRAPER_SEARCH_KEYWORDS=UWindsor,Windsor University,Assumption University,Assumption College,Windsor Law,professor emeritus,alumnus,alumni
SCRAPER_ALUMNI_KEYWORDS=University of Windsor,UWindsor,Windsor University,Assumption University,Assumption College,Windsor Law,professor emeritus,alumnus,alumni
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
SCRAPER_REQUEST_TIMEOUT=10
SCRAPER_RETRY_TOTAL=3
SCRAPER_REPEATED_PAGE_STOP_THRESHOLD=3
```

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Run database migrations

Create or update tables from the Alembic migration history:

```bash
flask db upgrade
```

This creates or updates:

```text
obituary
dist_obituary
scrape_state
scrape_runs
```

### 7. Run locally

```bash
flask run
```

Open:

```text
http://127.0.0.1:5000
```

## Production-Style Run

Use the WSGI entrypoint with Waitress:

```bash
python wsgi.py
```

Default URL:

```text
http://127.0.0.1:8000
```

For Linux deployment later, the same app object is available as:

```text
wsgi:app
```

## Docker

Docker runs two containers:

- `web`: Flask app served by Waitress
- `db`: PostgreSQL 17 database

Build and run the full stack:

```bash
docker compose up --build
```

The web container runs migrations before starting Waitress:

```text
flask db upgrade && python wsgi.py
```

Open:

```text
http://127.0.0.1:8000
```

Stop containers while keeping database data:

```bash
docker compose down
```

Delete containers and database volume for a fresh Docker database:

```bash
docker compose down -v
```

Run migrations manually inside Docker if needed:

```bash
docker compose exec web flask db upgrade
```

Open the Docker PostgreSQL shell:

```bash
docker compose exec db psql -U postgres -d remembering_lancers
```

Check Docker logs:

```bash
docker compose logs -f web
```

For real deployment, change these Compose defaults before exposing the app:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- published ports and network settings

## Testing

```bash
python -m pytest
```

## Scraper Configuration

Important scraper environment variables:

```env
SCRAPER_CITY=windsorstar
SCRAPER_MODE=keyword_search
SCRAPER_CURRENT_MONTH_ONLY=false
SCRAPER_MAX_PAGES=3
SCRAPER_PAGE_LIMIT=125
SCRAPER_SEARCH_KEYWORDS=UWindsor,Windsor University,Assumption University,Assumption College,Windsor Law,professor emeritus,alumnus,alumni
SCRAPER_ALUMNI_KEYWORDS=University of Windsor,UWindsor,Windsor University,Assumption University,Assumption College,Windsor Law,professor emeritus,alumnus,alumni
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
SCRAPER_REQUEST_TIMEOUT=10
SCRAPER_RETRY_TOTAL=3
SCRAPER_REPEATED_PAGE_STOP_THRESHOLD=3
```

- `SCRAPER_MODE`: use `listing_scan` to scan each obituary once from normal listing pages, or `keyword_search` to use Remembering.ca keyword search pages.
- `SCRAPER_CITY`: scrape only one Remembering.ca subdomain. Empty means scrape all configured locations, with Windsor and nearby Ontario locations first.
- `SCRAPER_CURRENT_MONTH_ONLY`: when `true`, skip older publication dates. For discovery/testing, use `false`.
- `SCRAPER_MAX_PAGES`: maximum pages to scan. In `listing_scan`, this is per city listing. In `keyword_search`, this is per city and keyword.
- `SCRAPER_PAGE_LIMIT`: requested result count per listing/search page. Remembering.ca supports `125`, which reduces listing/search pagination overhead.
- `SCRAPER_SEARCH_KEYWORDS`: comma-separated search terms used on Remembering.ca. Keep this list focused on terms that return useful site-search results.
- `SCRAPER_ALUMNI_KEYWORDS`: comma-separated phrases checked inside each obituary body. If omitted, the scraper falls back to `SCRAPER_SEARCH_KEYWORDS`, then built-in defaults.
- `SCRAPER_RESUME_FROM_STATE`: when `true`, resume from the last URL stored in `scrape_state`. When `false`, ignore previous state and start from page 1.
- `SCRAPER_FORCE_RESCAN`: when `true`, scan city/keyword pairs even if `scrape_state` says they are completed.
- `SCRAPER_REQUEST_TIMEOUT`: HTTP timeout in seconds for scraper requests.
- `SCRAPER_RETRY_TOTAL`: retry count for temporary HTTP failures.
- `SCRAPER_REPEATED_PAGE_STOP_THRESHOLD`: number of repeated listing pages allowed before marking listing pagination as blocked.

The scraper stores resume progress in the `scrape_state` table. If stopped and started again, it resumes after the last processed URL for each city and search keyword.

The scraper stores Start-click history in the `scrape_runs` table. It tracks status, current city, current keyword, page number, saved count, skipped count, duplicate count, start/end time, and error message.

For production efficiency, prefer:

```env
SCRAPER_MODE=keyword_search
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
```

This uses Remembering.ca search pages as a fast candidate source, deduplicates candidate URLs, checks each candidate obituary body against the alumni keywords, skips already-saved obituary URLs, and resumes from the saved page and last processed URL.

For slower completeness checks or backfills, use:

```env
SCRAPER_MODE=listing_scan
SCRAPER_PAGE_LIMIT=125
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
```

This scans normal obituary listing pages one by one and verifies every new obituary body.

## Manual Scraper Test Checklist

Use this checklist when validating scraper behavior locally.

### 1. Use the scraper branch

```bash
git checkout test/scraper-logic
git pull
```

### 2. Configure a small Windsor-only run

Update `.env`:

```env
SCRAPER_CITY=windsorstar
SCRAPER_MODE=keyword_search
SCRAPER_CURRENT_MONTH_ONLY=false
SCRAPER_MAX_PAGES=100
SCRAPER_PAGE_LIMIT=125
SCRAPER_SEARCH_KEYWORDS=UWindsor,Windsor University,Assumption University,Assumption College,Windsor Law,professor emeritus,alumnus,alumni
SCRAPER_ALUMNI_KEYWORDS=University of Windsor,UWindsor,Windsor University,Assumption University,Assumption College,Windsor Law,professor emeritus,alumnus,alumni
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
SCRAPER_REQUEST_TIMEOUT=10
SCRAPER_RETRY_TOTAL=3
SCRAPER_REPEATED_PAGE_STOP_THRESHOLD=3
```

### 3. Apply migrations

```bash
flask db upgrade
```

### 4. Run the Flask app

```bash
flask run
```

Open:

```text
http://127.0.0.1:5000
```

Click **Start** on the dashboard.

### 5. Expected logs

You should see logs similar to:

```text
City scrape order: windsorstar
[WINDSORSTAR] Searching keyword: University of Windsor
[WINDSORSTAR] Pagination - Starting page 1
[WINDSORSTAR] Processing obituary URL: ...
[WINDSORSTAR] Publication date for obituary url=...
[WINDSORSTAR] Obituary content extracted with selector: ...
[WINDSORSTAR] Alumni keyword matched: ...
[WINDSORSTAR] Alumni obituary saved: obituary_id=...
```

For non-matches:

```text
Obituary skipped as non-alumni, no alumni keyword matched
```

For already-scraped records:

```text
Existing obituary duplicate skipped
```

### 6. Check database counts

Git Bash:

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "SELECT COUNT(*) FROM obituary;"
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "SELECT COUNT(*) FROM dist_obituary;"
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "SELECT COUNT(*) FROM scrape_state;"
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "SELECT COUNT(*) FROM scrape_runs;"
```

### 7. Check latest scraped records

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "SELECT id, name, city, province, tags, publication_date, obituary_url FROM obituary ORDER BY id DESC LIMIT 10;"
```

### 8. Check scraper resume state

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "SELECT subdomain, search_keyword, page_number, last_processed_url, status, updated_at FROM scrape_state ORDER BY updated_at DESC;"
```

### 9. Check scraper run history

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "SELECT id, status, city, search_keyword, page_number, saved_count, skipped_count, duplicate_count, error_message, started_at, finished_at FROM scrape_runs ORDER BY id DESC LIMIT 10;"
```

### 10. Reset scraper resume state if needed

Only reset state when you intentionally want scraper to start from the beginning again:

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "DELETE FROM scrape_state;"
```

You can also start from page 1 without deleting the state table by setting:

```env
SCRAPER_RESUME_FROM_STATE=false
```

The scraper will still update `scrape_state` during the run; it only ignores previous state at startup.

To clear all scraper data and state:

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d remembering_lancers_dev -c "TRUNCATE TABLE obituary, dist_obituary, scrape_state, scrape_runs RESTART IDENTITY;"
```

## Scraper Safety

Keep local scraper runs small while testing:

```env
SCRAPER_CITY=windsorstar
SCRAPER_MAX_PAGES=1
```

Increase page count only after validating scraper behavior and respecting the source site's terms, rate limits, and robots policy.

## Current Production Gaps

- Scraper network logic should be broadened with more mocked edge-case tests
- Authentication and authorization are not implemented
- Scraping should eventually run as a separate worker for production
- Production monitoring still needs setup

## Data and Privacy

This application processes publicly available obituary information. Deployments should follow applicable privacy requirements, data-retention policies, source-site terms, and ethical data-use practices.

## License

No license has been selected yet.
