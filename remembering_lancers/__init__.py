import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from .config import CONFIGS, validate_config
from .extensions import db, migrate
from .logging_config import configure_logging


def create_app(config_name=None):
    selected_config = config_name or os.environ.get("APP_ENV", "development")

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app.config.from_object(CONFIGS[selected_config])
    validate_config(selected_config, app.config)
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # Register SQLAlchemy models.
    from . import models

    from .api import api_bp
    from .scraper import scraper_bp
    from .scraper.service import init_scraper_service
    from .web import web_bp

    init_scraper_service(app)
    app.register_blueprint(api_bp)
    app.register_blueprint(scraper_bp)
    app.register_blueprint(web_bp)

    return app
