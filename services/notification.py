"""Notification service for alert fan-out."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


class NotificationService:
    """Minimal notification service for alert dispatch."""

    def dispatch_alert(self, alert) -> None:
        """Dispatch an alert to configured sinks."""
        LOGGER.warning(
            "ALERT [%s] user=%s ip=%s attempts=%s action=%s",
            alert.severity,
            alert.username,
            alert.ip_address,
            alert.failed_attempts,
            alert.action,
        )


notification_service = NotificationService()
