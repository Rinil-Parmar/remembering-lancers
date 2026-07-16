# Remembering Lancers Setup Guide

This guide explains how to install, configure, run, test, and troubleshoot the Remembering Lancers project in both normal local mode and Docker mode.

## 1. Project Overview

Remembering Lancers is a Flask application that scrapes public obituary pages from Remembering.ca, detects records that mention University of Windsor-related alumni terms, stores matching records in PostgreSQL, and displays them in a searchable dashboard with CSV export and map views.

The application has three main parts:

- Flask web dashboard and JSON API
- Scraper service and scraper runner
- PostgreSQL database with Alembic migrations

## 2. Main Technologies

- Python 3.13
- Flask
- Flask-SQLAlchemy
- Flask-Migrate / Alembic
- PostgreSQL
- Requests
- Beautiful Soup
- APScheduler
- Geopy
- Waitress
- Pytest
- Docker and Docker Compose

Frontend dependencies are currently loaded from public CDNs in the dashboard:

- Bootstrap
- Leaflet
- Chart.js

## 3. Repository Entry Points

| File | Purpose |
| --- | --- |
| `app.py` | Local Flask development entrypoint. Starts Flask and also starts the background scheduler. |
| `wsgi.py` | Production-style Waitress entrypoint. Serves the Flask app on `HOST` and `PORT`. |
| `docker-compose.yml` | Local Docker stack for the web app and PostgreSQL. |
| `Dockerfile` | Builds the Python/Flask application image. |
| `remembering_lancers/config.py` | Main environment-based app configuration. |
| `remembering_lancers/scraper/runner.py` | Scraper configuration, scraping logic, parsing flow, matching logic, and database persistence. |
| `remembering_lancers/scraper/service.py` | Start/stop scraper service, in-memory run lock, and monthly scheduler setup. |
| `migrations/` | Database migration history. |
| `tests/` | Automated regression tests. |

## 4. Prerequisites

Install these before running the project locally:

- Git
- Python 3.13
- PostgreSQL 17 or compatible PostgreSQL version
- Docker Desktop, only if using Docker

Check versions:

```powershell
git --version
py -3.13 --version
docker --version
docker compose version
```

PostgreSQL should be running locally if you are using the normal non-Docker setup.

## 5. Clone the Repository

```powershell
git clone https://github.com/Rinil-Parmar/remembering-lancers.git
cd remembering-lancers
```

Use the active project branch for current scraper improvements:

```powershell
git checkout feature/scraper-matching-improvements
```

If IT or the team uses a different branch name, use the approved branch for deployment testing.

## 6. Normal Local Setup

### 6.1 Create Virtual Environment

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 6.2 Install Dependencies

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

`requirements.txt` is needed to run the app.

`requirements-dev.txt` is needed for tests and development checks.

### 6.3 Create Local PostgreSQL Database

Example using the default local database name:

```powershell
psql -U postgres -c "CREATE DATABASE remembering_lancers_dev;"
```

If `psql` is not on the PATH, use the full PostgreSQL path, for example:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE remembering_lancers_dev;"
```

If the database already exists, continue to the next step.

### 6.4 Create `.env`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Generate a secure secret key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `.env` with your local database password and generated secret:

```env
FLASK_APP=app.py
FLASK_DEBUG=1
SECRET_KEY=replace-with-generated-secret
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
SCRAPER_SEARCH_KEYWORDS=UWindsor,University of Windsor,Assumption University,Assumption College,Windsor Law,Essex College
SCRAPER_ALUMNI_KEYWORDS=University of Windsor,UWindsor,Assumption University,Assumption College,Windsor Law,Essex College
SCRAPER_MATCH_MODE=proximity
SCRAPER_INSTITUTION_KEYWORDS=University of Windsor,UWindsor,Windsor Law,Assumption University,Assumption College,Essex College
SCRAPER_STATUS_KEYWORDS=graduated,graduating,graduate,grad,alumnus,alumna,alumni,attended,studied,degree,B.A.,B.Sc.,LL.B.,J.D.,class of
SCRAPER_MATCH_WINDOW=160
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
SCRAPER_REQUEST_TIMEOUT=10
SCRAPER_RETRY_TOTAL=3
SCRAPER_REPEATED_PAGE_STOP_THRESHOLD=3
```

### 6.5 Apply Database Migrations

```powershell
flask db upgrade
```

This creates or updates these tables:

- `obituary`
- `dist_obituary`
- `scrape_state`
- `scrape_runs`

### 6.6 Run the App in Flask Development Mode

```powershell
flask run
```

Default URL:

```text
http://127.0.0.1:5000
```

Important note: `flask run` uses the Flask CLI. The monthly scheduler is started when running `python app.py`, but not automatically when using `flask run`.

### 6.7 Run the App with `app.py`

```powershell
python app.py
```

Default URL:

```text
http://127.0.0.1:5000
```

This mode starts the app and calls `start_scheduler()` before running Flask.

### 6.8 Run the App in Production-Style Local Mode

```powershell
python wsgi.py
```

Default URL:

```text
http://127.0.0.1:8000
```

`wsgi.py` uses Waitress and reads:

- `HOST`
- `PORT`

Important note: the current `wsgi.py` entrypoint does not start the monthly scheduler.

## 7. Docker Setup

Docker Compose runs:

- `web`: Flask application served by Waitress
- `db`: PostgreSQL 17 database

### 7.1 Create Docker Environment File

```powershell
Copy-Item .env.docker.example .env.docker
```

Generate a secure secret key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `.env.docker`:

```env
APP_ENV=production
APP_PORT=8000
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

