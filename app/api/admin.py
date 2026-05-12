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
# pylint: disable=broad-exception-caught, inconsistent-return-statements

import os
from datetime import date

from flask import Blueprint, Response, g, jsonify, request

from app.api.decorators import admin_required, require_auth
from app.core import frbr_service
from app.core.permissions import PermissionName
from app.db.auth import User as AuthUser
from app.db.core import Expression, Item, Manifestation, Work
from app.db.models import InstanceSettings, Permission, Role, User, db
from app.utils.json_utils import parse_meta, sanitize_meta

admin_bp = Blueprint("admin", __name__, url_prefix="/v1/admin")


def _get_current_user() -> User | None:
    """Get the current user from request context."""
    return db.session.get(User, getattr(g, "user_id", None))


def _has_permission(user: User | None, permission: PermissionName | str) -> bool:
    """Check if user has a specific permission through their roles."""
    if not user:
        return False
    perm_val = permission.value if hasattr(permission, "value") else permission
    for role in getattr(user, "roles", []):
        for perm in getattr(role, "permissions", []):
            if perm.name == perm_val:
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
@require_auth
@admin_required
def get_users():
    """Get all users with optional filtering and pagination."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.READ_USERS):
        return jsonify({"success": False, "error": "Permission denied: read:users required"}), 403

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    # QA FIX: Clamp limit to prevent DB/Memory DoS attacks
    limit = min(request.args.get("limit", 50, type=int), 100)

    stmt = db.select(User)

    if search:
        stmt = stmt.filter(db.or_(User.email.ilike(f"%{search}%"), User.display_name.ilike(f"%{search}%")))

    if status == "active":
        stmt = stmt.filter(User.is_active.is_(True))
    elif status == "inactive":
        stmt = stmt.filter(User.is_active.is_(False))

    stmt = stmt.order_by(User.created_at.desc())

    paginated = db.paginate(stmt, page=page, per_page=limit, error_out=False)

    return jsonify(
        {
            "success": True,
            "data": [_format_user(u) for u in paginated.items],
            "meta": {"total": paginated.total, "page": paginated.page, "pages": paginated.pages, "limit": limit},
        }
    )


@admin_bp.route("/users/<uuid:user_id>", methods=["PUT"])
@require_auth
@admin_required
def update_user(user_id):
    """Update user's active status and RBAC roles."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.WRITE_USERS):
        return jsonify({"success": False, "error": "Permission denied: write:users required"}), 403

    user_obj = db.get_or_404(User, user_id)
    data = request.json or {}

    if "is_active" in data:
        user_obj.is_active = bool(data["is_active"])

    if "roles" in data and isinstance(data["roles"], list):
        new_roles = db.session.execute(db.select(Role).filter(Role.name.in_(data["roles"]))).scalars().all()
        user_obj.roles = list(new_roles)

    db.session.commit()
    return jsonify({"success": True, "data": _format_user(user_obj)})


@admin_bp.route("/roles", methods=["GET", "POST"])
@require_auth
@admin_required
def get_roles():
    """Get all available roles for RBAC assignment, or create a new role."""
    user = _get_current_user()

    if request.method == "POST":
        if not _has_permission(user, PermissionName.WRITE_ROLES):
            return jsonify({"success": False, "error": f"Permission denied: {PermissionName.WRITE_ROLES} required"}), 403

        data = request.json or {}
        name = data.get("name", "").strip()
        err = None
        if not name:
            err = "Role name is required"
        elif len(name) > 50:
            err = "Role name too long"
        elif db.session.execute(db.select(Role).filter_by(name=name)).scalar_one_or_none():
            err = "Role already exists"

        if err:
            return jsonify({"success": False, "error": err}), 400

        role = Role(name=name)
        db.session.add(role)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": role.id, "name": role.name, "is_protected": False}})

    if not _has_permission(user, PermissionName.READ_ROLES):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.READ_ROLES} required"}), 403

    roles = db.session.execute(db.select(Role)).scalars().all()
    protected_roles = {"admin", "user", "contributor"}
    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "id": r.id,
                    "name": r.name,
                    "is_protected": r.name.lower() in protected_roles,
                    "member_count": db.session.execute(db.select(db.func.count()).select_from(user_roles).filter_by(role_id=r.id)).scalar()
                    or 0,  # pylint: disable=not-callable
                    "permission_count": len(r.permissions),
                }
                for r in roles
            ],
        }
    )


