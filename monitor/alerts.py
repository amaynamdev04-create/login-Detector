"""Alert generation helpers."""

from __future__ import annotations

from datetime import timedelta

from database.database import db
from database.models import Alert, BlockedIP, utcnow
from services.notification import notification_service
from utils.constants import ALERT_SEVERITY_CRITICAL


def create_alert(context: dict[str, object], block_duration_minutes: int) -> Alert:
    """Create an alert and block the offending IP temporarily."""
    alert_time = utcnow()
    description = (
        f"Brute-force behavior detected via {context['trigger']} correlation after "
        f"{context['failed_attempts']} failed login attempts within the detection window."
    )
    alert = Alert(
        timestamp=alert_time,
        username=str(context["username"]),
        ip_address=str(context["ip_address"]),
        source=str(context.get("source", "unknown")),
        failed_attempts=int(context["failed_attempts"]),
        severity=ALERT_SEVERITY_CRITICAL,
        action=f"Blocked IP for {block_duration_minutes} minutes",
        description=description,
    )
    db.session.add(alert)

    blocked_ip = BlockedIP.query.filter_by(ip_address=str(context["ip_address"])).first()
    expiry = alert_time + timedelta(minutes=block_duration_minutes)
    if blocked_ip:
        blocked_ip.blocked_at = alert_time
        blocked_ip.expires_at = expiry
        blocked_ip.source = str(context.get("source", "unknown"))
        blocked_ip.reason = description
    else:
        blocked_ip = BlockedIP(
            ip_address=str(context["ip_address"]),
            blocked_at=alert_time,
            expires_at=expiry,
            source=str(context.get("source", "unknown")),
            reason=description,
        )
        db.session.add(blocked_ip)

    db.session.commit()
    notification_service.dispatch_alert(alert)
    return alert
