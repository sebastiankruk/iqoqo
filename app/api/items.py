"""(Handles User Collections)"""

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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from flask import current_app, g, jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import optional_auth, require_auth, require_permission
from app.api.manifestations import lookup_isbn
from app.core.permissions import PermissionName
from app.db.models import Expression, Item, ItemStatusLog, Manifestation, User, Work, db


@api_bp.route("/items", methods=["GET"])
@require_auth
def get_items():
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return (
            jsonify({"success": False, "data": [], "meta": {"page": 1, "limit": 20, "total": 0, "pages": 0}, "error": "Unauthorized"}),
            401,
        )

    page_param = request.args.get("page", "1")
    limit_param = request.args.get("limit", "20")
    statuses_filter = request.args.get("statuses", None)
    category_filter = request.args.get("category", None)
    format_filter = request.args.get("format", None)
    q = request.args.get("q", request.args.get("search", "")).strip()
    sort_by = request.args.get("sort", "updated")

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    if page < 1 or limit < 1:
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    offset = (page - 1) * limit

    if q:
        from app.core.search_service import SearchService

        statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()] if statuses_filter else None
        total, results = SearchService.search_items(
            q, user_id, limit, offset, statuses=statuses_list, category=category_filter, format_filter=format_filter
        )

        items_data = []
        for row in results:
            items_data.append(
                {
                    "id": row["item_id"],
                    "owner_id": str(row["owner_id"]) if row["owner_id"] else None,
                    "status": row["status"],
                    "collection_status": row["collection_status"],
                    "manifestation_id": row["manifestation_id"],
                    "isbn": row.get("isbn13") or row.get("isbn"),
                    "title": row["title"],
                    "cover_url": row["cover_url"],
                    "cover_status": (row.get("manifestation_meta") or {}).get("cover_status"),
                    "authors": (row.get("work_meta") or {}).get("authors", []),
                    "content_type": row.get("content_type"),
                    "added_at": row["added_at"].isoformat() if hasattr(row["added_at"], "isoformat") else row["added_at"],
                    "updated_at": (
                        (row.get("updated_at") or row["added_at"]).isoformat()
                        if hasattr((row.get("updated_at") or row["added_at"]), "isoformat")
                        else (row.get("updated_at") or row["added_at"])
                    ),
                }
            )

        return jsonify(
            {
                "success": True,
                "data": items_data,
                "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
                "error": None,
            }
        )

    # Standard sorting and querying
    query = Item.query.options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
    query = query.filter(Item.owner_id == user_id)

    if category_filter or format_filter or sort_by in ("title", "title-desc", "author"):
        # We need to join these models if we have filters or specific sorting
        query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
        query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
        query = query.outerjoin(Work, Expression.work_id == Work.id)

    if category_filter:
        query = query.filter(Expression.content_type == category_filter)

    if format_filter:
        query = query.filter(Manifestation.meta["format"].as_string() == format_filter)

    if statuses_filter:
        statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()]
        query = query.filter(db.or_(Item.status.in_(statuses_list), Item.collection_status.in_(statuses_list)))

    if sort_by == "title":
        query = query.order_by(Work.title.asc().nulls_last())
    elif sort_by == "title-desc":
        query = query.order_by(Work.title.desc().nulls_last())
    elif sort_by == "author":
        query = query.order_by(db.cast(Work.meta["authors"], db.String).asc().nulls_last())
    elif sort_by == "added":
        query = query.order_by(Item.added_at.desc().nulls_last())
    else:
        # Default sort fallback to recency
        query = query.order_by(func.coalesce(Item.updated_at, Item.added_at).desc())

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    items_data = []
    for item in items:
        manifestation = item.manifestation
        work_title = ""
        authors = []
        if manifestation and manifestation.expression and manifestation.expression.work:
            work = manifestation.expression.work
            work_title = work.title or ""
            authors = work.meta.get("authors", []) if work.meta else []

        items_data.append(
            {
                "id": item.id,
                "owner_id": item.owner_id,
                "status": item.status,
                "collection_status": item.collection_status,
                "manifestation_id": item.manifestation_id,
                "isbn": manifestation.isbn13 if manifestation else None,
                "title": work_title,
                "cover_url": manifestation.cover_url
                or (manifestation.meta.get("cover_url") if manifestation and manifestation.meta else None),
                "cover_status": manifestation.meta.get("cover_status") if manifestation and manifestation.meta else None,
                "authors": authors,
                "content_type": manifestation.expression.content_type if manifestation and manifestation.expression else None,
                "is_owner": str(item.owner_id) == str(g.user_id) if hasattr(g, "user_id") else False,
                "added_at": item.added_at.isoformat() if item.added_at else None,
                "updated_at": (item.updated_at or item.added_at).isoformat() if (item.updated_at or item.added_at) else None,
            }
        )

    return jsonify(
        {
            "success": True,
            "data": items_data,
            "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
            "error": None,
        }
    )


