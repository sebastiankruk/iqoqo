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
