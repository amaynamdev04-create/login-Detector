"""Dashboard routes."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template

from services.statistics import build_dashboard_context

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard():
    """Render the main dashboard."""
    context = build_dashboard_context(limit=current_app.config["RECENT_EVENTS_LIMIT"])
    return render_template("dashboard.html", **context)


@dashboard_bp.route("/about")
def about():
    """Render the about page."""
    return render_template("about.html")
