import os

from dotenv import load_dotenv
from flask import Flask

from .config import CONFIGS
from .extensions import db, migrate


def create_app(config_name=None):
    load_dotenv()

    selected_config = config_name or os.environ.get("APP_ENV", "development")

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app.config.from_object(CONFIGS[selected_config])

    db.init_app(app)
    migrate.init_app(app, db)

    # Register SQLAlchemy models.
    from . import models

    from .web import web_bp

    app.register_blueprint(web_bp)

    return app
