# IT Department Meeting Preparation

Project: Remembering Lancers automated obituary retrieval and review tool  
Purpose: prepare for secure deployment inside the University of Windsor environment

## 1. Short Project Explanation

Remembering Lancers is a Flask-based web application that helps the Alumni Department identify publicly available obituary records that may mention University of Windsor alumni or related university associations.

The application:

- retrieves publicly available obituary pages from Remembering.ca;
- checks obituary text for University of Windsor-related references;
- stores possible matches in PostgreSQL;
- provides a dashboard for review, search, filtering, tagging, CSV export, and map display;
- tracks scraper progress, run history, duplicates, skipped records, and errors.

Important point for the meeting:

The tool does not make a final alumni-status decision. It only identifies possible matches. Human review is still required.

## 2. Current Project Status

The project is a working prototype being prepared for production-style deployment.

Already implemented:

- Flask web dashboard.
- PostgreSQL database support.
- SQLAlchemy models and Flask-Migrate/Alembic migrations.
- Obituary record storage.
- Distinct obituary record storage.
- Scraper state tracking.
- Scraper run history tracking.
- Start, stop, and status endpoints for the scraper.
- CSV export.
- Keyword-based and listing-based retrieval modes.
- Duplicate URL detection.
- Resume support after scraper interruption.
- Dockerfile and Docker Compose local stack.
- Pytest regression tests.

Still needing ITS guidance:

- approved hosting environment;
- authentication and authorization;
- production database hosting;
- HTTPS and domain/subdomain setup;
- firewall and outbound access rules;
- backup and retention policy;
- monitoring/logging expectations;
- security/privacy review process.

## 3. Technology Stack

Runtime and application:

- Python 3.13
- Flask
- Waitress WSGI server for production-style serving
- Jinja templates
- HTML/CSS/JavaScript frontend
- Leaflet for map display

Database:

- PostgreSQL
- Flask-SQLAlchemy
- Flask-Migrate / Alembic
- psycopg2-binary PostgreSQL driver

Scraper and parsing:

- requests
- urllib3 retry support
- BeautifulSoup4
- python-dateutil
- geopy
- APScheduler
- pytz

Configuration and testing:

- python-dotenv
- pytest
- pytest-cov

## 4. Application Runtime

Development entrypoint:

- `app.py`
- usually run with `flask run`
- local development URL commonly uses port `5000`

Production-style entrypoint:

- `wsgi.py`
- served by Waitress
- host is controlled by `HOST`
- port is controlled by `PORT`
- current default production-style port is `8000`

Docker entrypoint:

- image based on `python:3.13-slim`
- container exposes port `8000`
- Docker Compose maps `8000:8000`
- web container runs migrations before startup:

```text
flask db upgrade && python wsgi.py
```

## 5. Network and Port Details

Current known ports:

| Purpose | Port | Notes |
|---|---:|---|
| Local Flask development server | 5000 | Used for local development with `flask run` |
| Production-style Waitress application | 8000 | Used by `python wsgi.py` and Docker web container |
| Docker web mapping | 8000:8000 | Host port 8000 maps to container port 8000 |
| PostgreSQL | 5432 | Should remain private/internal, not publicly exposed |
| Production HTTPS access | 443 | Recommended public access through reverse proxy/load balancer |

Recommended production model:

```text
Authorized user
  -> HTTPS on port 443
  -> ITS reverse proxy / load balancer
  -> Flask/Waitress app on internal port 8000
  -> PostgreSQL on private port 5432
```

Outbound access required:

- The scraper needs outbound HTTP/HTTPS access to public obituary pages.
- ITS should confirm whether outbound traffic must go through a proxy.
- ITS should confirm whether external domains need to be allowlisted.
- ITS should confirm acceptable scraping/request limits.

Important note:

The database should not be directly exposed to the public internet.

## 6. Docker and Container Details

Current Docker setup includes two services:

`web`

- builds from the project Dockerfile;
- runs the Flask application through Waitress;
- uses `APP_ENV=production`;
- exposes/mapping port `8000`;
- depends on healthy PostgreSQL service;
- runs database migrations before startup.

`db`

