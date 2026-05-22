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

from flask import Response, current_app, g, jsonify, request
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import optional_auth, require_auth, require_permission
from app.api.filters import apply_genre_filter
from app.api.manifestations import lookup_isbn
from app.api.schemas import ItemBulkCreateSchema, ItemCreateSchema, ItemManualCreateSchema, ItemUpdateSchema
from app.core.permissions import PermissionName
from app.db.models import Expression, Item, ItemStatusLog, ItemTag, Manifestation, Tag, User, UserCollection, UserCollectionItem, Work, db


def sync_tags(item_id: int, user_id, tags: list[str] | None):
    if tags is None:
        return
    existing_links = db.session.query(ItemTag).filter(ItemTag.item_id == item_id).all()
    existing_tag_ids = {link.tag_id: link for link in existing_links}
    desired_tag_names = {t.strip() for t in tags if t.strip()}

    db_tags = []
    for name in desired_tag_names:
        tag = db.session.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.flush()
        db_tags.append(tag)

    desired_tag_ids = {t.id for t in db_tags}

    for tag_id, link in existing_tag_ids.items():
        if tag_id not in desired_tag_ids:
            db.session.delete(link)

    for tag in db_tags:
        if tag.id not in existing_tag_ids:
            link = ItemTag(item_id=item_id, tag_id=tag.id, added_by_id=user_id)
            db.session.add(link)


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
    borrowed_only = request.args.get("borrowed", "false").lower() == "true"
    missing_cover = request.args.get("missing_cover", "false").lower() == "true"
    missing_id = request.args.get("missing_id", "false").lower() == "true"
    tags_filter = request.args.get("tags", None)
    collections_filter = request.args.get("collections", None)
    genres_filter = request.args.get("genres", None)
    publishers_filter = request.args.get("publishers", None)

    tags_list = [t.strip() for t in tags_filter.split(",") if t.strip()] if tags_filter else None
    collections_list = [c.strip() for c in collections_filter.split(",") if c.strip()] if collections_filter else None
    genres_list = [gen.strip() for gen in genres_filter.split(",") if gen.strip()] if genres_filter else None
    publishers_list = [p.strip() for p in publishers_filter.split(",") if p.strip()] if publishers_filter else None

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    # Hard cap the limit to prevent users/bots from requesting the entire DB at once
    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    offset = (page - 1) * limit

    if q:
        from app.core.search_service import SearchService

        statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()] if statuses_filter else None
        total, results = SearchService.search_items(
            q,
            user_id,
            limit,
            offset,
            statuses=statuses_list,
            category=category_filter,
            format_filter=format_filter,
            borrowed_only=borrowed_only,
            missing_cover=missing_cover,
            missing_id=missing_id,
            tags=tags_list,
            collections=collections_list,
            genres=genres_list,
            publishers=publishers_list,
        )

        items_data = []
        for row in results:
            items_data.append(
                {
                    "id": row["item_id"],
                    "owner_id": str(row["owner_id"]) if row["owner_id"] else None,
                    "status": row["status"],
                    "collection_status": row["collection_status"],
                    "lent_to_user_id": row.get("lent_to_user_id"),
                    "lent_to_name": row.get("lent_to_name"),
                    "manifestation_id": row["manifestation_id"],
                    "isbn": row.get("isbn13") or row.get("isbn"),
                    "title": row["title"],
                    "cover_url": row["cover_url"],
                    "cover_status": (row.get("manifestation_meta") or {}).get("cover_status"),
                    "authors": (row.get("work_meta") or {}).get("authors", []),
                    "content_type": row.get("content_type"),
                    "is_owner": str(row["owner_id"]) == str(g.user_id) if hasattr(g, "user_id") else False,
                    "is_borrowed": str(row["owner_id"]) != str(g.user_id) if hasattr(g, "user_id") else False,
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
                "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + limit) < total},
                "error": None,
            }
        )

    # Standard sorting and querying
    query = Item.query.options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))

    if borrowed_only:
        query = query.filter(Item.lent_to_user_id == user_id)
    else:
        query = query.filter(db.or_(Item.owner_id == user_id, Item.lent_to_user_id == user_id))

    needs_mfn_join = bool(category_filter or format_filter or missing_cover or missing_id)
    needs_work_join = bool(genres_list or publishers_list or sort_by in ("title", "title-desc", "author"))
    if needs_mfn_join or needs_work_join:
        # We need to join these models if we have filters or specific sorting
        query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
        query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
        query = query.outerjoin(Work, Expression.work_id == Work.id)

    if category_filter:
        query = query.filter(Expression.content_type == category_filter)

    if format_filter:
        query = query.filter(Manifestation.meta["format"].as_string() == format_filter)

    if missing_cover:
        query = query.filter(
            db.and_(
                db.or_(Manifestation.cover_url.is_(None), Manifestation.cover_url == ""),
                db.or_(
                    Manifestation.meta["cover_url"].as_string().is_(None),
                    Manifestation.meta["cover_url"].as_string() == "",
                ),
            )
        )
    if missing_id:
        query = query.filter(
            db.and_(
                db.or_(Manifestation.isbn13.is_(None), Manifestation.isbn13 == ""),
                db.or_(Manifestation.upc.is_(None), Manifestation.upc == ""),
                db.or_(Manifestation.ean.is_(None), Manifestation.ean == ""),
                db.or_(
                    Manifestation.meta["barcode"].as_string().is_(None),
                    Manifestation.meta["barcode"].as_string() == "",
                ),
                db.or_(
                    Manifestation.meta["catalog_number"].as_string().is_(None),
                    Manifestation.meta["catalog_number"].as_string() == "",
                ),
            )
        )

    # Apply taxonomy filters
    if tags_list:
        query = query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
        tags_conditions = [Tag.name.ilike(t.strip()) for t in tags_list]
        query = query.filter(db.or_(*tags_conditions))

    if collections_list:
        query = query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
            UserCollection, UserCollectionItem.collection_id == UserCollection.id
        )
        coll_conditions = [UserCollection.name.ilike(c.strip()) for c in collections_list]
        query = query.filter(db.or_(*coll_conditions), UserCollection.owner_id == user_id)

    if genres_list:
        query = apply_genre_filter(query, genres_list)

    if publishers_list:
        pubs_conditions = [Manifestation.publisher.ilike(f"%{p.strip()}%") for p in publishers_list]
        query = query.filter(db.or_(*pubs_conditions))

    if statuses_filter:
        statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()]
        if "lent" in statuses_list and not borrowed_only:
            # If 'lent' is selected specifically, they want items THEY lent out.
            # So we exclude items they borrowed (which also have collection_status='lent').
            query = query.filter(
                db.or_(
                    Item.status.in_([s for s in statuses_list if s != "lent"]),
                    db.and_(Item.collection_status == "lent", Item.owner_id == user_id),
                    Item.collection_status.in_([s for s in statuses_list if s != "lent"]),
                )
            )
        else:
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

        is_owner = str(item.owner_id) == str(g.user_id) if hasattr(g, "user_id") else False
        items_data.append(
            {
                "id": item.id,
                "owner_id": item.owner_id,
                "status": item.status,
                "collection_status": item.collection_status,
                "lent_to_user_id": item.lent_to_user_id,
                "lent_to_name": item.lent_to_name,
                "manifestation_id": item.manifestation_id,
                "isbn": manifestation.isbn13 if manifestation else None,
                "title": work_title,
                "cover_url": manifestation.cover_url
                or (manifestation.meta.get("cover_url") if manifestation and manifestation.meta else None),
                "cover_status": manifestation.meta.get("cover_status") if manifestation and manifestation.meta else None,
                "authors": authors,
                "content_type": manifestation.expression.content_type if manifestation and manifestation.expression else None,
                "is_owner": is_owner,
                "is_borrowed": not is_owner,
                "tags": [link.tag.name for link in getattr(item, "tag_links", [])],
                "added_at": item.added_at.isoformat() if item.added_at else None,
                "updated_at": (item.updated_at or item.added_at).isoformat() if (item.updated_at or item.added_at) else None,
            }
        )

    return jsonify(
        {
            "success": True,
            "data": items_data,
            "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
            "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + limit) < total},
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
    is_borrowed = user_id and str(item.lent_to_user_id) == str(user_id)
    is_admin = False
    has_read_owners = False

    if item.is_hidden and not (is_owner or is_borrowed):
        # We check admin/read_owners later, but first pass: if hidden, you must have a reason to see it
        pass

    if user_id:
        user = db.session.get(User, user_id)
        if user and any(role.name == "admin" for role in getattr(user, "roles", [])):
            is_admin = True
        if user:
            has_read_owners = user.has_permission(PermissionName.READ_OWNERS)

    if item.is_hidden and not (is_owner or is_admin or is_borrowed or has_read_owners):
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    manifestation = item.manifestation
    owner_count = (
        db.session.query(db.func.count(Item.id)).filter(Item.manifestation_id == item.manifestation_id, Item.is_hidden.is_(False)).scalar()
        or 0
    )

    item_data = {
        "id": item.id,
        "owner_id": str(item.owner_id) if (is_owner or is_admin or is_borrowed) else "Unavailable",
        "is_owner": is_owner,
        "is_borrowed": is_borrowed,
        "owner_name": None,
        "owner_count": owner_count,
        "status": item.status,
        "collection_status": item.collection_status,
        "is_hidden": item.is_hidden,
        "manifestation_id": item.manifestation_id,
        "tags": [link.tag.name for link in getattr(item, "tag_links", [])],
        "meta": item.meta,
    }

    if is_owner or is_admin or is_borrowed:
        item_data["lent_to_user_id"] = item.lent_to_user_id
        item_data["lent_to_name"] = item.lent_to_name

    if is_owner or is_admin or has_read_owners or is_borrowed:
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
                container_work_id = work.member_of[0].container_work_id if work.member_of else None
                item_data["work"] = {
                    "id": work.id,
                    "title": work.title,
                    "authors": work.meta.get("authors", []) if work.meta else [],
                    "meta": work.meta,
                    "container_work_id": container_work_id,
                }

    return jsonify({"success": True, "data": item_data, "error": None})


@api_bp.route("/items/<int:item_id>", methods=["PUT"])
@require_auth
def update_item(item_id: int):
    item = db.session.get(Item, item_id)
    user_id = getattr(g, "user_id", None)
    user = db.session.get(User, user_id) if user_id else None

    is_owner = (str(item.owner_id) == str(user_id)) if item and user_id else False
    is_admin = any(role.name == "admin" for role in getattr(user, "roles", [])) if user else False
    has_update_permission = user.has_permission(PermissionName.UPDATE_ITEM) if user else False

    if not item or not (is_owner or is_admin or has_update_permission):
        error, code = ("Item not found", 404) if not item else ("Forbidden", 403)
        return jsonify({"success": False, "data": None, "error": error}), code

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    try:
        payload = ItemUpdateSchema(**data)
    except ValidationError as e:
        return jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    if payload.status and payload.status != item.status:
        old_status = item.status
        item.status = payload.status
        log = ItemStatusLog(item_id=item.id, user_id=user_id, old_status=old_status, new_status=item.status)
        db.session.add(log)

    if payload.collection_status and payload.collection_status != item.collection_status:
        old_c_status = item.collection_status
        item.collection_status = payload.collection_status
        log = ItemStatusLog(item_id=item.id, user_id=user_id, old_status=old_c_status, new_status=item.collection_status)
        db.session.add(log)

    if payload.lent_to_user_id is not None:
        item.lent_to_user_id = payload.lent_to_user_id
    if payload.lent_to_name is not None:
        item.lent_to_name = payload.lent_to_name
    if payload.is_hidden is not None:
        item.is_hidden = payload.is_hidden

    # Optional metadata update from extra fields or meta field
    metadata = payload.model_extra or {}
    if isinstance(payload.meta, dict):
        metadata.update(payload.meta)

    # BOLA protection: block sensitive fields
    forbidden = {"owner_id", "id", "created_at"}
    if any(k in metadata for k in forbidden):
        return jsonify({"success": False, "error": "Invalid payload: forbidden fields"}), 400

    if metadata:
        if item.manifestation:
            item.manifestation.update_meta(**metadata)
        # Also update item.meta if needed, but usually extra fields are for manifestation
        item.meta = {**item.meta, **metadata} if item.meta else metadata

    sync_tags(item.id, user_id, payload.tags)

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
def get_items_by_isbn(isbn: str) -> Response | tuple[Response, int]:
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    if not manifestation:
        return jsonify({"error": f"Manifestation not found for ISBN = {isbn}"}), 404

    items = Item.query.filter_by(manifestation_id=manifestation.id).filter(Item.is_hidden.is_(False)).all()
    if not items:
        return jsonify({"error": f"No items found for ISBN = {isbn}"}), 404

    return jsonify({"ids": [item.id for item in items]})


@api_bp.route("/item/<isbn>", methods=["POST"])
@require_auth
@require_permission(PermissionName.WRITE_ITEM)
def add_item(isbn: str) -> Response | tuple[Response, int]:
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

    payload_json = request.get_json(silent=True)
    if not isinstance(payload_json, dict):
        if payload_json is None and not request.data:
            payload_json = {}
        else:
            return invalid_json_payload_response()

    try:
        payload = ItemCreateSchema(**payload_json)
    except (ValidationError, TypeError) as e:
        return jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    metadata = payload.model_extra or {}
    if isinstance(payload.meta, dict):
        metadata.update(payload.meta)

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

    item = Item(
        manifestation_id=manifestation.id,
        owner_id=user_id,
        status=payload.status or "want_to_read",
        collection_status=payload.collection_status,
        meta={},
    )
    db.session.add(item)
    try:
        db.session.flush()
        sync_tags(item.id, user_id, payload.tags)
        db.session.commit()
        return jsonify({"success": True, "data": {"item_id": item.id, "manifestation_id": manifestation.id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        current_app.logger.exception("Failed to add item for ISBN %s for user %s: %s", isbn, user_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to create item"}), 500


@api_bp.route("/manifestations/<int:manifestation_id>/add", methods=["POST"])
@require_auth
@require_permission(PermissionName.WRITE_ITEM)
def add_item_by_manifestation(manifestation_id: int) -> Response | tuple[Response, int]:
    """Add a new item to the user collection by manifestation ID (no ISBN required)."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    manifestation = db.session.get(Manifestation, manifestation_id)
    if not manifestation:
        return jsonify({"success": False, "data": None, "error": "Manifestation not found"}), 404

    payload_json = request.get_json(silent=True)
    if not isinstance(payload_json, dict):
        if payload_json is None and not request.data:
            payload_json = {}
        else:
            return invalid_json_payload_response()

    try:
        payload = ItemCreateSchema(**payload_json)
    except (ValidationError, TypeError) as e:
        return jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    item = Item(
        manifestation_id=manifestation.id,
        owner_id=user_id,
        status=payload.status or "want_to_read",
        collection_status=payload.collection_status,
        meta={},
    )
    db.session.add(item)
    db.session.flush()
    if payload.collection_id:
        link = UserCollectionItem(collection_id=payload.collection_id, item_id=item.id)
        db.session.add(link)
    sync_tags(item.id, user_id, payload.tags)
    db.session.commit()

    return jsonify({"success": True, "data": {"item_id": item.id, "manifestation_id": manifestation.id}, "error": None})


@api_bp.route("/items/bulk", methods=["POST"])
@require_auth
def add_items_bulk() -> Response | tuple[Response, int]:
    """Bulk add multiple manifestations to user's collection."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    payload_json = request.get_json(silent=True)
    if not isinstance(payload_json, dict):
        return invalid_json_payload_response()

    try:
        payload = ItemBulkCreateSchema(**payload_json)
    except ValidationError as e:
        return jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    manifestations = Manifestation.query.filter(Manifestation.id.in_(payload.manifestation_ids)).all()
    if not manifestations:
        return jsonify({"success": False, "data": None, "error": "No valid manifestations found"}), 404

    created_items = []
    for man in manifestations:
        status = payload.status
        if not status:
            content_type = man.expression.content_type if man.expression else "text"
            from app.core.taxonomy import CATEGORY_PROGRESS_STATUSES, FORMAT_ALIAS_TO_CATEGORY, MediaCategory

            _fmt_lower = (content_type or "").lower()
            category = _fmt_lower if _fmt_lower in MediaCategory.ALL else FORMAT_ALIAS_TO_CATEGORY.get(_fmt_lower, MediaCategory.TEXT)
            status = CATEGORY_PROGRESS_STATUSES.get(category, ("want_to_read",))[0]

        item = Item(
            manifestation_id=man.id,
            owner_id=user_id,
            status=status,
            collection_status=payload.collection_status,
            is_hidden=payload.is_hidden or False,
            meta={},
        )
        db.session.add(item)
        created_items.append(item)

    try:
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "data": {"item_ids": [i.id for i in created_items], "manifestation_ids": [m.id for m in manifestations]},
                "error": None,
            }
        )
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        current_app.logger.exception("Failed to bulk add items for user %s: %s", user_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to create items"}), 500


@api_bp.route("/items/manual", methods=["POST"])
@require_auth
@require_permission(PermissionName.WRITE_ITEM)
def add_item_manual() -> Response | tuple[Response, int]:
    """Add a new item manually when ISBN is not available. Expects JSON with Title, Authors, Format."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"success": False, "data": None, "error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    try:
        payload = ItemManualCreateSchema(**data)
    except (ValidationError, TypeError) as e:
        return jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    title = payload.Title
    authors = payload.Authors
    if isinstance(authors, str):
        authors = [authors]
    content_type = payload.Format
    isbn = payload.ISBN
    pub_date_str = payload.PublicationDate

    # Derive a sensible default progress status from the media format using canonical mapping.
    from app.core.taxonomy import CATEGORY_PROGRESS_STATUSES, MediaCategory

    _fmt_lower = (content_type or "").lower()
    if _fmt_lower in MediaCategory.ALL:
        category = _fmt_lower
    else:
        from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY

        category = FORMAT_ALIAS_TO_CATEGORY.get(_fmt_lower, MediaCategory.TEXT)

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
            work = Work(title=title, meta={"authors": authors, "description": payload.Description})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type=content_type, language="en", meta={})
            db.session.add(expression)
            db.session.flush()

            # Store all extra fields in meta
            manifestation = Manifestation(expression_id=expression.id, meta=payload.model_dump())
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
            status=payload.status or default_status,
            collection_status=payload.collection_status,
            meta={},
        )
        db.session.add(item)
        db.session.flush()
        sync_tags(item.id, user_id, payload.tags)
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


@api_bp.route("/items/<int:item_id>/visibility", methods=["PATCH"])
@require_auth
def toggle_item_visibility(item_id: int):
    """
    Toggles the is_hidden flag for a specific item.
    Hidden items do not appear on the user's public profile or shared collections.
    """
    item = db.session.get(Item, item_id)
    user_id = getattr(g, "user_id", None)

    if not item or str(item.owner_id) != str(user_id):
        # Return 404 even if forbidden to prevent data leakage (BOLA protection)
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    data = request.get_json() or {}
    if "is_hidden" not in data:
        return jsonify({"error": "Missing 'is_hidden' boolean field.", "code": 400}), 400

    new_val = data["is_hidden"]
    if not isinstance(new_val, bool):
        return jsonify({"error": "Field 'is_hidden' must be a boolean.", "code": 400}), 400

    item.is_hidden = new_val
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"Item visibility updated to {'hidden' if item.is_hidden else 'public'}.",
            "is_hidden": item.is_hidden,
        }
    )
