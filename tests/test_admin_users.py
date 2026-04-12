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

"""Tests for the admin user management API endpoints."""

# pylint: disable=redefined-outer-name  # pytest fixtures

from app.db.models import Role, User, db


def test_get_users_unauthorized(client):
    """Ensure unauthenticated users are blocked."""
    res = client.get("/api/v1/admin/users")
    assert res.status_code in [401, 403]


def test_get_users_forbidden(client, normal_user_headers):
    """Ensure non-admin users get forbidden."""
    res = client.get("/api/v1/admin/users", headers=normal_user_headers)
    assert res.status_code in [401, 403]


def test_get_users_admin(client, admin_headers, app):
    """Test fetching, searching, and filtering users with admin rights."""
    with app.app_context():
        u1 = User(email="active@iqoqo.local", display_name="Active Jane", is_active=True)
        u2 = User(email="suspended@iqoqo.local", display_name="Suspended Joe", is_active=False)
        db.session.add_all([u1, u2])
        db.session.commit()

    # 1. Fetch all users (Admin + 2 injected = 3 minimum)
    res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) >= 3

    # 2. Test search capability
    res_search = client.get("/api/v1/admin/users?search=suspended", headers=admin_headers)
    assert res_search.status_code == 200
    assert len(res_search.json["data"]) == 1
    assert res_search.json["data"][0]["email"] == "suspended@iqoqo.local"

    # 3. Test filter capability
    res_filter = client.get("/api/v1/admin/users?status=inactive", headers=admin_headers)
    assert res_filter.status_code == 200
    assert len(res_filter.json["data"]) == 1
    assert res_filter.json["data"][0]["is_active"] is False


def test_update_user_rbac(client, admin_headers, app):
    """Test modifying a user's active status and RBAC roles."""
    with app.app_context():
        u = User(email="target@iqoqo.local", is_active=True)
        custodian_role = Role(name="custodian")
        db.session.add_all([u, custodian_role])
        db.session.commit()
        user_uuid = str(u.id)

    # Test updating user via API
    payload = {"is_active": False, "roles": ["custodian"]}
    res = client.put(f"/api/v1/admin/users/{user_uuid}", json=payload, headers=admin_headers)

    assert res.status_code == 200
    assert res.json["success"] is True
    data = res.json["data"]
    assert data["is_active"] is False
    assert "custodian" in data["roles"]
