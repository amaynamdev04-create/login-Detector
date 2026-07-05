"""Aggregation and query helpers for dashboard and APIs."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import func, or_

from database.models import Alert, BlockedIP, LoginAttempt
from services.authentication import build_blacklist_block, format_block_time
from utils.constants import ALERT_SEVERITY_CRITICAL


def query_login_attempts(
    page: int = 1,
    per_page: int = 15,
    search: str = "",
    status: str = "",
    start_date: str = "",
    end_date: str = "",
    source: str = "",
):
    """Return filtered login attempts with pagination."""
    query = LoginAttempt.query.order_by(LoginAttempt.timestamp.desc())
    if search:
        query = query.filter(
            or_(
                LoginAttempt.username.ilike(f"%{search}%"),
                LoginAttempt.ip_address.ilike(f"%{search}%"),
                LoginAttempt.public_ip.ilike(f"%{search}%"),
                LoginAttempt.private_ip.ilike(f"%{search}%"),
                LoginAttempt.source.ilike(f"%{search}%"),
                LoginAttempt.country.ilike(f"%{search}%"),
                LoginAttempt.region.ilike(f"%{search}%"),
                LoginAttempt.city.ilike(f"%{search}%"),
                LoginAttempt.message.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.filter(LoginAttempt.status == status)
    if source:
        query = query.filter(LoginAttempt.source == source)
    if start_date:
        query = query.filter(func.date(LoginAttempt.timestamp) >= start_date)
    if end_date:
        query = query.filter(func.date(LoginAttempt.timestamp) <= end_date)
    return query.paginate(page=page, per_page=per_page, error_out=False)


def query_alerts(page: int = 1, per_page: int = 15, severity: str = "", source: str = ""):
    """Return filtered alerts."""
    query = Alert.query.order_by(Alert.timestamp.desc())
    if severity:
        query = query.filter(Alert.severity == severity)
    if source:
        query = query.filter(Alert.source == source)
    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_blocked_ips():
    """Return non-expired blocked IPs."""
    database_blocks = (
        BlockedIP.query.filter(BlockedIP.expires_at >= datetime.now(timezone.utc))
        .order_by(BlockedIP.expires_at.desc())
        .all()
    )
    blacklisted_ips = set(current_app.config.get("BLACKLIST_IPS", []))
    existing_ips = {item.ip_address for item in database_blocks}
    for ip_address in sorted(blacklisted_ips - existing_ips):
        database_blocks.insert(0, build_blacklist_block(ip_address))
    return database_blocks


def build_dashboard_context(limit: int = 10) -> dict[str, object]:
    """Build the context for the dashboard and stats API."""
    all_logs = LoginAttempt.query.order_by(LoginAttempt.timestamp.desc()).all()
    all_alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    blocked_ips = get_blocked_ips()
    total_logins = len(all_logs)
    successful = sum(1 for log in all_logs if log.status == "success")
    failed = total_logins - successful
    avg_risk = round(sum(log.risk_score for log in all_logs) / total_logins, 2) if total_logins else 0
    threat_level = (
        "Critical"
        if any(alert.severity == ALERT_SEVERITY_CRITICAL for alert in all_alerts)
        else "Guarded" if failed else "Stable"
    )

    top_attackers = Counter(log.public_ip for log in all_logs if log.status == "failed").most_common(5)
    top_users = Counter(log.username for log in all_logs).most_common(5)
    top_sources = Counter(log.source for log in all_logs).most_common(5)
    top_countries = Counter(log.country for log in all_logs if log.country != "Unknown").most_common(5)
    hourly = Counter(log.timestamp.strftime("%H:00") for log in all_logs)

    return {
        "summary": {
            "total_logins": total_logins,
            "successful_logins": successful,
            "failed_logins": failed,
            "blocked_ips": len(blocked_ips),
            "average_risk": avg_risk,
            "threat_level": threat_level,
        },
        "recent_activity": [log.to_dict() for log in all_logs[:limit]],
        "recent_alerts": [alert.to_dict() for alert in all_alerts[:limit]],
        "top_attackers": [{"label": item[0], "count": item[1]} for item in top_attackers],
        "top_users": [{"label": item[0], "count": item[1]} for item in top_users],
        "top_sources": [{"label": item[0], "count": item[1]} for item in top_sources],
        "top_countries": [{"label": item[0], "count": item[1]} for item in top_countries],
        "hourly_activity": [{"label": hour, "count": hourly[hour]} for hour in sorted(hourly)],
        "blocked_items": [_serialize_blocked_item(item) for item in blocked_ips],
    }


def _serialize_blocked_item(item) -> dict[str, object]:
    """Build blocked-IP view data with human-readable timestamps."""
    payload = item.to_dict()
    payload["blocked_at_display"] = payload.get("blocked_at_display") or format_block_time(item.blocked_at)
    payload["expires_at_display"] = payload.get("expires_at_display") or format_block_time(item.expires_at)
    return payload


def build_analytics_context() -> dict[str, object]:
    """Build chart-ready analytics datasets."""
    all_logs = LoginAttempt.query.order_by(LoginAttempt.timestamp.asc()).all()
    statuses = Counter(log.status for log in all_logs)
    risk_bands = {"0-24": 0, "25-49": 0, "50-74": 0, "75-100": 0}
    for log in all_logs:
        if log.risk_score < 25:
            risk_bands["0-24"] += 1
        elif log.risk_score < 50:
            risk_bands["25-49"] += 1
        elif log.risk_score < 75:
            risk_bands["50-74"] += 1
        else:
            risk_bands["75-100"] += 1

    attack_sources = Counter(log.public_ip for log in all_logs if log.status == "failed").most_common(7)
    site_sources = Counter(log.source for log in all_logs).most_common(7)
    geo_sources = Counter(log.country for log in all_logs if log.country != "Unknown").most_common(7)
    timeline = Counter(log.timestamp.strftime("%Y-%m-%d %H:%M") for log in all_logs if log.status == "failed")
    hourly = Counter(log.timestamp.strftime("%H:00") for log in all_logs)

    return {
        "status_breakdown": {"labels": list(statuses.keys()), "values": list(statuses.values())},
        "risk_distribution": {"labels": list(risk_bands.keys()), "values": list(risk_bands.values())},
        "top_attack_sources": {
            "labels": [item[0] for item in attack_sources],
            "values": [item[1] for item in attack_sources],
        },
        "site_sources": {
            "labels": [item[0] for item in site_sources],
            "values": [item[1] for item in site_sources],
        },
        "country_distribution": {
            "labels": [item[0] for item in geo_sources],
            "values": [item[1] for item in geo_sources],
        },
        "attack_timeline": {"labels": list(timeline.keys()), "values": list(timeline.values())},
        "hourly_trend": {"labels": sorted(hourly), "values": [hourly[key] for key in sorted(hourly)]},
    }
