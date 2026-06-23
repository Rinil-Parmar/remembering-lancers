import logging
import sys
from logging.config import dictConfig


def configure_logging(app):
    log_level = app.config.get("LOG_LEVEL", "INFO")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                }
            },
            "root": {
                "level": log_level,
                "handlers": ["console"],
            },
        }
    )

    logging.getLogger(__name__).info("Logging configured at %s level", log_level)
