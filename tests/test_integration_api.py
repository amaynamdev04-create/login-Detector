"""Tests for external website integration APIs."""

from datetime import datetime, timedelta, timezone

from app import app
from database.database import db
from database.models import Alert, BlockedIP, LoginAttempt


def auth_header():
    return {"X-API-Key": app.config["INGEST_API_KEY"]}


def test_external_login_attempt_ingest_creates_event_and_alert():
    with app.app_context():
        LoginAttempt.query.filter_by(source="storefront").delete()
        Alert.query.filter_by(source="storefront").delete()
        BlockedIP.query.filter_by(ip_address="203.0.113.10").delete()
        db.session.commit()

        client = app.test_client()
        start = datetime(2026, 6, 30, 18, 5, tzinfo=timezone.utc)
        for index in range(5):
            response = client.post(
                "/api/integrations/login-attempt",
                headers=auth_header(),
                json={
                    "username": "alice",
                    "ip_address": "203.0.113.10",
                    "status": "failed",
                    "source": "storefront",
                    "timestamp": (start + timedelta(seconds=index * 10)).isoformat(),
                },
            )
            assert response.status_code == 201

        assert LoginAttempt.query.filter_by(source="storefront").count() >= 5
        assert Alert.query.filter_by(source="storefront").count() >= 1
        assert BlockedIP.query.filter_by(ip_address="203.0.113.10").count() == 1


def test_external_block_check_endpoint_reports_active_block():
    with app.app_context():
        client = app.test_client()
        response = client.get(
            "/api/integrations/check-block",
            headers=auth_header(),
            query_string={"ip_address": "203.0.113.10"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["ip_address"] == "203.0.113.10"
        assert isinstance(payload["blocked"], bool)