@api_bp.route("/items/<int:item_id>", methods=["GET"])
@optional_auth
def get_item_detail(item_id: int):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    user_id = getattr(g, "user_id", None)
    is_owner = (str(item.owner_id) == str(user_id)) if user_id else False
    is_admin = False
    has_read_owners = False

    if user_id:
        user = db.session.get(User, user_id)
        if user and any(role.name == "admin" for role in getattr(user, "roles", [])):
            is_admin = True
        if user:
            has_read_owners = user.has_permission(PermissionName.READ_OWNERS)

    manifestation = item.manifestation
    owner_count = db.session.query(db.func.count(Item.id)).filter(Item.manifestation_id == item.manifestation_id).scalar() or 0

    item_data = {
        "id": item.id,
        "owner_id": str(item.owner_id) if (is_owner or is_admin) else "Unavailable",
        "is_owner": is_owner,
        "owner_name": None,
        "owner_count": owner_count,
        "status": item.status,
        "collection_status": item.collection_status,
        "manifestation_id": item.manifestation_id,
        "meta": item.meta,
    }

    if is_owner or is_admin or has_read_owners:
        owner = db.session.get(User, item.owner_id)
        if owner:
            item_data["owner_name"] = owner.display_name or owner.email

    if manifestation:
        item_data["isbn"] = manifestation.isbn13
        item_data["manifestation_meta"] = manifestation.meta
        item_data["cover_url"] = manifestation.cover_url or (manifestation.meta.get("cover_url") if manifestation.meta else None)
        item_data["cover_status"] = manifestation.meta.get("cover_status") if manifestation.meta else None

        if manifestation.expression:
            expression = manifestation.expression
            item_data["expression"] = {
                "id": expression.id,
                "content_type": expression.content_type,
                "language": expression.language,
            }

            if expression.work:
                work = expression.work
                item_data["work"] = {
                    "id": work.id,
                    "title": work.title,
                    "authors": work.meta.get("authors", []) if work.meta else [],
                    "meta": work.meta,
                }

    return jsonify({"success": True, "data": item_data, "error": None})


