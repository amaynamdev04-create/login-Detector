"""Configuration classes for the Login Attempt Monitor."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IS_VERCEL = os.getenv("VERCEL") is not None
DEFAULT_LOG_PATH = Path("/tmp/login_attempts.log") if IS_VERCEL else DATA_DIR / "login_attempts.log"


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default).lower()).strip().lower() in {"1", "true", "yes", "on"}


def _database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL", default).strip()
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw.removeprefix("postgres://")
    if raw.startswith("postgresql://") and "+psycopg" not in raw:
        return "postgresql+psycopg://" + raw.removeprefix("postgresql://")
    return raw


class Config:
    """Base configuration shared across environments."""

    ENV = "development"
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = _database_url(f"sqlite:///{BASE_DIR / 'login_attempt_monitor.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", str(DEFAULT_LOG_PATH))
    HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_PORT", "5000"))
    DEBUG = _env_flag("FLASK_DEBUG", False)
    ALERT_THRESHOLD = int(os.getenv("ALERT_THRESHOLD", "5"))
    ALERT_WINDOW_SECONDS = int(os.getenv("ALERT_WINDOW_SECONDS", "120"))
    BLOCK_DURATION_MINUTES = int(os.getenv("BLOCK_DURATION_MINUTES", "15"))
    RECENT_EVENTS_LIMIT = int(os.getenv("RECENT_EVENTS_LIMIT", "10"))
    ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", "15"))
    EXPORT_DIR = str(BASE_DIR / "exports")
    WHITELIST_IPS = [
        item.strip()
        for item in os.getenv("WHITELIST_IPS", "").split(",")
        if item.strip()
    ]
    BLACKLIST_IPS = [
        item.strip()
        for item in os.getenv("BLACKLIST_IPS", "").split(",")
        if item.strip()
    ]
    EMAIL_NOTIFICATIONS = _env_flag("EMAIL_NOTIFICATIONS", False)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    INGEST_API_KEY = os.getenv("INGEST_API_KEY", "change-this-ingest-key")
    DEFAULT_EVENT_SOURCE = os.getenv("DEFAULT_EVENT_SOURCE", "built-in-portal")
    GEOIP_PROVIDER_URL = os.getenv("GEOIP_PROVIDER_URL", "https://ipapi.co/{ip}/json/")
    GEOIP_API_TOKEN = os.getenv("GEOIP_API_TOKEN", "")
    GEOIP_TIMEOUT_SECONDS = float(os.getenv("GEOIP_TIMEOUT_SECONDS", "3"))
    ENABLE_LOG_WATCHER = _env_flag("ENABLE_LOG_WATCHER", not IS_VERCEL)
    INGEST_HISTORICAL_LOGS = _env_flag("INGEST_HISTORICAL_LOGS", False)
    BOOTSTRAP_USERNAME = os.getenv("BOOTSTRAP_USERNAME", "amay.namdev")
    BOOTSTRAP_PASSWORD = os.getenv("BOOTSTRAP_PASSWORD", "ChangeMe!123")
    BOOTSTRAP_FULL_NAME = os.getenv("BOOTSTRAP_FULL_NAME", "Amay Namdev")
    BOOTSTRAP_ROLE = os.getenv("BOOTSTRAP_ROLE", "Administrator")
    CLEAN_DEMO_DATA = _env_flag("CLEAN_DEMO_DATA", True)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = "http"
    TEMPLATES_AUTO_RELOAD = True
    OWNER_NAME = "Amay Namdev"

    @classmethod
    def init_app(cls, app) -> None:
        data_dir = Path(app.config["LOG_FILE_PATH"]).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        Path(app.config["EXPORT_DIR"]).mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    ENV = "development"
    DEBUG = True


class ProductionConfig(Config):
    ENV = "production"
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"

    @classmethod
    def init_app(cls, app) -> None:
        super().init_app(app)
        if app.config["SECRET_KEY"] == "change-me-in-production":
            raise RuntimeError("SECRET_KEY must be set in production.")
        if app.config["INGEST_API_KEY"] == "change-this-ingest-key":
            raise RuntimeError("INGEST_API_KEY must be set in production.")
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL must be set in production for persistent telemetry storage.")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
