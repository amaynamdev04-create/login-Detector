"""Database models for login telemetry and alerts."""

from __future__ import annotations

from datetime import datetime, timezone

from database.database import db
from werkzeug.security import check_password_hash, generate_password_hash


def utcnow() -> datetime:
    """Return a UTC timestamp with timezone awareness."""
    return datetime.now(timezone.utc)


class LoginAttempt(db.Model):
    """Stores each parsed login attempt."""

    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=False, index=True)
    public_ip = db.Column(db.String(64), nullable=False, index=True)
    private_ip = db.Column(db.String(64), nullable=True)
    ip_version = db.Column(db.String(10), nullable=True)
    source = db.Column(db.String(120), nullable=False, default="unknown", index=True)
    status = db.Column(db.String(32), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    risk_score = db.Column(db.Integer, nullable=False, default=0)
    country = db.Column(db.String(120), nullable=False, default="Unknown")
    country_code = db.Column(db.String(10), nullable=False, default="Unknown")
    region = db.Column(db.String(120), nullable=False, default="Unknown")
    city = db.Column(db.String(120), nullable=False, default="Unknown")
    timezone = db.Column(db.String(120), nullable=False, default="Unknown")
    isp = db.Column(db.String(255), nullable=False, default="Unknown")
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self) -> dict[str, object]:
        """Serialize the model for API responses."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "username": self.username,
            "ip_address": self.ip_address,
            "public_ip": self.public_ip,
            "private_ip": self.private_ip,
            "ip_version": self.ip_version,
            "source": self.source,
            "status": self.status,
            "message": self.message,
            "risk_score": self.risk_score,
            "country": self.country,
            "country_code": self.country_code,
            "region": self.region,
            "city": self.city,
            "timezone": self.timezone,
            "isp": self.isp,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class Alert(db.Model):
    """Stores generated security alerts."""

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=False, index=True)
    source = db.Column(db.String(120), nullable=False, default="unknown", index=True)
    failed_attempts = db.Column(db.Integer, nullable=False)
    severity = db.Column(db.String(32), nullable=False, index=True)
    action = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "username": self.username,
            "ip_address": self.ip_address,
            "source": self.source,
            "failed_attempts": self.failed_attempts,
            "severity": self.severity,
            "action": self.action,
            "description": self.description,
        }


class BlockedIP(db.Model):
    """Stores temporarily blocked IP addresses."""

    __tablename__ = "blocked_ips"

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(64), nullable=False, unique=True, index=True)
    blocked_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    source = db.Column(db.String(120), nullable=False, default="unknown", index=True)
    reason = db.Column(db.String(255), nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "ip_address": self.ip_address,
            "blocked_at": self.blocked_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "source": self.source,
            "reason": self.reason,
        }


class AppUser(db.Model):
    """Application user that can authenticate through the built-in login page."""

    __tablename__ = "app_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False, default="User")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    def set_password(self, password: str) -> None:
        """Persist a hashed password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a candidate password."""
        return check_password_hash(self.password_hash, password)
