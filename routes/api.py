"""REST API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from flask import Blueprint, current_app, jsonify, request, send_file

from services.exporter import export_logs_to_csv
from services.authentication import get_active_block
from services.network import normalize_ip, parse_ip_version
from services.statistics import (
    build_analytics_context,
    build_dashboard_context,
    get_blocked_ips,
    query_alerts,
    query_login_attempts,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")
LOGGER = logging.getLogger(__name__)


def _is_ingest_authorized() -> bool:
    return request.headers.get("X-API-Key") == current_app.config["INGEST_API_KEY"]


@api_bp.route("/stats")
def stats():
    """Return dashboard statistics as JSON."""
    return jsonify(build_dashboard_context(limit=10))


@api_bp.route("/logs")
def logs():
    """Return logs in JSON format."""
    page = request.args.get("page", default=1, type=int)
    logs_page = query_login_attempts(
        page=page,
        per_page=50,
        search=request.args.get("q", default="", type=str),
        status=request.args.get("status", default="", type=str),
        source=request.args.get("source", default="", type=str),
        start_date=request.args.get("start", default="", type=str),
        end_date=request.args.get("end", default="", type=str),
    )
    return jsonify(
        {
            "items": [log.to_dict() for log in logs_page.items],
            "page": logs_page.page,
            "pages": logs_page.pages,
            "total": logs_page.total,
        }
    )


@api_bp.route("/alerts")
def alerts():
    """Return alerts in JSON format."""
    page = request.args.get("page", default=1, type=int)
    alerts_page = query_alerts(
        page=page,
        per_page=50,
        source=request.args.get("source", default="", type=str),
    )
    return jsonify(
        {
            "items": [alert.to_dict() for alert in alerts_page.items],
            "page": alerts_page.page,
            "pages": alerts_page.pages,
            "total": alerts_page.total,
        }
    )


@api_bp.route("/blocked")
def blocked():
    """Return blocked IPs in JSON format."""
    return jsonify({"items": [item.to_dict() for item in get_blocked_ips()]})


@api_bp.route("/analytics")
def analytics():
    """Return chart-ready analytics data."""
    return jsonify(build_analytics_context())


@api_bp.route("/export/logs")
def export_logs():
    """Export logs as CSV."""
    file_path = export_logs_to_csv()
    return send_file(file_path, as_attachment=True)


@api_bp.route("/integrations/login-attempt", methods=["POST"])
def ingest_login_attempt():
    """Receive login attempt events from external websites."""
    if not _is_ingest_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    required_fields = {"username", "ip_address", "status", "source"}
    missing_fields = sorted(required_fields - payload.keys())
    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    status = str(payload["status"]).strip().lower()
    if status not in {"success", "failed"}:
        return jsonify({"error": "status must be success or failed"}), 400

    timestamp_raw = str(payload.get("timestamp", "")).strip()
    if timestamp_raw:
        try:
            event_time = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "timestamp must be ISO 8601 when provided"}), 400
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
    else:
        event_time = datetime.now(timezone.utc)

    parsed_entry = {
        "timestamp": event_time,
        "username": str(payload["username"]).strip(),
        "ip_address": normalize_ip(str(payload["ip_address"]).strip()),
        "public_ip": normalize_ip(str(payload.get("public_ip") or payload["ip_address"]).strip()),
        "private_ip": normalize_ip(str(payload["private_ip"]).strip()) if payload.get("private_ip") else None,
        "ip_version": str(payload.get("ip_version") or parse_ip_version(str(payload.get("public_ip") or payload["ip_address"])) or ""),
        "source": str(payload["source"]).strip(),
        "status": status,
        "message": str(payload.get("message") or f"Login {'Success' if status == 'success' else 'Failed'}"),
        "country": str(payload.get("country") or "").strip() or None,
        "country_code": str(payload.get("country_code") or "").strip() or None,
        "region": str(payload.get("region") or "").strip() or None,
        "city": str(payload.get("city") or "").strip() or None,
        "timezone": str(payload.get("timezone") or "").strip() or None,
        "isp": str(payload.get("isp") or "").strip() or None,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
    }
    if not all(parsed_entry[key] for key in ("username", "ip_address", "source", "public_ip")):
        return jsonify({"error": "username, ip_address, public_ip, and source must be non-empty"}), 400

    from monitor.watcher import monitoring_service

    LOGGER.info(
        "Received external login event source=%s user=%s ip=%s status=%s",
        parsed_entry["source"],
        parsed_entry["username"],
        parsed_entry["public_ip"],
        parsed_entry["status"],
    )
    monitoring_service.process_entry(parsed_entry)
    block = get_active_block(parsed_entry["public_ip"])
    return jsonify(
        {
            "ok": True,
            "processed": parsed_entry,
            "blocked": block is not None,
            "block": block.to_dict() if block else None,
        }
    ), 201


@api_bp.route("/integrations/check-block")
def check_block():
    """Allow external websites to check if an IP is currently blocked."""
    if not _is_ingest_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    ip_address = normalize_ip(request.args.get("ip_address", default="", type=str).strip())
    if not ip_address:
        return jsonify({"error": "ip_address is required"}), 400

    block = get_active_block(ip_address)
    return jsonify(
        {
            "ip_address": ip_address,
            "blocked": block is not None,
            "block": block.to_dict() if block else None,
        }
    )
