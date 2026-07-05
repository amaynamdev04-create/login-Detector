"""CSV export helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from flask import current_app

from database.models import LoginAttempt

try:
    import pandas as pd
except ImportError:  # pragma: no cover - fallback path depends on runtime environment.
    pd = None


def export_logs_to_csv() -> str:
    """Export login attempts to a CSV file and return the path."""
    export_dir = Path(current_app.config["EXPORT_DIR"])
    export_dir.mkdir(parents=True, exist_ok=True)
    records = [item.to_dict() for item in LoginAttempt.query.order_by(LoginAttempt.timestamp.desc()).all()]
    file_path = export_dir / "login_attempts_export.csv"
    columns = [
        "id",
        "timestamp",
        "username",
        "ip_address",
        "public_ip",
        "private_ip",
        "ip_version",
        "source",
        "status",
        "message",
        "risk_score",
        "country",
        "country_code",
        "region",
        "city",
        "timezone",
        "isp",
        "latitude",
        "longitude",
    ]
    if pd is not None:
        dataframe = pd.DataFrame(records)
        if dataframe.empty:
            dataframe = pd.DataFrame(columns=columns)
        dataframe.to_csv(file_path, index=False)
    else:
        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in records:
                writer.writerow(row)
    return str(file_path)