SECRET_KEY=replace-with-generated-secret

POSTGRES_DB=remembering_lancers
POSTGRES_USER=remembering_lancers_app
POSTGRES_PASSWORD=replace-with-strong-database-password
POSTGRES_PORT=5432
DATABASE_URL=postgresql://remembering_lancers_app:replace-with-strong-database-password@db:5432/remembering_lancers

SCRAPER_MAX_PAGES=1
```

Make sure the password in `DATABASE_URL` matches `POSTGRES_PASSWORD`.

### 7.2 Build and Start Docker Stack

```powershell
docker compose --env-file .env.docker up --build
```

Open:

```text
http://127.0.0.1:8000
```

The web container runs this startup command:

```sh
flask db upgrade && python wsgi.py
```

So database migrations are applied before Waitress starts.

### 7.3 Run Docker in Background

```powershell
docker compose --env-file .env.docker up --build -d
```

### 7.4 View Logs

```powershell
docker compose --env-file .env.docker logs -f web
docker compose --env-file .env.docker logs -f db
```

### 7.5 Stop Docker Stack

Stop containers but keep database data:

```powershell
docker compose --env-file .env.docker down
```

Stop containers and delete the database volume:

```powershell
docker compose --env-file .env.docker down -v
```

Use `down -v` only when you intentionally want a fresh Docker database.

### 7.6 Run Migrations Manually in Docker

```powershell
docker compose --env-file .env.docker exec web flask db upgrade
```

### 7.7 Open PostgreSQL Shell in Docker

```powershell
docker compose --env-file .env.docker exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

### 7.8 Docker Port Behavior

Current Compose behavior:

- Web app maps `${APP_PORT:-8000}:8000`
- PostgreSQL maps `127.0.0.1:${POSTGRES_PORT:-5432}:5432`

This means:

- The app is available on local port `8000` by default.
- PostgreSQL is only bound to localhost for local development.
- PostgreSQL should not be publicly exposed in production.

For production, the web app should normally sit behind HTTPS on port `443` through a reverse proxy or platform load balancer.

## 8. Environment Variables

### 8.1 Application Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` or `production` | Selects Flask config class. Production requires real `SECRET_KEY` and `DATABASE_URL`. |
| `FLASK_APP` | `app.py` | Flask CLI entrypoint. |
| `FLASK_DEBUG` | `1` | Enables Flask debug behavior for local development. Do not use in production. |
| `SECRET_KEY` | generated random string | Flask signing/session secret. Required and must be secure in production. |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | SQLAlchemy database connection string. |
| `HOST` | `0.0.0.0` | Host used by `wsgi.py`. |
| `PORT` | `8000` | Port used by `wsgi.py`. |
| `LOG_LEVEL` | `INFO` | Application logging level. |
| `CSV_EXPORT_PATH` | optional | File path for CSV export. Defaults to `obituaries_data.csv` in the project root. |
| `TEST_DATABASE_URL` | `sqlite:///:memory:` | Test database URL used by testing config. |

