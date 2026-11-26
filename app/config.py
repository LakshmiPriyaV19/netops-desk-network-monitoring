"""Application configuration loaded securely from environment variables."""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load variables from .env file if present in the project root
load_dotenv()


def build_mysql_uri() -> str:
    """Construct the SQLAlchemy MySQL+PyMySQL connection URI from environment variables.

    Supports an explicit DATABASE_URL override or individual DB_* variables.
    URL-encodes credentials safely so special characters in passwords do not break parsing.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    if os.getenv("USE_SQLITE_FALLBACK", "false").lower() == "true":
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        return f"sqlite:///{os.path.join(base_dir, 'netops_desk_dev.db')}"

    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "netops_desk")

    encoded_user = quote_plus(db_user)
    encoded_password = quote_plus(db_password)
    auth = f"{encoded_user}:{encoded_password}" if db_password else encoded_user

    return f"mysql+pymysql://{auth}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


class BaseConfig:
    """Base configuration shared across all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-fallback-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Detect and recycle stale MySQL connections automatically
    }
    MONITORING_ENABLED = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    MONITORING_INTERVAL_SECONDS = int(os.getenv("MONITORING_INTERVAL_SECONDS", "15"))


class DevelopmentConfig(BaseConfig):
    """Local development configuration targeting MySQL (or optional SQLite fallback)."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = build_mysql_uri()


class TestingConfig(BaseConfig):
    """Isolated test configuration using an in-memory SQLite database for fast, repeatable pytest runs."""

    TESTING = True
    DEBUG = False
    MONITORING_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(BaseConfig):
    """Production configuration with debug mode disabled."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = build_mysql_uri()


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