- uses `postgres:17`;
- stores data in a persistent Docker volume;
- has a health check using `pg_isready`;
- currently maps `5432:5432` for local development.

For production, ask ITS whether:

- Docker Compose is acceptable;
- a managed container platform is preferred;
- PostgreSQL should be managed separately;
- the database port mapping should be removed;
- secrets should be stored in an approved secret manager instead of Compose environment values.

## 7. Database Details

Database engine:

- PostgreSQL

Main database tables:

- `obituary`
- `dist_obituary`
- `scrape_state`
- `scrape_runs`

Stored obituary-related fields include:

- name;
- first name;
- last name;
- birth date;
- death date;
- city;
- province;
- publication date;
- obituary URL;
- family information;
- donation information;
- funeral home;
- alumni-match flag;
- review tag;
- latitude;
- longitude.

Scraper state fields include:

- city/subdomain;
- search keyword;
- page number;
- last processed URL;
- status;
- updated timestamp.

Scraper run history includes:

- run status;
- start time;
- finish time;
- current city;
- search keyword;
- page number;
- saved count;
- skipped count;
- duplicate count;
- error message.

Database questions for ITS:

- Should PostgreSQL be hosted by ITS?
- Should the app use a managed database service?
- What backup schedule is required?
- What restore process is expected?
- Who will maintain database credentials?
- Should database access be restricted by network, user, or both?
- Should the database be encrypted at rest?
- What data retention policy should be applied?

## 8. Web Routes and API Endpoints

User-facing web routes:

- `/` - dashboard
- `/obituary/<id>` - obituary detail page
- `/about` - about page
- `/download_csv` - CSV export
- `/update_tags/<id>` - update review tag

API/data routes:

- `/get_obituaries` - retrieve alumni obituary records
- `/search_obituaries` - search/filter obituary records
- `/api/publications/grouped-by-year` - group publication records by year

Scraper control routes:

- `/start_scrape` - start scraper
- `/stop_scrape` - request scraper stop
- `/scrape_status` - check scraper status and latest run

Important security point:

These routes should not be publicly available without authentication in production.

## 9. Configuration and Environment Variables

Important application variables:

| Variable | Purpose |
|---|---|
| `APP_ENV` | development, testing, or production |
| `SECRET_KEY` | Flask secret key; must be secure in production |
| `DATABASE_URL` | PostgreSQL connection string |
| `HOST` | app bind host, currently supports `0.0.0.0` |
| `PORT` | app port, default production-style value is `8000` |
| `LOG_LEVEL` | logging level |
| `CSV_EXPORT_PATH` | optional CSV output path |

Important scraper variables:

| Variable | Purpose |
|---|---|
| `SCRAPER_MODE` | `keyword_search` or `listing_scan` |
| `SCRAPER_CITY` | target Remembering.ca city/subdomain, optional |
| `SCRAPER_CURRENT_MONTH_ONLY` | skip older records when true |
| `SCRAPER_MAX_PAGES` | page limit for a run |
| `SCRAPER_PAGE_LIMIT` | result count requested per search/listing page |
| `SCRAPER_SEARCH_KEYWORDS` | terms used for candidate discovery |
| `SCRAPER_ALUMNI_KEYWORDS` | terms used for simple alumni matching |
| `SCRAPER_MATCH_MODE` | `simple` or `proximity` |
| `SCRAPER_INSTITUTION_KEYWORDS` | institution terms such as University of Windsor |
| `SCRAPER_STATUS_KEYWORDS` | status terms such as alumnus, graduate, degree |
| `SCRAPER_MATCH_WINDOW` | character distance for proximity matching |
| `SCRAPER_RESUME_FROM_STATE` | resume from saved scraper state |
| `SCRAPER_FORCE_RESCAN` | rescan completed states |
| `SCRAPER_REQUEST_TIMEOUT` | HTTP request timeout |
| `SCRAPER_RETRY_TOTAL` | retry count for temporary HTTP failures |
| `SCRAPER_REPEATED_PAGE_STOP_THRESHOLD` | prevents repeated-page loops |

Production configuration notes:

- `SECRET_KEY` must not use a default value.
- `DATABASE_URL` must not be committed with real credentials.
- `.env` should not be used as the final secret management method unless ITS approves.
- ITS should confirm the approved way to store secrets.

