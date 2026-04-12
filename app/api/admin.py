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

from flask import Blueprint, jsonify, request

from app.api.decorators import admin_required
from app.db.models import InstanceSettings, Permission, Role, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/v1/admin")


def _format_user(u: User) -> dict:
    """Helper to serialize user for admin views."""
    return {
        "id": str(u.id),
        "email": u.email,
        "display_name": u.display_name,
        "is_active": u.is_active,
        "roles": [r.name for r in u.roles],  # type: ignore[attr-defined]
    }


@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    """Get all users with optional filtering and pagination."""
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)

    query = User.query

    # Global search on email or display name
    if search:
        query = query.filter(db.or_(User.email.ilike(f"%{search}%"), User.display_name.ilike(f"%{search}%")))

    # Status filtering
    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))

    # Order by newest
    query = query.order_by(User.created_at.desc())

    paginated = query.paginate(page=page, per_page=limit, error_out=False)

    return jsonify(
        {
            "success": True,
            "data": [_format_user(u) for u in paginated.items],
            "meta": {"total": paginated.total, "page": paginated.page, "pages": paginated.pages},
        }
    )


@admin_bp.route("/users/<uuid:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    """Update user's active status and RBAC roles."""
    user = User.query.get_or_404(user_id)
    data = request.json or {}

    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    if "roles" in data and isinstance(data["roles"], list):
        # Fetch corresponding Role models from database
        new_roles = Role.query.filter(Role.name.in_(data["roles"])).all()
        user.roles = new_roles

    db.session.commit()
    return jsonify({"success": True, "data": _format_user(user)})


@admin_bp.route("/roles", methods=["GET", "POST"])
@admin_required
def get_roles():
    """Get all available roles for RBAC assignment, or create a new role."""
    if request.method == "POST":
        data = request.json or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"success": False, "error": "Role name is required"}), 400
        if len(name) > 50:
            return jsonify({"success": False, "error": "Role name too long (max 50 chars)"}), 400
        # Check if role already exists
        if Role.query.filter_by(name=name).first():
            return jsonify({"success": False, "error": "Role already exists"}), 400
        role = Role(name=name)
        db.session.add(role)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": role.id, "name": role.name, "is_protected": False}})

    roles = Role.query.all()
    protected_roles = {"admin", "user", "contributor"}
    return jsonify(
        {"success": True, "data": [{"id": r.id, "name": r.name, "is_protected": r.name.lower() in protected_roles} for r in roles]}
    )


@admin_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@admin_required
def delete_role(role_id):
    """Delete a role (only non-protected roles can be deleted)."""
    role = Role.query.get_or_404(role_id)
    protected_roles = {"admin", "user", "contributor"}
    if role.name.lower() in protected_roles:
        return jsonify({"success": False, "error": "Cannot delete protected role"}), 400
    db.session.delete(role)
    db.session.commit()
    return jsonify({"success": True, "data": None})


@admin_bp.route("/permissions", methods=["GET"])
@admin_required
def get_permissions():
    """Get all available permissions that can be assigned to roles."""
    permissions = Permission.query.all()
    return jsonify({"success": True, "data": [{"id": p.id, "name": p.name, "description": p.description} for p in permissions]})


@admin_bp.route("/roles/<int:role_id>/permissions", methods=["GET", "PUT"])
@admin_required
def manage_role_permissions(role_id):
    """Get or update permissions for a specific role."""
    role = Role.query.get_or_404(role_id)

    if request.method == "GET":
        role_permission_ids = {p.id for p in role.permissions}
        return jsonify(
            {
                "success": True,
                "data": {
                    "role_id": role.id,
                    "role_name": role.name,
                    "permission_ids": list(role_permission_ids),
                },
            }
        )

    # PUT - update permissions
    data = request.json or {}
    permission_ids = data.get("permission_ids", [])

    # Fetch permissions by ID
    permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all() if permission_ids else []

    # Replace role's permissions
    role.permissions = permissions
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "data": {
                "role_id": role.id,
                "role_name": role.name,
                "permission_ids": [p.id for p in role.permissions],
            },
        }
    )


@admin_bp.route("/settings", methods=["GET", "PUT"])
@admin_required
def manage_settings():
    """Manage global instance settings."""
    if request.method == "GET":
        settings = InstanceSettings.query.all()
        return jsonify({"success": True, "data": {s.key: s.value for s in settings}})

    data = request.json or {}
    for key, value in data.items():
        setting = InstanceSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = InstanceSettings(key=key, value=value)
            db.session.add(setting)

    db.session.commit()
    return jsonify({"success": True, "data": data})