@admin_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@require_auth
@admin_required
def delete_role(role_id):
    """Delete a role (only non-protected roles can be deleted)."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.WRITE_ROLES):
        return jsonify({"success": False, "error": "Permission denied: write:roles required"}), 403

    role = db.get_or_404(Role, role_id)
    protected_roles = {"admin", "user", "contributor"}
    if role.name.lower() in protected_roles:
        return jsonify({"success": False, "error": "Cannot delete protected role"}), 400
    db.session.delete(role)
    db.session.commit()
    return jsonify({"success": True, "data": None})


@admin_bp.route("/permissions", methods=["GET"])
@require_auth
@admin_required
def get_permissions():
    """Get all available permissions that can be assigned to roles."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.READ_ROLES):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.READ_ROLES} required"}), 403

    permissions = db.session.execute(db.select(Permission)).scalars().all()
    return jsonify(
        {
            "success": True,
            "data": [{"id": p.id, "name": p.name, "description": p.description} for p in permissions],
        }
    )


@admin_bp.route("/roles/<int:role_id>/permissions", methods=["GET", "PUT"])
@require_auth
@admin_required
def manage_role_permissions(role_id):
    """Get or update permissions for a specific role."""
    user = _get_current_user()
    if request.method == "GET":
        if not _has_permission(user, PermissionName.READ_ROLES):
            return jsonify({"success": False, "error": f"Permission denied: {PermissionName.READ_ROLES} required"}), 403
    elif request.method == "PUT":
        if not _has_permission(user, PermissionName.WRITE_ROLES):
            return jsonify({"success": False, "error": f"Permission denied: {PermissionName.WRITE_ROLES} required"}), 403

    role = db.get_or_404(Role, role_id)

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

    # QA FIX: Prevent malicious or accidental stripping of admin role permissions
    if role.name.lower() == "admin":
        return jsonify({"success": False, "error": "Cannot modify permissions of the admin role"}), 400

    data = request.json or {}
    permission_ids = data.get("permission_ids", [])
    permissions = (
        db.session.execute(db.select(Permission).filter(Permission.id.in_(permission_ids))).scalars().all() if permission_ids else []
    )
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

INTERNAL_KEYS = {"instance_name", "IQOQO_KNOWN_JUNK_PHASHES", "MAINTENANCE_MODE"}


def _mask_api_key(value: str) -> str:
    """Mask API key showing only last 4 characters."""
    if not value:
        return ""
    if len(value) >= 8:
        return f"***{value[-4:]}"
    return "***"


def _get_settings(user: User, category: str) -> tuple[Response, int] | dict:
    """Helper for GET /settings."""
    can_external = _has_permission(user, PermissionName.CONFIG_EXTERNAL_APIS)
    can_federation = _has_permission(user, PermissionName.CONFIG_FEDERATION)
    can_affiliate = _has_permission(user, PermissionName.CONFIG_AFFILIATE)
    can_internal = _has_permission(user, PermissionName.CONFIG_INTERNAL)

    if category == "federation" and not can_federation:
        return jsonify({"success": False, "error": "Permission denied"}), 403
    if category == "affiliate" and not can_affiliate:
        return jsonify({"success": False, "error": "Permission denied"}), 403
    if category in {"external_apis", "apikeys"} and not can_external:
        return jsonify({"success": False, "error": "Permission denied"}), 403
    if category == "internal" and not can_internal:
        return jsonify({"success": False, "error": "Permission denied"}), 403

    db_settings = {s.key: s.value for s in db.session.execute(db.select(InstanceSettings)).scalars().all()}
    from flask import current_app

    flask_config = current_app.config if current_app else {}
    result = {}

    def normalize_val(v):
        s_v = str(v or "").lower()
        return s_v if s_v in ("true", "false") else str(v or "")

    if can_external:
        for key in API_KEYS:
            source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
            value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
            # Mask API keys but keep other external settings unmasked
            display_value = (
                (_mask_api_key(str(value)) if value and key not in ("LOCAL_SD_URL",) else str(value or ""))
                if key in API_KEYS and key != "LOCAL_SD_URL"
                else str(value or "")
            )
            result[key] = {"value": display_value, "source": source}

    if can_federation:
        for key in FEDERATION_KEYS:
            source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
            value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
            result[key] = {"value": normalize_val(value), "source": source}

    if can_affiliate:
        for key in AFFILIATE_KEYS:
            source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
            value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
            result[key] = {"value": normalize_val(value), "source": source}

    if can_internal:
        for key in INTERNAL_KEYS:
            source = "db" if key in db_settings else "env" if key in flask_config or os.environ.get(key) else "missing"
            value = db_settings.get(key) or flask_config.get(key) or os.environ.get(key)
            result[key] = {"value": normalize_val(value), "source": source}

    return {"success": True, "data": result}


