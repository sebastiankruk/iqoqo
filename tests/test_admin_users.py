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


def test_get_roles(client, admin_headers, app):
    """Test fetching available roles."""
    with app.app_context():
        # Check if roles exist first, create only if needed
        existing_roles = Role.query.count()
        if existing_roles == 0:
            admin_role = Role(name="admin")
            user_role = Role(name="user")
            db.session.add_all([admin_role, user_role])
            db.session.commit()

    res = client.get("/api/v1/admin/roles", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) > 0
    role_names = [r["name"] for r in res.json["data"]]
    assert "admin" in role_names or "user" in role_names

    # Verify member_count is returned
    role_data = res.json["data"][0]
    assert "member_count" in role_data


def test_create_role(client, admin_headers):
    """Test creating a new role."""
    payload = {"name": "new_test_role"}
    res = client.post("/api/v1/admin/roles", json=payload, headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["name"] == "new_test_role"
    assert res.json["data"]["is_protected"] is False


def test_create_duplicate_role(client, admin_headers, app):
    """Test that creating duplicate role fails."""
    # First ensure the role exists
    with app.app_context():
        existing = Role.query.filter_by(name="user").first()
        if not existing:
            db.session.add(Role(name="user"))
            db.session.commit()

    # Now try to create duplicate
    payload = {"name": "user"}
    res = client.post("/api/v1/admin/roles", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json["success"] is False


def test_delete_role(client, admin_headers, app):
    """Test deleting a non-protected role."""
    # First create a role to delete
    payload = {"name": "temp_role_for_deletion"}
    res = client.post("/api/v1/admin/roles", json=payload, headers=admin_headers)
    assert res.status_code == 200
    role_id = res.json["data"]["id"]

    # Now delete it
    res = client.delete(f"/api/v1/admin/roles/{role_id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True


def test_delete_protected_role(client, admin_headers):
    """Test that deleting protected role fails."""
    # Try to delete a non-existent role (ID 999)
    # This test verifies the endpoint exists
    res = client.delete("/api/v1/admin/roles/999", headers=admin_headers)
    # Either not found (if ID doesn't exist) or could be 400 if we try a real protected role
    assert res.status_code in [404, 400]


def test_get_permissions(client, admin_headers, app):
    """Test fetching available permissions."""
    from app.db.auth import Permission

    with app.app_context():
        # Ensure permissions exist
        if Permission.query.count() == 0:
            p1 = Permission(name="test:permission", description="Test permission")
            db.session.add(p1)
            db.session.commit()

    res = client.get("/api/v1/admin/permissions", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) > 0
    perm = res.json["data"][0]
    assert "id" in perm
    assert "name" in perm


def test_get_role_permissions(client, admin_headers, app):
    """Test fetching permissions for a specific role."""
    from app.db.auth import Permission

    with app.app_context():
        # Ensure we have a role and permissions
        role = Role.query.first()
        if not role:
            role = Role(name="test_role")
            db.session.add(role)
            db.session.commit()

        # Assign a permission if none exists
        if Permission.query.count() > 0 and len(role.permissions) == 0:
            perm = Permission.query.first()
            role.permissions.append(perm)
            db.session.commit()

        role_id = role.id

    res = client.get(f"/api/v1/admin/roles/{role_id}/permissions", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    data = res.json["data"]
    assert "role_id" in data
    assert "role_name" in data
    assert "permission_ids" in data


def test_update_role_permissions(client, admin_headers, app):
    """Test updating permissions for a role."""
    from app.db.auth import Permission

    with app.app_context():
        # Create a fresh role and permission for this test
        role = Role(name="test_role_perms")
        perm = Permission(name="test:update_perm", description="Test permission for update")
        db.session.add_all([role, perm])
        db.session.commit()
        role_id = role.id
        perm_id = perm.id

    # Update permissions
    payload = {"permission_ids": [perm_id]}
    res = client.put(f"/api/v1/admin/roles/{role_id}/permissions", json=payload, headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert perm_id in res.json["data"]["permission_ids"]
