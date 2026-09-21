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

import json

import pytest

from app.db.models import Role, User, db


@pytest.fixture(autouse=True)
def setup_roles(app):
    """Ensure the default 'user' role exists in the test DB before running auth tests."""
    if not Role.query.filter_by(name="user").first():
        db.session.add(Role(name="user"))
        db.session.commit()


def test_user_registration(client):
    response = client.post(
        "/api/auth/register", json={"email": "test@iqoqo.local", "password": "securepassword", "display_name": "Test User"}
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "token" in data

    user = User.query.filter_by(email="test@iqoqo.local").first()
    assert user is not None
    assert user.check_password("securepassword")
    assert user.roles[0].name == "user"


def test_user_registration_duplicate(client):
    client.post("/api/auth/register", json={"email": "dup@iqoqo.local", "password": "securepassword"})
    response = client.post("/api/auth/register", json={"email": "dup@iqoqo.local", "password": "securepassword"})
    assert response.status_code == 409
    assert b"Email already registered" in response.data


def test_user_registration_missing_fields(client):
    response = client.post("/api/auth/register", json={"email": "missing@iqoqo.local"})
    assert response.status_code == 400


def test_local_login(client):
    # Register first
    client.post("/api/auth/register", json={"email": "login@iqoqo.local", "password": "mypassword"})

    # Attempt login
    response = client.post("/api/auth/login", json={"email": "login@iqoqo.local", "password": "mypassword"})
    assert response.status_code == 200
    assert "token" in json.loads(response.data)


def test_local_login_invalid_credentials(client):
    client.post("/api/auth/register", json={"email": "invalid@iqoqo.local", "password": "mypassword"})
    response = client.post("/api/auth/login", json={"email": "invalid@iqoqo.local", "password": "wrongpassword"})
    assert response.status_code == 401
    assert b"Invalid credentials" in response.data


def test_local_login_missing_fields(client):
    response = client.post("/api/auth/login", json={"email": "login@iqoqo.local"})
    assert response.status_code == 400


def test_logout(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert b"Logged out successfully" in response.data


def test_protected_route_without_token(client):
    response = client.delete("/api/items/1")
    assert response.status_code == 401
    assert b"Token missing" in response.data


def test_token_blocklist_expires_at_and_pruning(client, app):
    """Ensure TokenBlocklist records expires_at on logout and prune_expired cleans up old entries."""
    from datetime import UTC, datetime, timedelta

    from app.db.models import TokenBlocklist

    # Register and login to obtain token
    client.post("/api/auth/register", json={"email": "logout_exp@iqoqo.local", "password": "mypassword"})
    login_res = client.post("/api/auth/login", json={"email": "logout_exp@iqoqo.local", "password": "mypassword"})
    token = json.loads(login_res.data)["token"]

    # Logout
    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    with app.app_context():
        # Check that token was recorded with expires_at
        entry = TokenBlocklist.query.first()
        assert entry is not None
        assert entry.expires_at is not None
        exp_dt = entry.expires_at if entry.expires_at.tzinfo else entry.expires_at.replace(tzinfo=UTC)
        assert exp_dt > datetime.now(UTC)

        # Verify constant-time revocation check
        assert TokenBlocklist.is_revoked(entry.jti) is True
        assert TokenBlocklist.is_revoked("unknown-jti") is False
        assert TokenBlocklist.is_revoked(None) is False

        # Add an expired entry
        past_time = datetime.now(UTC) - timedelta(hours=1)
        expired_entry = TokenBlocklist(jti="expired-jti-12345", expires_at=past_time)
        db.session.add(expired_entry)
        db.session.commit()

        # Prune expired tokens
        deleted_count = TokenBlocklist.prune_expired()
        assert deleted_count >= 1

        # Expired token was deleted, valid token remains
        assert TokenBlocklist.query.filter_by(jti="expired-jti-12345").first() is None
        assert TokenBlocklist.query.filter_by(jti=entry.jti).first() is not None


def test_google_login_not_configured(client, app, monkeypatch):
    """Google login should redirect to /login?error=oauth_not_configured instead of crashing with 500."""
    from app.api.auth import oauth

    # Simulate environment and DB without Google OAuth credentials
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    app.config.pop("GOOGLE_CLIENT_ID", None)
    app.config.pop("GOOGLE_CLIENT_SECRET", None)
    oauth._registry.pop("google", None)
    oauth._clients.pop("google", None)

    response = client.get("/api/auth/login/google")
    assert response.status_code == 302
    assert "error=oauth_not_configured" in response.headers["Location"]


def test_google_login_configured_in_db(client, app, monkeypatch):
    """Google login should load credentials from DB InstanceSettings and redirect to Google."""
    from app.api.auth import oauth
    from app.db.models import InstanceSettings

    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    app.config.pop("GOOGLE_CLIENT_ID", None)
    app.config.pop("GOOGLE_CLIENT_SECRET", None)
    oauth._registry.pop("google", None)
    oauth._clients.pop("google", None)

    with app.app_context():
        InstanceSettings.set_value("GOOGLE_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com")
        InstanceSettings.set_value("GOOGLE_CLIENT_SECRET", "test-google-client-secret")

    response = client.get("/api/auth/login/google")
    assert response.status_code == 302
    assert "accounts.google.com" in response.headers["Location"]
    assert "client_id=test-google-client-id.apps.googleusercontent.com" in response.headers["Location"]
