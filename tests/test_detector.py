"""Tests for brute-force detection."""

from datetime import datetime, timedelta, timezone

from monitor.detector import BruteForceDetector


def test_detector_flags_repeated_failures():
    detector = BruteForceDetector(threshold=5, window_seconds=120)
    start = datetime(2026, 6, 30, 12, 30, tzinfo=timezone.utc)
    result = None
    for index in range(5):
        result = detector.record_attempt(
            username="admin",
            ip_address="192.168.1.20",
            source="built-in-portal",
            status="failed",
            timestamp=start + timedelta(seconds=index * 20),
        )
    assert result is not None
    assert result["failed_attempts"] == 5
