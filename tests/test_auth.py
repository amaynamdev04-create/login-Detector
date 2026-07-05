"""Tests for the built-in authentication flow."""

from datetime import datetime, timedelta, timezone

from app import app
from database.database import db
from database.models import Alert, BlockedIP, LoginAttempt
from monitor.watcher import monitoring_service


def bootstrap_credentials():
    return {
        "username": app.config["BOOTSTRAP_USERNAME"],
        "password": app.config["BOOTSTRAP_PASSWORD"],
    }


def test_login_page_allows_successful_authentication():
    with app.app_context():
        BlockedIP.query.filter_by(ip_address="127.0.0.1").delete()
        db.session.commit()
        client = app.test_client()
        response = client.post(
            "/login",
            data=bootstrap_credentials(),
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")


def test_login_page_rejects_blocked_ip():
    with app.app_context():
        BlockedIP.query.filter_by(ip_address="127.0.0.1").delete()
        db.session.add(
            BlockedIP(
                ip_address="127.0.0.1",
                blocked_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                reason="Test block",
            )
        )
        db.session.commit()

        client = app.test_client()
        response = client.post(
            "/login",
            data=bootstrap_credentials(),
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Login blocked" in response.data
        BlockedIP.query.filter_by(ip_address="127.0.0.1").delete()
        db.session.commit()


def test_login_page_blocks_only_after_five_failed_attempts():
    with app.app_context():
        ip_address = "127.0.0.1"
        source = app.config["DEFAULT_EVENT_SOURCE"]

        LoginAttempt.query.filter_by(ip_address=ip_address, source=source).delete()
        Alert.query.filter_by(ip_address=ip_address, source=source).delete()
        BlockedIP.query.filter_by(ip_address=ip_address).delete()
        db.session.commit()

        monitoring_service.detector.failed_by_ip.clear()
        monitoring_service.detector.failed_by_user.clear()
        monitoring_service.log_path.write_text("", encoding="utf-8")
        monitoring_service.file_position = 0

        client = app.test_client()
        for _ in range(5):
            response = client.post(
                "/login",
                data={"username": app.config["BOOTSTRAP_USERNAME"], "password": "wrong-password"},
                follow_redirects=True,
            )
            assert response.status_code == 200
            assert b"Invalid username or password." in response.data

        failed_attempts = LoginAttempt.query.filter_by(
            ip_address=ip_address,
            source=source,
            status="failed",
        ).count()
        assert failed_attempts == 5

        block = BlockedIP.query.filter_by(ip_address=ip_address).first()
        assert block is not None


def test_blacklisted_ip_blocks_login_immediately_with_friendly_time():
    with app.app_context():
        original_blacklist = list(app.config["BLACKLIST_IPS"])
        original_threshold = app.config["ALERT_THRESHOLD"]
        original_duration = app.config["BLOCK_DURATION_MINUTES"]
        original_whitelist = list(app.config["WHITELIST_IPS"])

        client = app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 1

        response = client.post(
            "/settings/",
            data={
                "alert_threshold": original_threshold,
                "block_duration": original_duration,
                "whitelist": ", ".join(original_whitelist),
                "blacklist": "127.0.0.1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        response = client.post(
            "/login",
            data=bootstrap_credentials(),
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Login blocked for 127.0.0.1 until" in response.data
        assert b"UTC" not in response.data

        app.config["BLACKLIST_IPS"] = original_blacklist
