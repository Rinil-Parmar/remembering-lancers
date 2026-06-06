# app.py
import os
from flask import jsonify, request, redirect, url_for
from flask import flash

import logging
from remembering_lancers import create_app
from remembering_lancers.extensions import db
from remembering_lancers.models import DistinctObituary, Obituary

import csv, json
from flask import send_file
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz

# import certifi
import requests

# requests.get('https://nominatim.openstreetmap.org', verify=certifi.where())

app = create_app()
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "obituaries_data.csv")

# Import models to register with SQLAlchemy
from scrapper import main

# --- Global variables to track scraper state ---
scrape_thread = None
stop_event = threading.Event()
stop_event.set() # Initially set to True to indicate scraper is not running
last_scrape_time = None
app.extensions["scraper_state"] = {"stop_event": stop_event}

# --- Flask Routes ---
@app.route('/update_tags/<int:obituary_id>', methods=['POST'])
def update_tags(obituary_id):
    new_tags = request.form.get('tags')

    # Update Obituary
    obituary = Obituary.query.get_or_404(obituary_id)
    obituary.tags = new_tags

    # Update DistinctObituary if exists
    distinct_obit = DistinctObituary.query.filter_by(
        obituary_url=obituary.obituary_url
    ).first()
    if distinct_obit:
        distinct_obit.tags = new_tags

    db.session.commit()
    return redirect(url_for('web.obituary_detail', obituary_id=obituary_id))

def is_last_day_of_month():
    logging.info("Checking is_last_day_of_month...") # Log when function is called
    tomorrow = datetime.now(pytz.utc) + timedelta(days=1)
    result = tomorrow.day == 1
    return result


def auto_scrape_job():
    logging.info("auto_scrape_job function called") # Log at start
    if is_last_day_of_month():
        logging.info("⏰ AUTOSCRAPE: is_last_day_of_month returned True") # Log when condition is met
        logging.info("⏰ AUTOSCRAPE: Last day of month detected, starting automated scrape")
        try:
            main(stop_event)  # Use your existing main function
            logging.info("✅ AUTOSCRAPE: Monthly auto-scrape completed successfully")
        except Exception as e:
            logging.error(f"❌ AUTOSCRAPE ERROR inside try block: {str(e)}") # More specific error log
        finally:
            stop_event.set()
    else:
        logging.info("auto_scrape_job: is_last_day_of_month returned False, skipping scrape.") # Log when not last day

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.utc)

    # Run auto_scrape_job every minute for testing
    scheduler.add_job(
        auto_scrape_job,  # Use auto_scrape_job again
        'cron',
        hour=0,
        minute=0,
        id='monthly_scrape'# Keep the same id or change
    )

    scheduler.start()
    logging.info("⏲️  Scheduler started - Auto-scrape job scheduled every month for testing.") # Update log message

@app.route('/start_scrape', methods=['POST'])
def start_scrape():
    """Route to start the scraper in a background thread."""
    global scrape_thread, stop_event, last_scrape_time

    if not stop_event.is_set():
        db.session.query(Obituary).update({Obituary.tags: 'updated'})
        db.session.query(DistinctObituary).update({DistinctObituary.tags: 'updated'})
        db.session.commit() # Check event status instead of boolean flag
        return jsonify({'message': 'Scraping is already running!'}), 400

    stop_event.clear()  # Clear the stop event to start scraping

    # Overwrite CSV before starting the scraper
    if os.path.exists(CSV_FILE_PATH):
        open(CSV_FILE_PATH, 'w').close()  # Truncate the file (overwrite)

    scrape_thread = threading.Thread(target=run_scraper_background, args=(stop_event,)) # Pass stop_event as argument
    scrape_thread.start()

    last_scrape_time = datetime.now()

    return jsonify({
        'message': 'Scraping started in the background.',
        'scraping_active': True, # Add this line
        'last_scrape_time': last_scrape_time.isoformat()
    })


@app.route('/stop_scrape', methods=['POST'])
def stop_scrape():
    """Route to stop the scraper (set event to stop gracefully)."""
    global stop_event, last_scrape_time

    if stop_event.is_set(): # Check event status instead of boolean flag
        return jsonify({'message': 'Scraping is not currently running!'}), 400

    stop_event.set()  # Set the stop event to signal scraper to stop
    time.sleep(2)  # Keep delay for testing, can remove later

    last_scrape_time = datetime.now()

    return jsonify({
        'message': 'Stopping scraping...',
        'scraping_active': False,
        'last_scrape_time': last_scrape_time.isoformat() # Add this line
    })


@app.route('/scrape_status')
def scrape_status():
    global last_scrape_time
    """Route to get the current scraping status."""
    return jsonify({'scraping_active': not stop_event.is_set(), 'last_scrape_time': last_scrape_time.isoformat() if last_scrape_time else None})


def run_scraper_background(stop_event):
    """Function to run the scraper in the background thread."""
    logging.info("Scraper background thread started.")
    try:
        main(stop_event)  # Pass stop_event to main()
    except Exception as e:
        logging.error(f"Scraper background thread encountered an error: {e}")
    finally:
        # Automatically stop when done
        with app.app_context():
            try:
                client = app.test_client()
                client.post('/stop_scrape')
                logging.info("Automatic stop triggered after completion")
            except Exception as e:
                logging.error(f"Error triggering automatic stop: {e}")
        logging.info("Scraper background thread finished.")

def generate_csv():
    """Helper function to generate a fresh CSV file from the database."""
    with app.app_context():
        obituaries = DistinctObituary.query.order_by(DistinctObituary.publication_date.desc()).all()

        if not obituaries:
            return None  # No data available

        with open(CSV_FILE_PATH, 'w', newline='') as csvfile:
            # fieldnames = ['id', 'name', 'first_name', 'last_name', 'city', 'province', 'birth_date',
            #               'death_date', 'obituary_url']
            fieldnames = ['id', 'name', 'first_name', 'last_name', 'city', 'province', 'birth_date',
              'death_date', 'obituary_url', 'tags']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for obit in obituaries:
                writer.writerow({
                    'id': obit.id,
                    'name': obit.name,
                    'first_name': obit.first_name,
                    'last_name': obit.last_name,
                    'obituary_url': obit.obituary_url,
                    'city': obit.city,
                    'province': obit.province,
                    'birth_date': obit.birth_date,
                    'death_date': obit.death_date,
                    'tags': obit.tags,
                })

        return CSV_FILE_PATH


@app.route('/download_csv')
def download_csv():
    """Route to generate and download obituaries data as CSV."""
    csv_file = generate_csv()  # Generate CSV before downloading
    if not csv_file:
        return jsonify({'error': 'No obituaries available to download'}), 404

    return send_file(csv_file, as_attachment=True, download_name="obituaries.csv", mimetype="text/csv")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        start_scheduler()  # Start the scheduler
        stop_event.set()
    app.run(debug=True)
