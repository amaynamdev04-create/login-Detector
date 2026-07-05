"""Log browsing routes."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, request

from services.statistics import query_login_attempts

logs_bp = Blueprint("logs", __name__, url_prefix="/logs")


@logs_bp.route("/")
def list_logs():
    """Render the searchable logs table."""
    page = request.args.get("page", default=1, type=int)
    query = request.args.get("q", default="", type=str)
    status = request.args.get("status", default="", type=str)
    source = request.args.get("source", default="", type=str)
    start = request.args.get("start", default="", type=str)
    end = request.args.get("end", default="", type=str)
    logs = query_login_attempts(
        page=page,
        per_page=current_app.config["ITEMS_PER_PAGE"],
        search=query,
        status=status,
        source=source,
        start_date=start,
        end_date=end,
    )
    return render_template(
        "logs.html",
        logs=logs,
        query=query,
        status=status,
        source=source,
        start=start,
        end=end,
    )