@api_bp.route("/items/<int:item_id>", methods=["PUT"])
@require_auth
def update_item(item_id: int):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    user_id = getattr(g, "user_id", None)
    is_owner = (str(item.owner_id) == str(user_id)) if user_id else False
    is_admin = False

    user = db.session.get(User, user_id)
    if user and any(role.name == "admin" for role in getattr(user, "roles", [])):
        is_admin = True

    has_update_permission = user.has_permission(PermissionName.UPDATE_ITEM) if user else False

    if not (is_owner or is_admin or has_update_permission):
        return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    if data.get("status") and data["status"] != item.status:
        old_status = item.status
        item.status = data["status"]
        log = ItemStatusLog(item_id=item.id, user_id=user_id, old_status=old_status, new_status=item.status)
        db.session.add(log)

    if data.get("collection_status") and data["collection_status"] != item.collection_status:
        # We also log collection status changes in the same log for now,
        # but we could add a flag if needed.
        old_c_status = item.collection_status
        item.collection_status = data["collection_status"]
        log = ItemStatusLog(item_id=item.id, user_id=user_id, old_status=old_c_status, new_status=item.collection_status)
        db.session.add(log)

    if data.get("meta"):
        item.meta = data["meta"]

    try:
        db.session.commit()
        return jsonify({"success": True, "data": {"id": item.id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        return jsonify({"success": False, "data": None, "error": str(e)}), 500


@api_bp.route("/items/<int:item_id>", methods=["DELETE"])
@require_auth
@require_permission(PermissionName.DELETE_ITEM)
def delete_item(item_id: int):
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    user_id = getattr(g, "user_id", None)
    is_owner = (str(item.owner_id) == str(user_id)) if user_id else False
    is_admin = False

    user = db.session.get(User, user_id)
    if user and any(role.name == "admin" for role in getattr(user, "roles", [])):
        is_admin = True

    if not (is_owner or is_admin):
        return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": item_id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        return jsonify({"success": False, "data": None, "error": str(e)}), 500


@api_bp.route("/item/<isbn>", methods=["GET"])
def get_items_by_isbn(isbn: str):
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    if not manifestation:
        return jsonify({"error": f"Manifestation not found for ISBN = {isbn}"}), 404

    items = Item.query.filter_by(manifestation_id=manifestation.id).all()
    if not items:
        return jsonify({"error": f"No items found for ISBN = {isbn}"}), 404

    return jsonify({"ids": [item.id for item in items]})


@api_bp.route("/item/<isbn>", methods=["POST"])
@require_auth
def add_item(isbn: str):
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    if not manifestation:
        lookup_response = lookup_isbn(isbn)
        if isinstance(lookup_response, tuple):
            status_code = lookup_response[1] if len(lookup_response) > 1 else 404
            if status_code != 200:
                return jsonify({"success": False, "data": None, "error": f"Manifestation not found for ISBN = {isbn}"}), 404
        manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    metadata = request.get_json(silent=True)
    if metadata:
        manifestation.update_meta(**metadata)
        if manifestation.expression and manifestation.expression.work:
            if "Title" in metadata:
                manifestation.expression.work.title = metadata["Title"]
            if "Authors" in metadata:
                if not manifestation.expression.work.meta:
                    manifestation.expression.work.meta = {}
                work_meta = dict(manifestation.expression.work.meta)
                work_meta["authors"] = metadata["Authors"]
                manifestation.expression.work.meta = work_meta

    item = Item(manifestation_id=manifestation.id, owner_id=user_id, status="want_to_read", collection_status="available", meta={})
    db.session.add(item)
    try:
        db.session.commit()
        return jsonify({"success": True, "data": {"item_id": item.id, "manifestation_id": manifestation.id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        current_app.logger.exception("Failed to add item for ISBN %s for user %s: %s", isbn, user_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to create item"}), 500


@api_bp.route("/manifestations/<int:manifestation_id>/add", methods=["POST"])
@require_auth
def add_item_by_manifestation(manifestation_id: int):
    """Add a new item to the user collection by manifestation ID (no ISBN required)."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    manifestation = db.session.get(Manifestation, manifestation_id)
    if not manifestation:
        return jsonify({"success": False, "data": None, "error": "Manifestation not found"}), 404

    item = Item(manifestation_id=manifestation.id, owner_id=user_id, status="want_to_read", collection_status="available", meta={})
    db.session.add(item)
    db.session.commit()

    return jsonify({"success": True, "data": {"item_id": item.id, "manifestation_id": manifestation.id}, "error": None})


@api_bp.route("/items/manual", methods=["POST"])
@require_auth
def add_item_manual():
    """Add a new item manually when ISBN is not available. Expects JSON with Title, Authors, Format."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    title = data.get("Title", "Unknown Title")
    authors = data.get("Authors", [])
    if isinstance(authors, str):
        authors = [authors]
    content_type = data.get("Format", "text")
    isbn = data.get("ISBN")
    pub_date_str = data.get("PublicationDate")

    # Derive a sensible default progress status from the media format using canonical mapping.
    from app.db.core import CATEGORY_PROGRESS_STATUSES, MediaCategory, MediaFormat

    _FORMAT_TO_CATEGORY: dict[str, str] = {
        MediaFormat.BOOK: MediaCategory.TEXT,
        MediaFormat.AUDIOBOOK_CD: MediaCategory.MUSIC,
        MediaFormat.CD: MediaCategory.MUSIC,
        MediaFormat.VINYL: MediaCategory.MUSIC,
        MediaFormat.SACD: MediaCategory.MUSIC,
        MediaFormat.MUSIC: MediaCategory.MUSIC,
        MediaFormat.DVD: MediaCategory.MOVIE,
        MediaFormat.BLURAY: MediaCategory.MOVIE,
        MediaFormat.MOVIE: MediaCategory.MOVIE,
        MediaFormat.BOARD_GAME: MediaCategory.BOARD_GAME,
        MediaFormat.PUZZLE: MediaCategory.PUZZLE,
    }
    _fmt_lower = (content_type or "").lower()
    category = _FORMAT_TO_CATEGORY.get(_fmt_lower, MediaCategory.TEXT)
    default_status = CATEGORY_PROGRESS_STATUSES[category][0]

    try:
        # --- Try to reuse an existing manifestation when ISBN clashes (retry scenario) ---
        existing_manifestation: Manifestation | None = None
        normalised_isbn: str | None = None
        if isbn:
            normalised_isbn = str(isbn).replace("-", "").replace(" ", "").strip()
            existing_manifestation = Manifestation.query.filter_by(isbn13=normalised_isbn).first()

        if existing_manifestation:
            # Manifestation already exists — just create a new Item linked to it
            manifestation = existing_manifestation
        else:
            work = Work(title=title, meta={"authors": authors, "description": data.get("Description")})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type=content_type, language="en", meta={})
            db.session.add(expression)
            db.session.flush()

            manifestation = Manifestation(expression_id=expression.id, meta=data)
            if normalised_isbn:
                manifestation.isbn13 = normalised_isbn
            if pub_date_str:
                from datetime import date

                try:
                    manifestation.publication_date = date.fromisoformat(pub_date_str)
                except (ValueError, TypeError):
                    pass
            db.session.add(manifestation)
            db.session.flush()

        item = Item(
            manifestation_id=manifestation.id,
            owner_id=user_id,
            status=default_status,
            collection_status="available",
            meta={},
        )
        db.session.add(item)
        db.session.commit()

        return jsonify({"success": True, "data": {"item_id": item.id, "manifestation_id": manifestation.id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        current_app.logger.exception("Failed to create manual item for user %s: %s", user_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to create item"}), 500


@api_bp.route("/items/<int:item_id>/logs", methods=["GET"])
@require_auth
def get_item_logs(item_id: int):
    """Get the status timeline for an item."""
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    is_owner = str(item.owner_id) == str(user_id)
    user = db.session.get(User, user_id)
    is_admin = user and any(role.name == "admin" for role in getattr(user, "roles", []))
    has_update_permission = user.has_permission(PermissionName.UPDATE_ITEM) if user else False

    if not (is_owner or is_admin or has_update_permission):
        return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

    logs = db.session.query(ItemStatusLog).filter(ItemStatusLog.item_id == item_id).order_by(ItemStatusLog.changed_at.desc()).all()
    return jsonify(
        {
            "success": True,
            "data": [
                {
                    "old_status": entry.old_status,
                    "new_status": entry.new_status,
                    "changed_at": entry.changed_at.isoformat(),
                }
                for entry in logs
            ],
            "error": None,
        }
    )
