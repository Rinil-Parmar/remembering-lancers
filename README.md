# Remembering Lancers

Remembering Lancers is a Flask-based obituary scraping and management dashboard for identifying Remembering.ca obituary records that mention the University of Windsor. It stores alumni records in PostgreSQL and displays them through a searchable dashboard, CSV export, and location map.

> This project is being upgraded from a student prototype into a production-ready application.

## Features

- Search and filter alumni obituary records
- Store data with Flask-SQLAlchemy and PostgreSQL
- Start and stop the scraper from the dashboard
- Detect University of Windsor alumni mentions
- Export alumni records to CSV
- Show obituary locations on a Leaflet map
- Run with Flask locally or Waitress for a production-style WSGI server

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
├── models.py                      # Compatibility wrapper for old imports
├── scrapper.py                    # Compatibility wrapper for old scraper imports
├── requirements.txt               # Runtime dependencies
├── requirements-dev.txt           # Test/development dependencies
├── pytest.ini                     # Pytest configuration
├── remembering_lancers/
│   ├── __init__.py                # Flask app factory
│   ├── config.py                  # Environment-based configuration
│   ├── extensions.py              # Flask extension instances
│   ├── models.py                  # SQLAlchemy models
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
SCRAPER_MAX_PAGES=1
APP_ENV=development
HOST=0.0.0.0
PORT=8000
```

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Create database tables

The migration history still needs cleanup. For the current development setup, create tables from the SQLAlchemy models:

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('tables created')"
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

## Testing

```bash
python -m pytest
```

## Scraper Safety

Keep local scraper runs small while testing:

```env
SCRAPER_MAX_PAGES=1
```

Increase this only after validating scraper behavior and respecting the source site's terms, rate limits, and robots policy.

## Current Production Gaps

- Database migrations need to be rebuilt and verified
- Scraper network logic needs stronger mocked tests
- Authentication and authorization are not implemented
- Scraping should eventually run as a separate worker for production
- Docker configuration still needs to be added
- Production logging and monitoring still need setup

## Data and Privacy

This application processes publicly available obituary information. Deployments should follow applicable privacy requirements, data-retention policies, source-site terms, and ethical data-use practices.

## License

No license has been selected yet.
