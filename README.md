# Remembering Lancers

Remembering Lancers is a Flask-based obituary scraping and management dashboard. It searches Remembering.ca obituary listings, identifies records mentioning the University of Windsor, stores alumni records in PostgreSQL, and displays them through a searchable dashboard and map.

> This project is for educational and research purposes. Obituary data remains the property of its original publishers and sources.

## Features

- Search Remembering.ca obituary listings
- Identify University of Windsor alumni
- Store obituary records in PostgreSQL
- Search and filter records by name, city, and province
- Display obituary locations on an interactive map
- Review and update record status
- Export records as CSV
- Start and stop scraping from the dashboard

## Technology Stack

- Python 3.13
- Flask
- Flask-SQLAlchemy
- PostgreSQL
- Beautiful Soup
- Requests
- spaCy
- APScheduler
- Leaflet
- Tailwind CSS

## Project Structure

```text
remembering-lancers/
├── app.py                  # Flask application and routes
├── models.py               # SQLAlchemy database models
├── scrapper.py             # Obituary scraping logic
├── requirements.txt        # Python dependencies
├── migrations/             # Database migration files
├── templates/              # Flask HTML templates
├── static/
│   ├── images/
│   ├── script.js
│   └── styles.css
└── obituaries_data.csv     # Generated CSV export
```

## Prerequisites

Install the following before running the project:

- Python 3.13, 64-bit
- PostgreSQL 15 or newer
- Git

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/remembering-lancers.git
cd remembering-lancers
```

### 2. Create and activate a virtual environment

Git Bash on Windows:

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
python -m spacy download en_core_web_sm
```

### 4. Create the PostgreSQL database

Open PostgreSQL:

```bash
psql -U postgres
```

Create the development database:

```sql
CREATE DATABASE remembering_lancers_dev;
\q
```

### 5. Configure environment variables

Copy `.env.example` to `.env`:

Git Bash:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your PostgreSQL password and a secure secret key:

```env
FLASK_APP=app.py
FLASK_DEBUG=1
SECRET_KEY=replace-with-a-secure-secret
DATABASE_URL=postgresql://postgres:your-password@localhost:5432/remembering_lancers_dev
SCRAPER_MAX_PAGES=1
```

Generate a secure secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 6. Create database tables

The migration history is currently being rebuilt. For the current development version, create tables from the SQLAlchemy models:

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('tables created')"
```

### 7. Run the application

```bash
flask run
```

Open:

```text
http://127.0.0.1:5000
```

## Scraper Safety

For local testing, keep the scraper page limit low:

```env
SCRAPER_MAX_PAGES=1
```

Increase this only after validating scraper behavior and respecting the source website's terms, rate limits, and robots policy.

## Production Status

This project is currently being upgraded from a student prototype to a production-ready application.

Remaining production work includes:

- Repairing database migrations
- Improving scraper duplicate handling
- Adding authentication and authorization
- Moving scraping into a dedicated worker
- Adding automated tests
- Improving frontend responsiveness and accessibility
- Adding Docker configuration
- Adding production logging and monitoring

## Data and Privacy

This application processes publicly available obituary information. Deployments should follow applicable privacy requirements, data-retention policies, source-site terms, and ethical data-use practices.

## License

No license has been selected yet.