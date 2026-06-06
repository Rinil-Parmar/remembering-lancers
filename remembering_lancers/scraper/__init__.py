from flask import Blueprint


scraper_bp = Blueprint("scraper", __name__)

from . import routes
