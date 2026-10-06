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
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.db.models import Item, User, db


def test_get_profile(client):
    # Register and login first (using the test_auth flow)
    client.post("/api/auth/register", json={"email": "prof@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "prof@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]

    response = client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["data"]["email"] == "prof@iqoqo.local"


def test_profile_includes_avatar_field(client):
    # Create a user directly with avatar_url and ensure the profile endpoint returns it
    user = User(email="avatar@iqoqo.local", display_name="Avatar Test", avatar_url="https://lh3.googleusercontent.com/a/test")
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()

    # Generate a token for this user

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "roles": [],
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, client.application.config["JWT_SECRET_KEY"], algorithm="HS256")

    response = client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["data"].get("avatar_url") == "https://lh3.googleusercontent.com/a/test"


def test_update_profile(client):
    client.post("/api/auth/register", json={"email": "update@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "update@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]

    response = client.put("/api/profile/", headers={"Authorization": f"Bearer {token}"}, json={"display_name": "New Name"})
    assert response.status_code == 200
    assert json.loads(response.data)["data"]["display_name"] == "New Name"


def test_delete_account_requires_email_confirmation(client):
    """The unconditional delete must refuse and must not remove anything.

    A single authenticated call that irreversibly deletes an account is what the
    confirmation flow exists to replace, so the legacy route has to keep refusing
    rather than quietly forwarding somewhere that would delete on a session
    cookie alone.
    """
    client.post("/api/auth/register", json={"email": "delete@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "delete@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]

    # Verify user exists
    user = User.query.filter_by(email="delete@iqoqo.local").first()
    assert user is not None

    response = client.delete("/api/profile/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 409
    body = response.get_json()
    assert "requires confirmation by email" in body["error"]
    assert body["replacement"] == "/api/account/deletion/request"

    # Verify user is NOT removed (blocked)
    user_after = User.query.filter_by(email="delete@iqoqo.local").first()
    assert user_after is not None


def test_user_to_dict_includes_avatar(client):
    test_user = User(email="test@example.com", display_name="Test", avatar_url="https://lh3.googleusercontent.com/a/test")
    test_user.set_password("test-password")
    db.session.add(test_user)
    db.session.commit()

    user_dict = test_user.to_dict()
    assert "avatar_url" in user_dict
    assert user_dict["avatar_url"] == "https://lh3.googleusercontent.com/a/test"


def test_update_profile_bio_length_limit(client):
    client.post("/api/auth/register", json={"email": "biotest@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "biotest@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Bio exceeding 500 characters
    oversized_bio = "a" * 501
    resp = client.put("/api/profile/", headers=headers, json={"bio": oversized_bio})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Biography cannot exceed 500 characters"

    # Bio exactly 500 characters
    valid_bio = "b" * 500
    resp_valid = client.put("/api/profile/", headers=headers, json={"bio": valid_bio})
    assert resp_valid.status_code == 200
    assert resp_valid.get_json()["data"]["bio"] == valid_bio


def test_update_profile_settings_bio_length_limit(client):
    """PATCH /api/profile/settings must enforce the same 500-char bio limit as PUT."""
    client.post("/api/auth/register", json={"email": "biosettings@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "biosettings@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]
    headers = {"Authorization": f"Bearer {token}"}

    oversized_bio = "a" * 501
    resp = client.patch("/api/profile/settings", headers=headers, json={"bio": oversized_bio})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Biography cannot exceed 500 characters"

    valid_bio = "b" * 500
    resp_valid = client.patch("/api/profile/settings", headers=headers, json={"bio": valid_bio})
    assert resp_valid.status_code == 200
    assert resp_valid.get_json()["data"]["bio"] == valid_bio


def test_update_profile_settings_bio_sanitization(client):
    """PATCH /api/profile/settings must strip HTML, not just enforce length."""
    client.post("/api/auth/register", json={"email": "xsssettings@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "xsssettings@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"bio": "<p>Hello</p> <img src=x onerror=alert(1)>World<iframe src='//bad.site'></iframe>"}
    resp = client.patch("/api/profile/settings", headers=headers, json=payload)
    assert resp.status_code == 200
    bio = resp.get_json()["data"]["bio"]
    assert bio == "Hello World"
    assert "<" not in bio
    assert ">" not in bio


def test_update_profile_settings_bio_non_string_does_not_crash(client):
    """A null or non-string bio must be handled, not raise (regression: 500)."""
    client.post("/api/auth/register", json={"email": "biobad@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "biobad@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp_null = client.patch("/api/profile/settings", headers=headers, json={"bio": None})
    assert resp_null.status_code == 200
    assert resp_null.get_json()["data"]["bio"] is None

    resp_int = client.patch("/api/profile/settings", headers=headers, json={"bio": 12345})
    assert resp_int.status_code == 200
    assert resp_int.get_json()["data"]["bio"] == "12345"


def test_update_profile_html_sanitization(client):
    """HTML tags in bio and display_name must be stripped by bleach.clean()."""
    client.post("/api/auth/register", json={"email": "xss@iqoqo.local", "password": "test-password"})
    res = client.post("/api/auth/login", json={"email": "xss@iqoqo.local", "password": "test-password"})
    token = json.loads(res.data)["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "display_name": "<b>Evil</b> <script>alert('xss')</script>Name",
        "bio": "<p>Hello</p> <img src=x onerror=alert(1)>World<iframe src='//bad.site'></iframe>",
    }
    resp = client.put("/api/profile/", headers=headers, json=payload)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["display_name"] == "Evil alert('xss')Name"
    assert "<" not in data["display_name"]
    assert ">" not in data["display_name"]
    assert data["bio"] == "Hello World"
    assert "<" not in data["bio"]
    assert ">" not in data["bio"]
