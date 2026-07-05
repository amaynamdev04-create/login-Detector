"""Parse authentication log lines into structured events."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?) "
    r"(?P<level>[A-Z]+) Login (?P<outcome>Success|Failed) "
    r"user=(?P<username>[\w.@-]+) ip=(?P<ip_address>[0-9a-fA-F:.]+)"
    r"(?: source=(?P<source>[\w.-]+))?"
    r"(?: meta=(?P<meta>\{.*\}))?$"
)


def parse_log_line(line: str) -> dict[str, object] | None:
    """Parse a log line into a structured dictionary."""
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None

    data = match.groupdict()
    status = "success" if data["outcome"].lower() == "success" else "failed"
    timestamp_format = "%Y-%m-%d %H:%M:%S.%f" if "." in data["timestamp"] else "%Y-%m-%d %H:%M:%S"
    timestamp = datetime.strptime(data["timestamp"], timestamp_format).replace(tzinfo=timezone.utc)
    metadata = {}
    if data.get("meta"):
        try:
            metadata = json.loads(data["meta"])
        except json.JSONDecodeError:
            metadata = {}
    return {
        "timestamp": timestamp,
        "username": data["username"],
        "ip_address": data["ip_address"],
        "public_ip": metadata.get("public_ip") or data["ip_address"],
        "private_ip": metadata.get("private_ip"),
        "ip_version": metadata.get("ip_version"),
        "source": data.get("source") or "unknown",
        "status": status,
        "message": f"Login {data['outcome']}",
    }
