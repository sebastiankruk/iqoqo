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

from app.db.models import Item, User, db


def test_get_profile(client):
    # Register and login first (using the test_auth flow)
    client.post("/api/auth/register", json={"email": "prof@iqoqo.local", "password": "pass"})
    res = client.post("/api/auth/login", json={"email": "prof@iqoqo.local", "password": "pass"})
    token = json.loads(res.data)["token"]

    response = client.get("/api/profile/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["data"]["email"] == "prof@iqoqo.local"


def test_update_profile(client):
    client.post("/api/auth/register", json={"email": "update@iqoqo.local", "password": "pass"})
    res = client.post("/api/auth/login", json={"email": "update@iqoqo.local", "password": "pass"})
    token = json.loads(res.data)["token"]

    response = client.put("/api/profile/", headers={"Authorization": f"Bearer {token}"}, json={"display_name": "New Name"})
    assert response.status_code == 200
    assert json.loads(response.data)["display_name"] == "New Name"


def test_delete_account_right_to_be_forgotten(client):
    client.post("/api/auth/register", json={"email": "delete@iqoqo.local", "password": "pass"})
    res = client.post("/api/auth/login", json={"email": "delete@iqoqo.local", "password": "pass"})
    token = json.loads(res.data)["token"]

    # Verify user exists
    user = User.query.filter_by(email="delete@iqoqo.local").first()
    assert user is not None

    response = client.delete("/api/profile/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # Verify user is completely removed
    user_after = User.query.filter_by(email="delete@iqoqo.local").first()
    assert user_after is None