def _put_settings(user: User, data: dict) -> dict:
    """Helper for PUT /settings."""
    can_external = _has_permission(user, PermissionName.CONFIG_EXTERNAL_APIS)
    can_federation = _has_permission(user, PermissionName.CONFIG_FEDERATION)
    can_affiliate = _has_permission(user, PermissionName.CONFIG_AFFILIATE)
    can_internal = _has_permission(user, PermissionName.CONFIG_INTERNAL)

    key_permissions = {
        **dict.fromkeys(API_KEYS, can_external),
        **dict.fromkeys(FEDERATION_KEYS, can_federation),
        **dict.fromkeys(AFFILIATE_KEYS, can_affiliate),
        **dict.fromkeys(INTERNAL_KEYS, can_internal),
    }

    saved = {}
    for key, value in data.items():
        if not key_permissions.get(key, True):
            continue

        if isinstance(value, str) and value.startswith("***"):
            continue

        setting = db.session.execute(db.select(InstanceSettings).filter_by(key=key)).scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            new_setting = InstanceSettings()
            new_setting.key = key
            new_setting.value = value
            db.session.add(new_setting)
        saved[key] = value

    db.session.commit()
    return {"success": True, "data": saved}


@admin_bp.route("/settings", methods=["GET", "PUT"])
@require_auth
@admin_required
def manage_settings():
    """Manage global instance settings with category-based RBAC."""
    user = _get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    if request.method == "GET":
        res = _get_settings(user, request.args.get("category", "all"))
        return jsonify(res) if isinstance(res, dict) else res

    return jsonify(_put_settings(user, request.json or {}))


# --- FRBR ENTITY MANAGEMENT ROUTES ---


