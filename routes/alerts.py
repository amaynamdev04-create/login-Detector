"""Alert history routes."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, request

from services.statistics import query_alerts

alerts_bp = Blueprint("alerts", __name__, url_prefix="/alerts")


@alerts_bp.route("/")
def list_alerts():
    """Render stored alerts."""
    page = request.args.get("page", default=1, type=int)
    severity = request.args.get("severity", default="", type=str)
    source = request.args.get("source", default="", type=str)
    alerts = query_alerts(
        page=page,
        per_page=current_app.config["ITEMS_PER_PAGE"],
        severity=severity,
        source=source,
    )
    return render_template("alerts.html", alerts=alerts, severity=severity, source=source)
