"""Authentication service helpers for the built-in login flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json

from flask import current_app

from database.models import AppUser, BlockedIP
from monitor.watcher import monitoring_service
from services.network import ClientNetwork, normalize_ip, resolve_client_network

MANUAL_BLACKLIST_SOURCE = "manual-blacklist"


@dataclass
class RuntimeBlock:
    """In-memory block representation for IPs blacklisted in settings."""

    ip_address: str
    blocked_at: datetime
    expires_at: datetime
    source: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": None,
            "ip_address": self.ip_address,
            "blocked_at": self.blocked_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "source": self.source,
            "reason": self.reason,
            "blocked_at_display": format_block_time(self.blocked_at),
            "expires_at_display": format_block_time(self.expires_at),
        }


def get_client_network(request) -> ClientNetwork:
    """Resolve structured client network details for the current request."""
    private_ip = request.form.get("private_ip") or request.headers.get("X-Client-Private-IP")
    return resolve_client_network(request, private_ip=private_ip)


def format_block_time(value: datetime) -> str:
    """Render a user-friendly local timestamp for block messaging."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local_value = value.astimezone()
    tzname = local_value.tzname()
    # Prefer a numeric offset when the tz name is 'UTC' or unavailable
    if not tzname or tzname == "UTC":
        offset = local_value.strftime("%z") or "+0000"
        # format +HHMM -> +HH:MM
        offset = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else offset
        timezone_label = offset
    else:
        timezone_label = tzname
    return f"{local_value.strftime('%d %b %Y, %I:%M:%S %p')} {timezone_label}"


def build_blacklist_block(ip_address: str) -> RuntimeBlock:
    blocked_at = datetime.now(timezone.utc)
    expires_at = blocked_at + timedelta(days=3650)
    return RuntimeBlock(
        ip_address=ip_address,
        blocked_at=blocked_at,
        expires_at=expires_at,
        source=MANUAL_BLACKLIST_SOURCE,
        reason="IP address is manually blacklisted in settings.",
    )


def get_active_block(ip_address: str) -> BlockedIP | RuntimeBlock | None:
    """Return the active block for the IP address, if any."""
    ip_address = normalize_ip(ip_address)
    blacklist = set(current_app.config.get("BLACKLIST_IPS", []))
    if ip_address in blacklist:
        return build_blacklist_block(ip_address)

    block = BlockedIP.query.filter_by(ip_address=ip_address).first()
    if not block:
        return None
    expires_at = block.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return None
    return block


def write_login_event(
    username: str,
    client_network: ClientNetwork,
    success: bool,
    log_file_path: str,
    source: str,
    request=None,
) -> None:
    """Write a login attempt into the monitored log file and ingest it immediately."""
    event_time = datetime.now(timezone.utc)
    timestamp = event_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    status_word = "Success" if success else "Failed"
    level = "INFO" if success else "ERROR"
    payload = {
        "timestamp": event_time,
        "username": username,
        "ip_address": client_network.public_ip,
        "public_ip": client_network.public_ip,
        "private_ip": client_network.private_ip,
        "ip_version": client_network.ip_version,
        "source": source,
        "status": "success" if success else "failed",
        "message": f"Login {status_word}",
        "request": request,
    }
    if not current_app.config.get("ENABLE_LOG_WATCHER", True):
        monitoring_service.process_entry(payload)
        return
    metadata = {
        "public_ip": client_network.public_ip,
        "private_ip": client_network.private_ip,
        "ip_version": client_network.ip_version,
        "source": source,
    }
    line = (
        f"{timestamp} {level} Login {status_word} user={username} "
        f"ip={client_network.public_ip} source={source} meta={json.dumps(metadata, separators=(',', ':'))}\n"
    )
    with open(log_file_path, "a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
    monitoring_service.read_new_lines()


def authenticate_user(username: str, password: str) -> AppUser | None:
    """Validate the submitted username and password."""
    user = AppUser.query.filter_by(username=username).first()
    if not user:
        return None
    return user if user.check_password(password) else None