@admin_bp.route("/frbr/tree/manifestation/<int:manif_id>", methods=["GET"])
@require_auth
@admin_required
def get_frbr_tree(manif_id):
    """Fetches the full FRBR lineage upward from a Manifestation."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.READ_METADATA):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.READ_METADATA} required"}), 403

    manif = db.session.get(Manifestation, manif_id)
    if manif is None:
        return jsonify({"success": False, "error": "Manifestation not found"}), 404

    expr = db.session.get(Expression, manif.expression_id) if manif.expression_id else None
    work = db.session.get(Work, expr.work_id) if expr and expr.work_id else None

    items = db.session.execute(db.select(Item).filter_by(manifestation_id=manif.id).order_by(Item.id)).scalars().all()

    items_data = []
    for i in items:
        owner = db.session.get(AuthUser, i.owner_id) if i.owner_id else None
        owner_name = owner.display_name if owner and owner.display_name else (owner.email if owner else None)
        items_data.append(
            {
                "id": i.id,
                "status": i.status,
                "condition": i.condition,
                "meta": sanitize_meta(i.meta),
                "owner_id": i.owner_id,
                "owner_name": owner_name,
            }
        )

    return jsonify(
        {
            "success": True,
            "data": {
                "work": {"id": work.id, "title": work.title, "meta": sanitize_meta(work.meta)} if work else None,
                "expression": (
                    {
                        "id": expr.id,
                        "content_type": expr.content_type,
                        "language": expr.language,
                        "meta": sanitize_meta(expr.meta),
                        "work_id": expr.work_id,
                    }
                    if expr
                    else None
                ),
                "manifestation": {
                    "id": manif.id,
                    "expression_id": manif.expression_id,
                    "isbn13": manif.isbn13,
                    "upc": manif.upc,
                    "ean": manif.ean,
                    "publisher": manif.publisher,
                    "publication_date": str(manif.publication_date) if manif.publication_date else None,
                    "meta": sanitize_meta(manif.meta),
                },
                "items": items_data,
            },
        }
    )


@admin_bp.route("/frbr/work/<int:work_id>", methods=["PUT"])
@require_auth
@admin_required
def update_work(work_id):
    """Update a Work entity."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.WRITE_METADATA):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.WRITE_METADATA} required"}), 403

    data = request.json or {}
    try:
        work = frbr_service.update_work(work_id, title=data.get("title"), meta=parse_meta(data.get("meta")))
        return jsonify({"success": True, "data": {"id": work.id}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404


@admin_bp.route("/frbr/expression/<int:expr_id>", methods=["PUT"])
@require_auth
@admin_required
def update_expression(expr_id):
    """Update an Expression entity."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.WRITE_METADATA):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.WRITE_METADATA} required"}), 403

    data = request.json or {}
    try:
        expr = frbr_service.update_expression(
            expr_id,
            work_id=data.get("work_id"),
            content_type=data.get("content_type"),
            language=data.get("language"),
            meta=parse_meta(data.get("meta")),
        )
        return jsonify({"success": True, "data": {"id": expr.id}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404


@admin_bp.route("/frbr/manifestation/<int:manif_id>", methods=["PUT"])
@require_auth
@admin_required
def update_manifestation(manif_id):
    """Update a Manifestation entity."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.WRITE_METADATA):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.WRITE_METADATA} required"}), 403

    data = request.json or {}
    pub_date_str = data.get("publication_date")
    try:
        pub_date = date.fromisoformat(pub_date_str) if pub_date_str else None
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format. Use ISO format (YYYY-MM-DD)"}), 400

    try:
        manif = frbr_service.update_manifestation(
            manif_id,
            expression_id=data.get("expression_id"),
            isbn13=data.get("isbn13"),
            upc=data.get("upc"),
            ean=data.get("ean"),
            publisher=data.get("publisher"),
            publication_date=pub_date,
            meta=parse_meta(data.get("meta")),
        )
        return jsonify({"success": True, "data": {"id": manif.id}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404


@admin_bp.route("/frbr/item/<int:item_id>", methods=["PUT"])
@require_auth
@admin_required
def update_item(item_id):
    """Update an Item entity."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.WRITE_METADATA):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.WRITE_METADATA} required"}), 403

    data = request.json or {}
    try:
        item = frbr_service.update_item(
            item_id,
            manifestation_id=data.get("manifestation_id"),
            status=data.get("status"),
            condition=data.get("condition"),
            meta=parse_meta(data.get("meta")),
        )
        return jsonify({"success": True, "data": {"id": item.id}})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404


@admin_bp.route("/frbr/search", methods=["GET"])
@require_auth
@admin_required
def search_frbr_entities():
    """Search for FRBR entities (Works, Expressions, Manifestations) by title or identifier."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.READ_METADATA):
        return jsonify({"success": False, "error": f"Permission denied: {PermissionName.READ_METADATA} required"}), 403

    query = request.args.get("q", "").strip()
    entity_type = request.args.get("type", "manifestation")  # work, expression, manifestation
    limit = request.args.get("limit", 20, type=int)

    if not query:
        return jsonify({"success": True, "data": [], "meta": {"total": 0}})

    results = []

    if entity_type == "work":
        works = db.session.execute(db.select(Work).filter(Work.title.ilike(f"%{query}%")).limit(limit)).scalars().all()
        results = [{"id": w.id, "title": w.title, "type": "work"} for w in works]
    elif entity_type == "expression":
        # Join with Work to filter by title
        expressions = (
            db.session.execute(
                db.select(Expression)
                .join(Work, Expression.work_id == Work.id)
                .filter(db.or_(Work.title.ilike(f"%{query}%"), Expression.content_type.ilike(f"%{query}%")))
                .limit(limit)
            )
            .scalars()
            .all()
        )

        results = [
            {
                "id": e.id,
                "title": db.session.get(Work, e.work_id).title if e.work_id else f"Expression {e.id}",
                "content_type": e.content_type,
                "type": "expression",
            }
            for e in expressions
        ]
    else:  # manifestation
        # Search by ISBN/UPC/EAN OR by work title/author in meta
        work_filter = db.or_(
            Work.title.ilike(f"%{query}%"),
            db.or_(
                Work.meta["authors"].cast(db.String).ilike(f"%{query}%"),
                Work.meta["author"].cast(db.String).ilike(f"%{query}%"),
            ),
        )
        identifier_filter = db.or_(
            Manifestation.isbn13.ilike(f"%{query}%"),
            Manifestation.upc.ilike(f"%{query}%"),
            Manifestation.ean.ilike(f"%{query}%"),
        )

        # Get manifestations matching either criteria
        work_stmt = db.select(Work.id).filter(work_filter)
        expr_stmt = db.select(Expression.id).filter(Expression.work_id.in_(work_stmt))
        stmt = (
            db.select(Manifestation)
            .filter(
                db.or_(
                    identifier_filter,
                    Manifestation.expression_id.in_(expr_stmt),
                )
            )
            .limit(limit)
        )
        mans = db.session.execute(stmt).scalars().all()
        results = []
        for m in mans:
            expr = db.session.get(Expression, m.expression_id) if m.expression_id else None
            work = db.session.get(Work, expr.work_id) if expr and expr.work_id else None
            title = work.title if work else f"Manifestation {m.id}"
            results.append({"id": m.id, "title": title, "isbn13": m.isbn13, "upc": m.upc, "ean": m.ean, "type": "manifestation"})

    return jsonify({"success": True, "data": results, "meta": {"total": len(results), "query": query, "type": entity_type}})


@admin_bp.route("/media/upload-cover", methods=["POST"])
@require_auth
@admin_required
def upload_cover():
    """Accepts a client-side processed image blob, saves it, and binds it to an entity."""
    user = _get_current_user()

    if not _has_permission(user, PermissionName.EDIT_COVER) and not _has_permission(user, PermissionName.UPLOAD_COVER):
        return jsonify({"success": False, "error": "Permission denied"}), 403

    file = request.files.get("file")
    entity_type = request.form.get("entity_type")
    entity_id = request.form.get("entity_id")

    if not file or not file.filename or entity_type not in ["manifestation", "item"] or not str(entity_id).isdigit():
        return jsonify({"success": False, "error": "Invalid request parameters"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"{entity_type}_{entity_id}_cover.{ext}"

    try:
        from app.utils.images import save_upload_image

        public_url = save_upload_image(file, subfolder="covers", filename=filename)
    except Exception as e:
        return jsonify({"success": False, "error": f"Image processing failed: {str(e)}"}), 500

    saved_filepath = None
    try:
        from app.utils.covers import COVERS_DIR

        saved_filepath = os.path.join(COVERS_DIR, filename)
        entity = db.session.get(Manifestation, int(entity_id)) if entity_type == "manifestation" else db.session.get(Item, int(entity_id))

        if not entity:
            return jsonify({"success": False, "error": "Entity not found"}), 404

        if hasattr(entity, "cover_url"):
            entity.cover_url = public_url

        new_meta = dict(entity.meta or {})
        new_meta["cover_url"] = public_url
        entity.meta = new_meta

        db.session.commit()
        return jsonify({"success": True, "data": {"cover_url": public_url}})
    except Exception as e:
        db.session.rollback()
        if saved_filepath:
            try:
                os.remove(saved_filepath)
            except OSError:
                pass
        return jsonify({"success": False, "error": f"Database binding failed: {str(e)}"}), 500