### 8.2 Docker Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `APP_PORT` | `8000` | Host port mapped to the web container's internal port `8000`. |
| `POSTGRES_DB` | `remembering_lancers` | Docker PostgreSQL database name. |
| `POSTGRES_USER` | `remembering_lancers_app` | Docker PostgreSQL username. |
| `POSTGRES_PASSWORD` | strong password | Docker PostgreSQL password. |
| `POSTGRES_PORT` | `5432` | Localhost-only host port for PostgreSQL during Docker development. |

### 8.3 Scraper Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `SCRAPER_MODE` | `keyword_search` | Scraper mode. Use `keyword_search` or `listing_scan`. |
| `SCRAPER_CITY` | `windsorstar` | Restrict scraping to one Remembering.ca subdomain. Empty means all configured locations. |
| `SCRAPER_CURRENT_MONTH_ONLY` | `true` | When true, skip older publication dates. |
| `SCRAPER_MAX_PAGES` | `1` | Maximum pages scanned. Scope depends on scraper mode. |
| `SCRAPER_PAGE_LIMIT` | `125` | Requested result count per listing/search page. |
| `SCRAPER_SEARCH_KEYWORDS` | comma-separated terms | Search terms used on Remembering.ca search pages. |
| `SCRAPER_ALUMNI_KEYWORDS` | comma-separated terms | Terms used by simple/fallback alumni matching. |
| `SCRAPER_MATCH_MODE` | `proximity` | Use `proximity` or `simple`. |
| `SCRAPER_INSTITUTION_KEYWORDS` | comma-separated terms | Institution terms used by proximity matching. |
| `SCRAPER_STATUS_KEYWORDS` | comma-separated terms | Education/status terms used by proximity matching. |
| `SCRAPER_MATCH_WINDOW` | `160` | Character distance allowed between institution and status terms. |
| `SCRAPER_RESUME_FROM_STATE` | `true` | Resume from the saved `scrape_state` table. |
| `SCRAPER_FORCE_RESCAN` | `false` | Rescan even when state says a city/keyword is complete. |
| `SCRAPER_REQUEST_TIMEOUT` | `10` | HTTP request timeout in seconds. |
| `SCRAPER_RETRY_TOTAL` | `3` | Retry count for temporary request failures. |
| `SCRAPER_REPEATED_PAGE_STOP_THRESHOLD` | `3` | Stop threshold for repeated listing pages. |

Important Docker note: the current `docker-compose.yml` only passes `SCRAPER_MAX_PAGES` into the web container. If Docker deployments need the full scraper configuration, add the other `SCRAPER_*` variables to `docker-compose.yml` or configure them in the deployment platform.

## 9. Scraper Modes

### 9.1 `keyword_search`

Recommended normal mode.

This mode searches Remembering.ca using configured keywords, collects candidate obituary URLs, checks each obituary body for alumni evidence, deduplicates URLs, and saves matching records.

Recommended production-style values:

```env
SCRAPER_MODE=keyword_search
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
SCRAPER_PAGE_LIMIT=125
```

### 9.2 `listing_scan`

Slower completeness/backfill mode.

This mode scans normal listing pages and checks each obituary. It can be useful for validation or historical backfills, but it performs more requests.

Recommended cautious values:

```env
SCRAPER_MODE=listing_scan
SCRAPER_CITY=windsorstar
SCRAPER_MAX_PAGES=1
SCRAPER_PAGE_LIMIT=125
```

## 10. Safe Local Scraper Test

For a small local validation run:

```env
SCRAPER_CITY=windsorstar
SCRAPER_MODE=keyword_search
SCRAPER_CURRENT_MONTH_ONLY=false
SCRAPER_MAX_PAGES=1
SCRAPER_PAGE_LIMIT=125
SCRAPER_RESUME_FROM_STATE=true
SCRAPER_FORCE_RESCAN=false
```

Start the app, open the dashboard, and click Start.

Check records:

```powershell
psql -U postgres -d remembering_lancers_dev -c "SELECT COUNT(*) FROM obituary;"
psql -U postgres -d remembering_lancers_dev -c "SELECT COUNT(*) FROM scrape_state;"
psql -U postgres -d remembering_lancers_dev -c "SELECT COUNT(*) FROM scrape_runs;"
```

