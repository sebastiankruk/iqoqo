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
# pylint: disable=too-many-return-statements, broad-exception-caught, inconsistent-return-statements

import os

from flask import Blueprint, jsonify, request

from app.api.decorators import admin_required
from app.db.models import InstanceSettings, Permission, Role, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/v1/admin")


def _get_current_user() -> User:
    """Get the current user from request context."""
    return db.session.get(User, request.user_id)


def _has_permission(user: User, permission: str) -> bool:
    """Check if user has a specific permission through their roles."""
    if not user:
        return False
    for role in getattr(user, "roles", []):
        for perm in getattr(role, "permissions", []):
            if perm.name == permission:
                return True
    return False


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
    user = _get_current_user()

    if not _has_permission(user, "read:users"):
        return jsonify({"success": False, "error": "Permission denied: read:users required"}), 403

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)

    query = User.query

    if search:
        query = query.filter(db.or_(User.email.ilike(f"%{search}%"), User.display_name.ilike(f"%{search}%")))

    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))

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
    user = _get_current_user()

    if not _has_permission(user, "write:users"):
        return jsonify({"success": False, "error": "Permission denied: write:users required"}), 403

    user_obj = User.query.get_or_404(user_id)
    data = request.json or {}

    if "is_active" in data:
        user_obj.is_active = bool(data["is_active"])

    if "roles" in data and isinstance(data["roles"], list):
        new_roles = Role.query.filter(Role.name.in_(data["roles"])).all()
        user_obj.roles = new_roles

    db.session.commit()
    return jsonify({"success": True, "data": _format_user(user_obj)})


@admin_bp.route("/roles", methods=["GET", "POST"])
@admin_required
def get_roles():
    """Get all available roles for RBAC assignment, or create a new role."""
    user = _get_current_user()

    if request.method == "POST":
        if not _has_permission(user, "write:roles"):
            return jsonify({"success": False, "error": "Permission denied: write:roles required"}), 403

        data = request.json or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"success": False, "error": "Role name is required"}), 400
        if len(name) > 50:
            return jsonify({"success": False, "error": "Role name too long (max 50 chars)"}), 400
        if Role.query.filter_by(name=name).first():
            return jsonify({"success": False, "error": "Role already exists"}), 400
        role = Role(name=name)
        db.session.add(role)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": role.id, "name": role.name, "is_protected": False}})

    if not _has_permission(user, "read:roles"):
        return jsonify({"success": False, "error": "Permission denied: read:roles required"}), 403

    roles = Role.query.all()
    protected_roles = {"admin", "user", "contributor"}
    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "id": r.id,
                    "name": r.name,
                    "is_protected": r.name.lower() in protected_roles,
                    "member_count": r.users.count(),
                    "permission_count": len(r.permissions),
                }
                for r in roles
            ],
        }
    )


@admin_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@admin_required
def delete_role(role_id):
    """Delete a role (only non-protected roles can be deleted)."""
    user = _get_current_user()

    if not _has_permission(user, "write:roles"):
        return jsonify({"success": False, "error": "Permission denied: write:roles required"}), 403

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
    user = _get_current_user()

    if not _has_permission(user, "read:roles"):
        return jsonify({"success": False, "error": "Permission denied: read:roles required"}), 403

    permissions = Permission.query.all()
    return jsonify({"success": True, "data": [{"id": p.id, "name": p.name, "description": p.description} for p in permissions]})


@admin_bp.route("/roles/<int:role_id>/permissions", methods=["GET", "PUT"])
@admin_required
def manage_role_permissions(role_id):
    """Get or update permissions for a specific role."""
    user = _get_current_user()

    if not _has_permission(user, "write:roles"):
        return jsonify({"success": False, "error": "Permission denied: write:roles required"}), 403

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

    data = request.json or {}
    permission_ids = data.get("permission_ids", [])
    permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all() if permission_ids else []
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


