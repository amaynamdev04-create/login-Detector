"""Tests for alert creation."""

from datetime import datetime, timezone

from flask import Flask

from database.database import db
from database.models import Alert, BlockedIP
from monitor.alerts import create_alert


def test_create_alert_persists_records():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        alert = create_alert(
            {
                "username": "admin",
                "ip_address": "192.168.1.20",
                "failed_attempts": 5,
                "trigger": "ip",
            },
            block_duration_minutes=15,
        )
        assert alert.id is not None
        assert Alert.query.count() == 1
        assert BlockedIP.query.count() == 1
