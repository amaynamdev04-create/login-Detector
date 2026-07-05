"""Risk scoring engine for login attempts."""

from __future__ import annotations


def calculate_risk(status: str, ip_address: str, username: str, whitelist: set[str] | list[str]) -> int:
    """Calculate a deterministic risk score for a login attempt."""
    score = 10 if status == "success" else 55
    if status == "failed":
        score += 10
    if username.lower() in {"admin", "root", "administrator"}:
        score += 10
    if ip_address not in set(whitelist):
        score += 10
    return min(score, 100)