## 10. Scraper Behavior

The scraper supports two modes:

`keyword_search`

- Uses Remembering.ca search pages.
- Faster for production-style use.
- Finds candidate obituary URLs based on search keywords.
- Then checks each obituary body for University-related matches.

`listing_scan`

- Scans normal obituary listing pages.
- Slower but useful for completeness checks and backfills.
- Processes every new obituary candidate from listing pages.

Matching behavior:

- Simple matching can check for configured alumni keywords.
- Proximity matching checks for an institution keyword near a status keyword.
- Example:
  - institution: `University of Windsor`
  - status: `graduate`, `alumnus`, `degree`, `class of`
  - match window: configured with `SCRAPER_MATCH_WINDOW`

Safety behavior:

- Maximum pages are configurable.
- Request timeout is configurable.
- Retry count is configurable.
- Repeated-page detection prevents infinite loops.
- Duplicate URLs are skipped.
- Scraper state allows restart/resume.
- Stop request can interrupt active scraping.

Question for ITS:

Should the scraper have a required delay/rate limit between requests, and what value is acceptable?

## 11. Security Considerations

Known security controls already present:

- Environment-based configuration.
- Production config validates required `SECRET_KEY` and `DATABASE_URL`.
- SQLAlchemy ORM is used for database access.
- Database URL is configurable.
- Logging level is configurable.

Security gaps to discuss:

- Authentication is not currently implemented.
- Authorization/roles are not currently implemented.
- Dashboard routes should be protected before production.
- Scraper start/stop routes should be restricted.
- PostgreSQL should not be exposed publicly.
- Secrets should use an ITS-approved secure storage method.
- HTTPS should be enforced in production.
- Backup and retention policies need confirmation.
- Security/privacy review may be required before deployment.

Questions for ITS:

- Should we use University SSO?
- Should access be limited to Alumni Department staff only?
- Should there be admin/reviewer/read-only roles?
- Should the app be available only on campus network or VPN?
- Are there vulnerability scanning requirements?
- Are there logging/audit requirements for user actions?
- What is the approved process for handling public obituary data?

## 12. Data and Privacy Points

The application handles publicly available obituary information.

Possible stored information:

- person name;
- obituary URL;
- publication date;
- death date;
- city/province;
- funeral home;
- obituary text/family information;
- donation information;
- alumni-related match indicator;
- review tag;
- latitude/longitude when available.

Privacy points to say clearly:

- The tool is for internal review and reporting.
- It does not confirm alumni identity automatically.
- Human review is required.
- It does not collect passwords, payment data, student academic records, or financial information.
- Retention and deletion rules should follow university policy.
- Source-site terms and ethical scraping expectations should be reviewed.

## 13. Logging, Monitoring, and Backups

Current logging:

- Python logging writes to console/stdout.
- Log level is controlled by `LOG_LEVEL`.
- Scraper progress, errors, duplicate skips, and run summaries are logged.

Monitoring needs:

- application availability;
- database availability;
- failed scraper runs;
- unexpected scraper errors;
- storage usage;
- backup success/failure;
- certificate expiry if HTTPS is managed for this app.

Backup needs:

- PostgreSQL backup schedule;
- retention period;
- restore test process;
- owner responsible for backups;
- backup encryption/storage location.

Questions for ITS:

- Should logs go to a central university logging system?
- What log retention period is required?
- Should scraper run errors trigger alerts?
- Who monitors the app after deployment?
- What backup schedule should be used?
- Who restores the database if needed?

## 14. Deployment Options To Discuss

Possible options:

1. ITS-managed virtual machine
   - App runs with Waitress or behind a reverse proxy.
   - PostgreSQL could be local or managed separately.

2. ITS container platform
   - Docker image/container is deployed by ITS.
   - PostgreSQL is managed separately or as an internal service.

3. Docker Compose on a controlled server
   - Good for simple deployment.
   - Must improve secrets, networking, backups, and database exposure before production.

4. University web hosting platform
   - Only possible if it supports Python/Flask, PostgreSQL, background tasks, and outbound HTTP/HTTPS.

Questions for ITS:

