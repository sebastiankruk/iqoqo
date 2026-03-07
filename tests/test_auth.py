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

from app.db.models import Role, User


def test_user_registration(client, app_context):
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


def test_local_login(client, app_context):
    # Register first
    client.post("/api/auth/register", json={"email": "login@iqoqo.local", "password": "mypassword"})

    # Attempt login
    response = client.post("/api/auth/login", json={"email": "login@iqoqo.local", "password": "mypassword"})
    assert response.status_code == 200
    assert "token" in json.loads(response.data)


def test_protected_route_without_token(client):
    response = client.delete("/api/items/1")
    assert response.status_code == 401
    assert b"Token missing" in response.data
    assert response.status_code == 401
    assert b"Token missing" in response.data
    assert b"Token missing" in response.data
