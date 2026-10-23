# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Tests for in-app notifications API and notification dispatcher."""

import uuid

import pytest

from app.core.notifications import create_notification
from app.db import db
from app.db.auth import User
from app.db.social import Notification


@pytest.fixture
def test_user(app):
    """Create a persistent user for testing notifications."""
    with app.app_context():
        user = User(
            email=f"notify_user_{uuid.uuid4().hex[:8]}@example.com",
            public_username=f"notif_{uuid.uuid4().hex[:6]}",
            display_name="Notification Tester",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        return user_id


@pytest.fixture
def auth_headers(client, app, test_user):
    """Generate JWT authentication headers for test_user."""
    import jwt

    token = jwt.encode({"sub": str(test_user)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_notifications(client, app, test_user, auth_headers):
    """Test creating notifications via helper and listing via API."""
    with app.app_context():
        n1 = create_notification(
            user_id=test_user,
            notification_type="follow_request",
            payload={"message": "Alice wants to follow you"},
            actor_uri="https://remote.library/users/alice",
        )
        n2 = create_notification(
            user_id=test_user,
            notification_type="loan_request",
            payload={"message": "Bob requested Dune"},
            target_iri="/items/42",
        )
        assert n1 is not None
        assert n2 is not None

    res = client.get("/api/v1/notifications", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    assert len(data["notifications"]) == 2
    types = [n["type"] for n in data["notifications"]]
    assert "follow_request" in types
    assert "loan_request" in types


def test_mark_notification_read(client, app, test_user, auth_headers):
    """Test marking a specific notification as read."""
    with app.app_context():
        n = create_notification(
            user_id=test_user,
            notification_type="escalation_resolved",
            payload={"message": "Resolved"},
        )
        notif_id = n.id

    # Mark as read
    res = client.patch(
        "/api/v1/notifications/read",
        json={"notification_ids": [notif_id]},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.get_json()["marked_count"] == 1

    # Check unread count
    list_res = client.get("/api/v1/notifications", headers=auth_headers)
    assert list_res.get_json()["unread_count"] == 0

    # Unread only filter
    unread_res = client.get("/api/v1/notifications?unread_only=true", headers=auth_headers)
    assert unread_res.get_json()["total"] == 0


def test_mark_all_read(client, app, test_user, auth_headers):
    """Test mark-all-read endpoint."""
    with app.app_context():
        create_notification(test_user, "type1", {"msg": "1"})
        create_notification(test_user, "type2", {"msg": "2"})

    res = client.post("/api/v1/notifications/read-all", headers=auth_headers)
    assert res.status_code == 200
    assert res.get_json()["marked_count"] >= 2

    list_res = client.get("/api/v1/notifications", headers=auth_headers)
    assert list_res.get_json()["unread_count"] == 0


def test_notifications_unauthorized(client):
    """Test endpoints reject unauthenticated requests."""
    assert client.get("/api/v1/notifications").status_code == 401
    assert client.patch("/api/v1/notifications/read", json={}).status_code == 401
    assert client.post("/api/v1/notifications/read-all").status_code == 401
