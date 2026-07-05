"""Blueprint registration."""

from routes.alerts import alerts_bp
from routes.analytics import analytics_bp
from routes.auth import auth_bp
from routes.api import api_bp
from routes.dashboard import dashboard_bp
from routes.logs import logs_bp
from routes.settings import settings_bp


def register_blueprints(app) -> None:
    """Register all application blueprints."""
    for blueprint in (
        dashboard_bp,
        auth_bp,
        logs_bp,
        alerts_bp,
        analytics_bp,
        settings_bp,
        api_bp,
    ):
        app.register_blueprint(blueprint)