API_KEYS = {
    "GOOGLE_BOOKS_API_KEY",
    "DISCOGS_USER_TOKEN",
    "TMDB_API_KEY",
    "TMDB_API_READ_ACCESS_TOKEN",
    "BGG_API_TOKEN",
    "LOCAL_SD_URL",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "UPC_ITEM_DB_KEY",
    "UPC_DATABASE_ORG_KEY",
    "ALLEGRO_CLIENT_ID",
    "ALLEGRO_CLIENT_SECRET",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
}

FEDERATION_KEYS = {"FEDERATION_ENABLED", "FEDERATION_BASE_URL"}

AFFILIATE_KEYS = {"AFFILIATE_AMAZON", "AFFILIATE_ALLEGRO", "AFFILIATE_EMPIK"}

INTERNAL_KEYS = {"instance_name", "IQOQO_KNOWN_JUNK_PHASHES"}


def _mask_api_key(value: str) -> str:
    """Mask API key showing only last 4 characters."""
    if not value:
        return ""
    if len(value) >= 8:
        return f"***{value[-4:]}"
    return "***"


@admin_bp.route("/settings", methods=["GET", "PUT"])
@admin_required
# pylint: disable=too-many-return-statements, broad-exception-caught, inconsistent-return-statements
def manage_settings():
    """Manage global instance settings with category-based RBAC."""
    user = _get_current_user()

    category = request.args.get("category", "all")

    if request.method == "GET":
        can_external = _has_permission(user, "config:external_apis")
        can_federation = _has_permission(user, "config:federation")
        can_affiliate = _has_permission(user, "config:affiliate")
        can_internal = _has_permission(user, "config:internal")

        # Get all DB settings
        db_settings = {s.key: s.value for s in InstanceSettings.query.all()}

        # Get Flask config keys
        try:
            from flask import current_app

            flask_config = current_app.config if current_app else {}
        except Exception:
            flask_config = {}

        result = {}

        # Process API keys (external)
        if can_external:
            for key in API_KEYS:
                source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
                value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
                if value:
                    result[key] = {"value": _mask_api_key(str(value)), "source": source}
                else:
                    result[key] = {"value": "", "source": source}

        # Process Federation keys
        if can_federation:
            for key in FEDERATION_KEYS:
                source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
                value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
                if value:
                    result[key] = {"value": str(value), "source": source}
                else:
                    result[key] = {"value": "", "source": source}

        # Process Affiliate keys
        if can_affiliate:
            for key in AFFILIATE_KEYS:
                source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
                value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
                if value:
                    result[key] = {"value": str(value), "source": source}
                else:
                    result[key] = {"value": "", "source": source}

        # Process Internal keys
        if can_internal:
            for key in INTERNAL_KEYS:
                source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
                value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
                if value:
                    result[key] = {"value": str(value), "source": source}
                else:
                    result[key] = {"value": "", "source": source}

        if category == "federation" and not can_federation:
            return jsonify({"success": False, "error": "Permission denied: config:federation required"}), 403
        if category == "affiliate" and not can_affiliate:
            return jsonify({"success": False, "error": "Permission denied: config:affiliate required"}), 403
        if category == "apikeys" and not can_external:
            return jsonify({"success": False, "error": "Permission denied: config:external_apis required"}), 403
        if category == "internal" and not can_internal:
            return jsonify({"success": False, "error": "Permission denied: config:internal required"}), 403

        return jsonify({"success": True, "data": result})

    if request.method == "PUT":
        can_external = _has_permission(user, "config:external_apis")
        can_federation = _has_permission(user, "config:federation")
        can_affiliate = _has_permission(user, "config:affiliate")
        can_internal = _has_permission(user, "config:internal")

        data = request.json or {}
        saved = {}

        for key, value in data.items():
            if key in API_KEYS and not can_external:
                continue
            if key in FEDERATION_KEYS and not can_federation:
                continue
            if key in AFFILIATE_KEYS and not can_affiliate:
                continue
            if key in INTERNAL_KEYS and not can_internal:
                continue

            if isinstance(value, str) and value.startswith("***"):
                continue

            setting = InstanceSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = InstanceSettings(key=key, value=value)
                db.session.add(setting)

            saved[key] = value

        db.session.commit()
        return jsonify({"success": True, "data": saved})
