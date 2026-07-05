"""Application entry point for the Login Attempt Monitor."""

from __future__ import annotations

import os

from flask import Flask, redirect, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config_by_name
from database.init_db import initialize_database
from monitor.watcher import monitoring_service
from routes import register_blueprints
from utils.logger import configure_logging


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    environment = os.getenv("FLASK_ENV") or ("production" if os.getenv("VERCEL") is not None else "development")
    config_class = config_by_name.get(environment, config_by_name["default"])
    app.config.from_object(config_class)
    config_class.init_app(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[assignment]

    configure_logging(app)
    initialize_database(app)
    register_blueprints(app)
    register_request_guards(app)

    with app.app_context():
        monitoring_service.configure(
            log_file=app.config["LOG_FILE_PATH"],
            threshold=app.config["ALERT_THRESHOLD"],
            window_seconds=app.config["ALERT_WINDOW_SECONDS"],
            block_duration_minutes=app.config["BLOCK_DURATION_MINUTES"],
            whitelist=app.config["WHITELIST_IPS"],
            app=app,
        )
        monitoring_service.start()

    return app


def register_request_guards(app: Flask) -> None:
    """Register simple session-based access control."""

    @app.before_request
    def require_login():
        allowed_endpoints = {
            "auth.login",
            "auth.logout",
            "static",
        }
        if request.endpoint in allowed_endpoints:
            return None
        if request.endpoint is None:
            return None
        if request.blueprint == "api":
            return None
        if session.get("user_id"):
            return None
        return redirect(url_for("auth.login"))


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
        use_reloader=False,
    )
