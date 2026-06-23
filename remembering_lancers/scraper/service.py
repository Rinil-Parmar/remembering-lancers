import logging
import os
import threading
from datetime import datetime, timedelta

import pytz
from apscheduler.schedulers.background import BackgroundScheduler

from ..extensions import db
from ..models import DistinctObituary, Obituary


class ScraperService:
    def __init__(self, app):
        self.app = app
        self.thread = None
        self.last_scrape_time = None
        self.stop_event = threading.Event()
        self.stop_event.set()
        self.state_lock = threading.RLock()
        self.scheduler = None
        self.runner = None

    @property
    def is_active(self):
        with self.state_lock:
            return not self.stop_event.is_set()

    def start(self):
        with self.state_lock:
            if self.is_active:
                return {
                    "message": "Scraping is already running!",
                    **self.status(),
                }, 400

            db.session.query(Obituary).update({Obituary.tags: "updated"})
            db.session.query(DistinctObituary).update(
                {DistinctObituary.tags: "updated"}
            )
            db.session.commit()

            csv_export_path = self.app.config["CSV_EXPORT_PATH"]
            if os.path.exists(csv_export_path):
                with open(csv_export_path, "w"):
                    pass

            self.stop_event.clear()
            self.last_scrape_time = datetime.now(pytz.utc)
            self.thread = threading.Thread(
                target=self._run_background,
                name="obituary-scraper",
                daemon=True,
            )
            self.thread.start()

            return {
                "message": "Scraping started in the background.",
                **self.status(),
            }, 200

    def stop(self):
        with self.state_lock:
            if not self.is_active:
                return {
                    "message": "Scraping is not currently running!",
                    **self.status(),
                }, 400

            self.stop_event.set()
            self.last_scrape_time = datetime.now(pytz.utc)
            return {
                "message": "Stopping scraping...",
                **self.status(),
            }, 200

    def status(self):
        with self.state_lock:
            return {
                "scraping_active": self.is_active,
                "last_scrape_time": (
                    self.last_scrape_time.isoformat()
                    if self.last_scrape_time
                    else None
                ),
            }

    def _run_background(self):
        logging.info("Scraper background thread started.")
        try:
            runner = self.runner or self._load_runner()
            with self.app.app_context():
                runner(self.stop_event)
        except Exception:
            logging.exception("Scraper background thread encountered an error")
        finally:
            with self.state_lock:
                self.stop_event.set()
                self.last_scrape_time = datetime.now(pytz.utc)
            logging.info("Scraper background thread finished.")

    @staticmethod
    def _load_runner():
        from .runner import main

        return main

    @staticmethod
    def is_last_day_of_month():
        tomorrow = datetime.now(pytz.utc) + timedelta(days=1)
        return tomorrow.day == 1

    def auto_scrape_job(self):
        if not self.is_last_day_of_month():
            logging.info("Auto-scrape skipped: today is not the last day of month.")
            return

        with self.app.app_context():
            result, status_code = self.start()
        if status_code == 200:
            logging.info("Monthly auto-scrape started.")
        else:
            logging.info("Monthly auto-scrape not started: %s", result["message"])

    def start_scheduler(self):
        if self.scheduler and self.scheduler.running:
            return

        self.scheduler = BackgroundScheduler(timezone=pytz.utc)
        self.scheduler.add_job(
            self.auto_scrape_job,
            "cron",
            hour=0,
            minute=0,
            id="monthly_scrape",
            replace_existing=True,
        )
        self.scheduler.start()
        logging.info("Scheduler started for the monthly auto-scrape check.")


def init_scraper_service(app):
    service = ScraperService(app)
    app.extensions["scraper_service"] = service
    return service
