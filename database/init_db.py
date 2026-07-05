"""Database initialization helpers."""

from __future__ import annotations

from pathlib import Path
import logging

from sqlalchemy import text

from database.database import db
from database.models import Alert, AppUser, BlockedIP, LoginAttempt
from monitor.parser import parse_log_line
from monitor.watcher import monitoring_service
from utils.helper import read_lines

LOGGER = logging.getLogger(__name__)


def initialize_database(app) -> None:
    """Initialize the database and optionally load historical logs."""
    db.init_app(app)
    app.config.from_mapping(
        APP_DISPLAY_NAME="Login Attempt Monitor",
        APP_OWNER_NAME=app.config["OWNER_NAME"],
    )
    with app.app_context():
        db.create_all()
        run_schema_updates()
        if app.config["CLEAN_DEMO_DATA"]:
            remove_demo_data()
        seed_bootstrap_user()
        if app.config["INGEST_HISTORICAL_LOGS"]:
            sample_log_path = Path(app.config["LOG_FILE_PATH"])
            if sample_log_path.exists():
                for line in read_lines(sample_log_path):
                    parsed = parse_log_line(line)
                    if parsed:
                        monitoring_service.process_entry(parsed, from_history=True)


def seed_bootstrap_user() -> None:
    """Create the bootstrap application user when absent."""
    existing_usernames = {username for (username,) in db.session.query(AppUser.username).all()}

    from flask import current_app

    bootstrap_username = current_app.config["BOOTSTRAP_USERNAME"].strip()
    if not bootstrap_username:
        LOGGER.warning("BOOTSTRAP_USERNAME is empty; skipping bootstrap user creation.")
        return
    if bootstrap_username in existing_usernames:
        return

    user = AppUser(
        username=bootstrap_username,
        full_name=current_app.config["BOOTSTRAP_FULL_NAME"].strip() or current_app.config["OWNER_NAME"],
        role=current_app.config["BOOTSTRAP_ROLE"].strip() or "Administrator",
    )
    user.set_password(current_app.config["BOOTSTRAP_PASSWORD"])
    db.session.add(user)
    db.session.commit()


def remove_demo_data() -> None:
    """Remove demo users and seeded placeholder records from bundled project data."""
    placeholder_users = {"admin", "analyst"}
    placeholder_names = {"Alex Morgan", "Jordan Lee", "John Doe", "Demo User", "Test User", "Sample Data"}

    AppUser.query.filter(
        (AppUser.username.in_(placeholder_users)) | (AppUser.full_name.in_(placeholder_names))
    ).delete(synchronize_session=False)
    LoginAttempt.query.filter(LoginAttempt.username.in_(placeholder_users)).delete(synchronize_session=False)
    Alert.query.filter(Alert.username.in_(placeholder_users)).delete(synchronize_session=False)
    BlockedIP.query.filter(BlockedIP.source == "built-in-portal").delete(synchronize_session=False)
    db.session.commit()


def run_schema_updates() -> None:
    """Apply lightweight SQLite-safe schema updates for new fields."""
    inspector = db.inspect(db.engine)
    table_columns = {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in ("login_attempts", "alerts", "blocked_ips", "app_users")
    }
    statements = []
    if "source" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN source VARCHAR(120) NOT NULL DEFAULT 'unknown'")
    if "public_ip" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN public_ip VARCHAR(64) NOT NULL DEFAULT '127.0.0.1'")
    if "private_ip" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN private_ip VARCHAR(64)")
    if "ip_version" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN ip_version VARCHAR(10)")
    if "source" not in table_columns["alerts"]:
        statements.append("ALTER TABLE alerts ADD COLUMN source VARCHAR(120) NOT NULL DEFAULT 'unknown'")
    if "source" not in table_columns["blocked_ips"]:
        statements.append("ALTER TABLE blocked_ips ADD COLUMN source VARCHAR(120) NOT NULL DEFAULT 'unknown'")
    if "country_code" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN country_code VARCHAR(10) NOT NULL DEFAULT 'Unknown'")
    if "region" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN region VARCHAR(120) NOT NULL DEFAULT 'Unknown'")
    if "city" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN city VARCHAR(120) NOT NULL DEFAULT 'Unknown'")
    if "timezone" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN timezone VARCHAR(120) NOT NULL DEFAULT 'Unknown'")
    if "isp" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN isp VARCHAR(255) NOT NULL DEFAULT 'Unknown'")
    if "latitude" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN latitude FLOAT")
    if "longitude" not in table_columns["login_attempts"]:
        statements.append("ALTER TABLE login_attempts ADD COLUMN longitude FLOAT")
    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
        inspector = db.inspect(db.engine)
        table_columns["login_attempts"] = {column["name"] for column in inspector.get_columns("login_attempts")}
    if "public_ip" in table_columns["login_attempts"]:
        db.session.execute(
            text(
                "UPDATE login_attempts "
                "SET public_ip = COALESCE(NULLIF(public_ip, ''), ip_address), "
                "ip_version = COALESCE(ip_version, CASE "
                "WHEN instr(COALESCE(NULLIF(public_ip, ''), ip_address), ':') > 0 THEN 'IPv6' "
                "ELSE 'IPv4' END)"
            )
        )
    if "country_code" in table_columns["login_attempts"]:
        db.session.execute(
            text(
                "UPDATE login_attempts SET "
                "country = COALESCE(NULLIF(country, ''), 'Unknown'), "
                "country_code = COALESCE(NULLIF(country_code, ''), 'Unknown'), "
                "region = COALESCE(NULLIF(region, ''), 'Unknown'), "
                "city = COALESCE(NULLIF(city, ''), 'Unknown'), "
                "timezone = COALESCE(NULLIF(timezone, ''), 'Unknown'), "
                "isp = COALESCE(NULLIF(isp, ''), 'Unknown')"
            )
        )
    db.session.commit()
