"""Analytics routes."""

from flask import Blueprint, render_template

from services.statistics import build_analytics_context

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
def analytics():
    """Render the analytics view."""
    return render_template("analytics.html", **build_analytics_context())
