"""Brute-force detection engine."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone


class BruteForceDetector:
    """Detect repeated failed login attempts by username or IP."""

    def __init__(self, threshold: int = 5, window_seconds: int = 120) -> None:
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.failed_by_ip: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)
        self.failed_by_user: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)

    def configure(self, threshold: int, window_seconds: int) -> None:
        """Update detector thresholds without restarting the process."""
        self.threshold = threshold
        self.window_seconds = window_seconds

    def _prune(self, bucket: deque[datetime], current_time: datetime) -> None:
        window_start = current_time - timedelta(seconds=self.window_seconds)
        while bucket and bucket[0] < window_start:
            bucket.popleft()

    def record_attempt(
        self,
        username: str,
        ip_address: str,
        source: str,
        status: str,
        timestamp: datetime,
    ):
        """Record an attempt and return detection context if suspicious."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        ip_key = (source, ip_address)
        user_key = (source, username)

        if status == "success":
            self.failed_by_ip[ip_key].clear()
            self.failed_by_user[user_key].clear()
            return None

        ip_events = self.failed_by_ip[ip_key]
        user_events = self.failed_by_user[user_key]
        ip_events.append(timestamp)
        user_events.append(timestamp)
        self._prune(ip_events, timestamp)
        self._prune(user_events, timestamp)

        ip_count = len(ip_events)
        user_count = len(user_events)
        if ip_count >= self.threshold or user_count >= self.threshold:
            return {
                "username": username,
                "ip_address": ip_address,
                "source": source,
                "failed_attempts": max(ip_count, user_count),
                "trigger": "ip" if ip_count >= user_count else "username",
            }
        return None
