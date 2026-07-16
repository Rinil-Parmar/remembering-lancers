import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:admin@localhost:5432/remembering_lancers_dev",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    SCRAPER_MAX_PAGES = int(os.environ.get("SCRAPER_MAX_PAGES", "1"))
    CSV_EXPORT_PATH = os.environ.get(
        "CSV_EXPORT_PATH",
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "obituaries_data.csv")
        ),
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def validate_config(config_name, app_config):
    if config_name != "production":
        return

    missing = [
        env_var
        for env_var in ("SECRET_KEY", "DATABASE_URL")
        if not os.environ.get(env_var)
    ]
    if missing:
        raise RuntimeError(
            "Missing required production environment variables: "
            + ", ".join(missing)
        )

    unsafe_secret_keys = {
        "dev-secret-change-me",
        "replace-with-a-secure-secret",
        "replace-with-a-secure-random-secret",
    }
    if app_config["SECRET_KEY"] in unsafe_secret_keys:
        raise RuntimeError("Production SECRET_KEY must not use a default placeholder.")