Check latest records:

```powershell
psql -U postgres -d remembering_lancers_dev -c "SELECT id, name, city, province, publication_date, obituary_url FROM obituary ORDER BY id DESC LIMIT 10;"
```

Check latest scraper runs:

```powershell
psql -U postgres -d remembering_lancers_dev -c "SELECT id, status, city, search_keyword, page_number, saved_count, skipped_count, duplicate_count, error_message, started_at, finished_at FROM scrape_runs ORDER BY id DESC LIMIT 10;"
```

## 11. Health Check

Health endpoint:

```text
GET /health
```

Expected healthy result:

```text
HTTP 200
```

If the database check fails, the app returns:

```text
HTTP 503
```

## 12. Run Tests

```powershell
python -m pytest
```

Current test command validates backend behavior, API behavior, scraper service behavior, parser behavior, and selected scraper runner behavior.

## 13. Production Deployment Notes for IT

Before production deployment, confirm these items with IT:

- Public access should go through HTTPS on port `443`.
- The Flask app can run internally on port `8000`.
- PostgreSQL port `5432` should not be publicly exposed.
- The app requires outbound HTTP/HTTPS access to retrieve public Remembering.ca obituary pages.
- Decide whether authentication will be handled by the app, a reverse proxy, SSO, VPN, or another University-approved method.
- Decide where production secrets will live.
- Decide whether PostgreSQL will be managed by IT or hosted as a managed database service.
- Confirm backup, restore, monitoring, and log-retention requirements.
- Confirm domain or subdomain.
- Confirm firewall, proxy, and allowlist requirements.

Current production caveats:

- Admin/scraper controls are not yet protected by authentication.
- CSRF protection is not yet implemented for scraper control actions.
- The in-memory scraper lock only protects one Python process.
- The monthly scheduler starts from `app.py`, but not from the current `wsgi.py`/Docker path.
- Docker Compose currently passes only `SCRAPER_MAX_PAGES` from scraper configuration.
- Dashboard frontend dependencies currently load from CDNs.

## 14. Common Problems

### Database connection fails

Check:

- PostgreSQL service is running.
- `DATABASE_URL` has correct username, password, host, port, and database name.
- The database exists.
- Firewall or VPN is not blocking the connection.

### `flask db upgrade` fails

Check:

- Virtual environment is active.
- Dependencies are installed.
- `FLASK_APP=app.py` is set.
- `DATABASE_URL` points to the correct database.

### Docker web container exits

Check:

```powershell
docker compose --env-file .env.docker logs web
```

Common causes:

- Missing `SECRET_KEY`
- Missing `DATABASE_URL`
- Database password mismatch between `POSTGRES_PASSWORD` and `DATABASE_URL`
- Database container is not healthy yet

### Dashboard opens but scraper does not save records

Check:

- `SCRAPER_CURRENT_MONTH_ONLY` may be filtering older records.
- `SCRAPER_CITY` may be too narrow or invalid.
- `SCRAPER_MAX_PAGES` may be too low.
- Outbound HTTP/HTTPS may be blocked.
- Remembering.ca page structure may have changed.
- The obituary text may not contain configured alumni keywords.

### Docker scraper settings do not apply

The current Compose file only passes `SCRAPER_MAX_PAGES`. Add required `SCRAPER_*` variables to the `web.environment` section or configure them in the hosting platform.

## 15. Recommended First-Time Setup Path

For a developer:

1. Create `.venv`.
2. Install dependencies.
3. Create local PostgreSQL database.
4. Copy `.env.example` to `.env`.
5. Update `SECRET_KEY` and `DATABASE_URL`.
6. Run `flask db upgrade`.
7. Run `flask run`.
8. Run `python -m pytest`.
9. Test a small scraper run with `SCRAPER_CITY=windsorstar` and `SCRAPER_MAX_PAGES=1`.

For IT deployment testing:

1. Copy `.env.docker.example` to `.env.docker`.
2. Replace all secrets.
3. Run `docker compose --env-file .env.docker up --build`.
4. Confirm `GET /health` returns 200.
5. Confirm dashboard loads on port `8000`.
6. Confirm database is not publicly exposed.
7. Confirm outbound HTTP/HTTPS to Remembering.ca works.
8. Confirm HTTPS/reverse proxy/authentication plan before production exposure.
