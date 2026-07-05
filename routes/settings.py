"""Settings routes."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from monitor.watcher import monitoring_service
from services.network import normalize_ip
from utils.helper import parse_csv_list

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
def settings():
    """View and update runtime monitoring settings."""
    if request.method == "POST":
        threshold = max(1, request.form.get("alert_threshold", type=int, default=5))
        duration = max(1, request.form.get("block_duration", type=int, default=15))
        whitelist = [normalize_ip(item) for item in parse_csv_list(request.form.get("whitelist", ""))]
        blacklist = [normalize_ip(item) for item in parse_csv_list(request.form.get("blacklist", ""))]

        current_app.config["ALERT_THRESHOLD"] = threshold
        current_app.config["BLOCK_DURATION_MINUTES"] = duration
        current_app.config["WHITELIST_IPS"] = whitelist
        current_app.config["BLACKLIST_IPS"] = blacklist
        monitoring_service.configure(
            log_file=current_app.config["LOG_FILE_PATH"],
            threshold=threshold,
            window_seconds=current_app.config["ALERT_WINDOW_SECONDS"],
            block_duration_minutes=duration,
            whitelist=whitelist,
            app=current_app._get_current_object(),
        )
        flash("Monitoring settings updated successfully.", "success")
        return redirect(url_for("settings.settings"))

    return render_template("settings.html", app_config=current_app.config)