- Which deployment model is approved?
- Can Docker images be deployed?
- Is Docker Compose acceptable?
- Is a reverse proxy/load balancer provided?
- Who manages TLS certificates?
- Who manages the domain/subdomain?
- Is PostgreSQL provided as a managed service?
- Are background tasks allowed in the app container/server?

## 15. Meeting Questions Checklist

Hosting and infrastructure:

- What hosting environment should we use for this Flask application?
- Is Docker/container deployment supported?
- Should we deploy using Docker Compose, a container platform, or a VM?
- Will ITS provide a reverse proxy or load balancer?
- What production URL/domain/subdomain should be used?

Network:

- Should public/user access go through HTTPS on port `443`?
- Should the app listen internally on port `8000`?
- Should database port `5432` remain private?
- Are outbound HTTP/HTTPS requests allowed from the hosting environment?
- Do outbound requests need a proxy?
- Are external obituary domains required to be allowlisted?
- Should app access be campus-only, VPN-only, or public with login?

Authentication and authorization:

- Should the app use University SSO?
- Which user groups should have access?
- Do we need admin/reviewer/read-only roles?
- Should scraper start/stop be restricted to admins?

Database:

- Should PostgreSQL be hosted by ITS?
- What version of PostgreSQL is preferred?
- How are database credentials managed?
- What backup and restore process should be used?
- Should the database be encrypted at rest?

Security:

- Is a formal security review required?
- Are vulnerability scans required before deployment?
- What is the approved secret management method?
- Are there required HTTP security headers?
- Should the app be behind Web Application Firewall rules?

Operations:

- Who will monitor the application?
- Where should application logs be sent?
- What alerts are required?
- Who restarts the app if it fails?
- What support handoff documentation is required?

Privacy and compliance:

- What data retention policy should apply?
- Is this data classification considered public, internal, or sensitive?
- Are there privacy review requirements?
- Are there restrictions on storing obituary text?
- Are there requirements for deleting/exporting records?

Scraping policy:

- Is automated retrieval from public obituary pages allowed?
- Are there request-rate limits ITS wants us to enforce?
- Should the scraper use a specific user agent?
- Should scraping run manually, monthly, or on another schedule?
- Should there be approval before running full backfills?

## 16. Things To Be Ready To Say In The Meeting

Use this simple explanation:

This is a Python Flask web application with a PostgreSQL database. It has a dashboard for authorized staff and a background scraper that retrieves publicly available obituary pages. The scraper identifies possible University of Windsor-related records using configured keywords and proximity matching, stores possible matches, and allows staff to review/export them. We need ITS guidance on approved hosting, authentication, database management, network/firewall rules, HTTPS, monitoring, backups, and data retention.

Important technical facts:

- Local development uses Flask on port `5000`.
- Production-style app uses Waitress on port `8000`.
- Docker Compose maps `8000:8000`.
- PostgreSQL uses `5432`, but it should stay private.
- Production user access should be HTTPS on `443`.
- The app needs outbound HTTP/HTTPS access for obituary retrieval.
- Current deployment secrets are environment-variable based.
- Authentication is not yet implemented and needs ITS direction.
- PostgreSQL backups and retention need ITS direction.
- The scraper can be limited by max pages, timeout, retry count, and resume state.

## 17. Recommended Next Work After The Meeting

After ITS gives direction, likely next tasks are:

1. Add authentication/SSO integration or approved access control.
2. Add a `/health` endpoint for monitoring.
3. Create `.env.production.example`.
4. Adjust Docker Compose for production-safe networking.
5. Add rate-limit/request-delay setting for the scraper if ITS requires it.
6. Add clearer scraper run summary on the dashboard.
7. Add deployment runbook.
8. Add backup/restore documentation.
9. Add security checklist to README or docs.
10. Add more tests for scraper network failures and edge cases.

## 18. Short Meeting Agenda

1. Project purpose and current status.
2. Application architecture and technical stack.
3. Hosting/deployment options.
4. Network, ports, firewall, and outbound access.
5. Database hosting, backup, and retention.
6. Authentication and user access.
7. Security/privacy review requirements.
8. Monitoring, logging, and operational ownership.
9. Scraping policy and acceptable request limits.
10. Next steps and action items.

