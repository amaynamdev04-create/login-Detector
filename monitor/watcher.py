"""Real-time file monitoring for authentication logs."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from database.database import db
from database.models import LoginAttempt
from monitor.alerts import create_alert
from monitor.detector import BruteForceDetector
from services.network import GeoDetails, resolve_geo_details
from services.risk_engine import calculate_risk

LOGGER = logging.getLogger(__name__)


class LogFileEventHandler(FileSystemEventHandler):
    """Handle modified log files by reading new lines from the tail."""

    def __init__(self, service: "MonitoringService") -> None:
        self.service = service

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        if Path(event.src_path).resolve() == self.service.log_path.resolve():
            self.service.read_new_lines()


class MonitoringService:
    """Singleton-style service responsible for parsing and detection."""

    def __init__(self) -> None:
        self.detector = BruteForceDetector()
        self.observer: Observer | None = None
        self.log_path = Path("data/login_attempts.log")
        self.file_position = 0
        self.block_duration_minutes = 15
        self.whitelist: set[str] = set()
        self.app = None
        self._started = False
        self._lock = threading.RLock()

    def configure(
        self,
        log_file: str,
        threshold: int,
        window_seconds: int,
        block_duration_minutes: int,
        whitelist: list[str],
        app=None,
    ) -> None:
        self.log_path = Path(log_file)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)
        self.detector.configure(threshold=threshold, window_seconds=window_seconds)
        self.block_duration_minutes = block_duration_minutes
        self.whitelist = set(whitelist)
        self.app = app

    def start(self) -> None:
        """Start watching the configured log file once per process."""
        with self._lock:
            if self._started:
                return
            if not self.app.config.get("ENABLE_LOG_WATCHER", True):
                LOGGER.info("Log watcher disabled by configuration.")
                self._started = True
                return
            self.read_new_lines()
            handler = LogFileEventHandler(self)
            self.observer = Observer()
            self.observer.schedule(handler, str(self.log_path.parent), recursive=False)
            self.observer.daemon = True
            self.observer.start()
            self._started = True
            LOGGER.info("Started monitoring %s", self.log_path)

    def stop(self) -> None:
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self._started = False

    def read_new_lines(self) -> None:
        """Consume new lines from the watched log file."""
        from monitor.parser import parse_log_line

        with self._lock:
            if self.app is not None:
                with self.app.app_context():
                    self._read_new_lines_without_context(parse_log_line)
                return
            self._read_new_lines_without_context(parse_log_line)

    def _read_new_lines_without_context(self, parse_log_line) -> None:
        """Read pending log lines assuming an app context is already available if needed."""
        with self.log_path.open("r", encoding="utf-8") as handle:
            handle.seek(self.file_position)
            for line in handle:
                parsed = parse_log_line(line)
                if parsed:
                    self.process_entry(parsed)
            self.file_position = handle.tell()

    def process_entry(self, parsed_entry: dict[str, object], from_history: bool = False) -> None:
        """Persist parsed entries and invoke detection logic."""
        public_ip = str(parsed_entry.get("public_ip") or parsed_entry["ip_address"])
        existing = LoginAttempt.query.filter_by(
            timestamp=parsed_entry["timestamp"],
            username=parsed_entry["username"],
            ip_address=public_ip,
            source=parsed_entry.get("source", "unknown"),
            status=parsed_entry["status"],
            message=parsed_entry["message"],
        ).first()
        if existing:
            return

        risk_score = calculate_risk(
            status=str(parsed_entry["status"]),
            ip_address=public_ip,
            username=str(parsed_entry["username"]),
            whitelist=self.whitelist,
        )
        provided_geo = GeoDetails(
            country=str(parsed_entry.get("country") or "Unknown"),
            country_code=str(parsed_entry.get("country_code") or "Unknown"),
            region=str(parsed_entry.get("region") or "Unknown"),
            city=str(parsed_entry.get("city") or "Unknown"),
            timezone=str(parsed_entry.get("timezone") or "Unknown"),
            isp=str(parsed_entry.get("isp") or "Unknown"),
            latitude=parsed_entry.get("latitude"),
            longitude=parsed_entry.get("longitude"),
        )
        looked_up_geo = resolve_geo_details(public_ip, parsed_entry.get("request"))
        geo_details = GeoDetails(
            country=provided_geo.country if provided_geo.country != "Unknown" else looked_up_geo.country,
            country_code=provided_geo.country_code if provided_geo.country_code != "Unknown" else looked_up_geo.country_code,
            region=provided_geo.region if provided_geo.region != "Unknown" else looked_up_geo.region,
            city=provided_geo.city if provided_geo.city != "Unknown" else looked_up_geo.city,
            timezone=provided_geo.timezone if provided_geo.timezone != "Unknown" else looked_up_geo.timezone,
            isp=provided_geo.isp if provided_geo.isp != "Unknown" else looked_up_geo.isp,
            latitude=provided_geo.latitude if provided_geo.latitude is not None else looked_up_geo.latitude,
            longitude=provided_geo.longitude if provided_geo.longitude is not None else looked_up_geo.longitude,
        )
        attempt = LoginAttempt(
            timestamp=parsed_entry["timestamp"],
            username=str(parsed_entry["username"]),
            ip_address=public_ip,
            public_ip=public_ip,
            private_ip=str(parsed_entry["private_ip"]) if parsed_entry.get("private_ip") else None,
            ip_version=str(parsed_entry["ip_version"]) if parsed_entry.get("ip_version") else None,
            source=str(parsed_entry.get("source", "unknown")),
            status=str(parsed_entry["status"]),
            message=str(parsed_entry["message"]),
            risk_score=risk_score,
            country=geo_details.country,
            country_code=geo_details.country_code,
            region=geo_details.region,
            city=geo_details.city,
            timezone=geo_details.timezone,
            isp=geo_details.isp,
            latitude=geo_details.latitude,
            longitude=geo_details.longitude,
        )
        db.session.add(attempt)
        db.session.commit()

        if public_ip in self.whitelist:
            return

        context = self.detector.record_attempt(
            username=str(parsed_entry["username"]),
            ip_address=public_ip,
            source=str(parsed_entry.get("source", "unknown")),
            status=str(parsed_entry["status"]),
            timestamp=parsed_entry["timestamp"],
        )
        if context:
            LOGGER.warning("Brute-force attack detected for %s", public_ip)
            create_alert(context, self.block_duration_minutes)


monitoring_service = MonitoringService()
