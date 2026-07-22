# pylint: disable=too-many-lines

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

import logging
import uuid

from flask import Response, current_app, g, jsonify, request
from pydantic import ValidationError
from sqlalchemy.orm import selectinload

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import optional_auth, require_auth, require_permission, require_physical_item
from app.api.filters import apply_genre_filter, apply_statuses_filter, parse_csv_param
from app.api.manifestations import lookup_isbn
from app.api.schemas import ItemBulkCreateSchema, ItemCollectionLinkSchema, ItemCreateSchema, ItemManualCreateSchema, ItemUpdateSchema
from app.core.item_access import require_item_access, verify_item_ownership
from app.core.limiter import limiter
from app.core.permissions import PermissionName
from app.db.models import (
    Expression,
    Item,
    ItemStatusLog,
    ItemTag,
    Manifestation,
    Tag,
    User,
    UserCollection,
    UserCollectionItem,
    UserWorkIntent,
    Work,
    db,
)

logger = logging.getLogger(__name__)


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


def log_initial_item_status(item_id: int, user_id: uuid.UUID, status: str, collection_status: str | None = None) -> None:
    """Helper to log initial item status and collection status when item is added."""
    progress_log = ItemStatusLog(item_id=item_id, user_id=user_id, old_status=None, new_status=status)
    db.session.add(progress_log)
    if collection_status:
        collection_log = ItemStatusLog(item_id=item_id, user_id=user_id, old_status=None, new_status=collection_status)
        db.session.add(collection_log)


def get_virtual_items(
    user_id, statuses_filter, category_list, format_list, q, publishers_list, missing_cover, missing_id, genres_list=None
):
    virtual_items = []

    is_wish_list_requested = True
    if statuses_filter:
        statuses_list = parse_csv_param(statuses_filter) or []
        is_wish_list_requested = any(
            s in statuses_list for s in ("wish_list", "want_to_read", "want_to_listen", "want_to_watch", "want_to_play")
        )

    if not is_wish_list_requested:
        return []

    # "wish_list" is a collection_status concept, not a UserWorkIntent.status value.
    # UserWorkIntent.status stores progress values like "want_to_read", "want_to_listen", etc.
    # When the frontend filters by statuses=wish_list, we must include all non-fulfilled intents
    # (because every intent IS a wishlist item).  Only narrow by actual intent-level statuses
    # (want_to_read, want_to_listen, …) when those are explicitly present in the filter.
    _INTENT_LEVEL_STATUSES = {"want_to_read", "want_to_listen", "want_to_watch", "want_to_play"}

    intent_query = db.session.query(UserWorkIntent).join(Work, UserWorkIntent.work_id == Work.id)
    if statuses_filter:
        statuses_list = parse_csv_param(statuses_filter) or []
        intent_statuses = [s for s in statuses_list if s in _INTENT_LEVEL_STATUSES]
        if intent_statuses:
            # Filter to specific intent progress statuses (e.g. "want_to_read")
            intent_query = intent_query.filter(UserWorkIntent.status.in_(intent_statuses))
        else:
            # "wish_list" (or other non-intent status) → include all non-fulfilled intents
            intent_query = intent_query.filter(UserWorkIntent.status != "fulfilled")
    else:
        intent_query = intent_query.filter(UserWorkIntent.status != "fulfilled")

    if genres_list:
        intent_query = apply_genre_filter(intent_query, genres_list)

    if q:
        pattern = f"%{q.strip().lower()}%"
        intent_query = intent_query.filter(db.or_(Work.title.ilike(pattern), db.cast(Work.meta["authors"], db.String).ilike(pattern)))

    if category_list or format_list or publishers_list or missing_cover or missing_id:
        intent_query = intent_query.outerjoin(Expression, Expression.work_id == Work.id).outerjoin(
            Manifestation, Manifestation.expression_id == Expression.id
        )
        if category_list:
            intent_query = intent_query.filter(db.or_(Expression.content_type.in_(category_list), Expression.content_type.is_(None)))
        if format_list:
            intent_query = intent_query.filter(Manifestation.meta["format"].as_string().in_(format_list))
        if publishers_list:
            pubs_conditions = []
            for p in publishers_list:
                p_term = f"%{p.strip()}%"
                pubs_conditions.append(
                    db.or_(
                        Manifestation.publisher.ilike(p_term),
                        Manifestation.meta["Publisher"].as_string().ilike(p_term),
                        Manifestation.meta["publisher"].as_string().ilike(p_term),
                        db.and_(Expression.content_type == "music", Manifestation.meta["label"].as_string().ilike(p_term)),
                    )
                )
            intent_query = intent_query.filter(db.or_(*pubs_conditions))
        if missing_cover:
            intent_query = intent_query.filter(
                db.and_(
                    db.or_(Manifestation.cover_url.is_(None), Manifestation.cover_url == ""),
                    db.or_(
                        Manifestation.meta["cover_url"].as_string().is_(None),
                        Manifestation.meta["cover_url"].as_string() == "",
                    ),
                )
            )
        if missing_id:
            intent_query = intent_query.filter(
                db.and_(
                    db.or_(Manifestation.isbn13.is_(None), Manifestation.isbn13 == ""),
                    db.or_(Manifestation.upc.is_(None), Manifestation.upc == ""),
                    db.or_(Manifestation.ean.is_(None), Manifestation.ean == ""),
                    db.or_(
                        Manifestation.meta["barcode"].as_string().is_(None),
                        Manifestation.meta["barcode"].as_string() == "",
                    ),
                )
            )

    intents = intent_query.filter(UserWorkIntent.user_id == user_id).all()

    for intent in intents:
        work = intent.work
        manifestation = None
        for expr in work.expressions:
            if category_list and expr.content_type not in category_list:
                continue
            if expr.manifestations:
                manifestation = expr.manifestations[0]
                break

        if not manifestation:
            # Build virtual item from Work-level data only (B8 fix)
            virtual_items.append(
                {
                    "is_virtual": True,
                    "id": -intent.id,
                    "owner_id": str(user_id) if user_id else None,
                    "status": intent.status,
                    "collection_status": "wish_list",
                    "lent_to_user_id": None,
                    "lent_to_name": None,
                    "manifestation_id": None,
                    "isbn": None,
                    "title": work.title,
                    "publisher": None,
                    "cover_url": None,
                    "cover_status": None,
                    "authors": work.meta.get("authors", []) if work.meta else [],
                    "content_type": None,
                    "is_owner": True,
                    "is_borrowed": False,
                    "is_hidden": intent.is_hidden,
                    "tags": [],
                    "added_at": intent.created_at.isoformat() if hasattr(intent.created_at, "isoformat") else intent.created_at,
                    "updated_at": (
                        (intent.updated_at or intent.created_at).isoformat()
                        if hasattr((intent.updated_at or intent.created_at), "isoformat")
                        else (intent.updated_at or intent.created_at)
                    ),
                }
            )
            continue

        virtual_items.append(
            {
                "is_virtual": True,
                "id": -intent.id,
                "owner_id": str(user_id) if user_id else None,
                "status": intent.status,
                "collection_status": "wish_list",
                "lent_to_user_id": None,
                "lent_to_name": None,
                "manifestation_id": manifestation.id,
                "isbn": manifestation.isbn13,
                "title": work.title,
                "publisher": manifestation.publisher if manifestation else None,
                "cover_url": manifestation.cover_url or (manifestation.meta.get("cover_url") if manifestation.meta else None),
                "cover_status": manifestation.meta.get("cover_status") if manifestation.meta else None,
                "authors": work.meta.get("authors", []) if work.meta else [],
                "content_type": manifestation.expression.content_type if manifestation.expression else None,
                "is_owner": True,
                "is_borrowed": False,
                "is_hidden": intent.is_hidden,
                "tags": [],
                "added_at": intent.created_at.isoformat() if hasattr(intent.created_at, "isoformat") else intent.created_at,
                "updated_at": (
                    (intent.updated_at or intent.created_at).isoformat()
                    if hasattr((intent.updated_at or intent.created_at), "isoformat")
                    else (intent.updated_at or intent.created_at)
                ),
            }
        )

    return virtual_items


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
    category_list = parse_csv_param(category_filter)
    format_list_raw = parse_csv_param(format_filter)
    from app.core.format_normalizer import expand_format_filter

    format_list = expand_format_filter(format_list_raw)
    q = request.args.get("q", request.args.get("search", "")).strip()
    sort_by = request.args.get("sort", "updated")
    borrowed_only = request.args.get("borrowed", "false").lower() == "true"
    missing_cover = request.args.get("missing_cover", "false").lower() == "true"
    missing_id = request.args.get("missing_id", "false").lower() == "true"
    # When include_public=true, also include non-hidden available items from other users.
    # This enables the social lending catalogue: borrowers can discover lendable items.
    include_public = request.args.get("include_public", "false").lower() == "true"
    tags_filter = request.args.get("tags", None)
    collections_filter = request.args.get("collections", None)
    genres_filter = request.args.get("genres", None)
    publishers_filter = request.args.get("publishers", None)

    tags_list = parse_csv_param(tags_filter)
    collections_list = parse_csv_param(collections_filter)
    genres_list = parse_csv_param(genres_filter)
    publishers_list = parse_csv_param(publishers_filter)

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    offset = (page - 1) * limit

    virtual_items = get_virtual_items(
        user_id, statuses_filter, category_list, format_list, q, publishers_list, missing_cover, missing_id, genres_list
    )

    combined_items_data = []

    if q:
        from app.core.search_service import SearchService

        statuses_list = parse_csv_param(statuses_filter)
        _, results = SearchService.search_items(
            q,
            user_id,
            1000,
            0,
            statuses=statuses_list,
            category=category_list,
            format_filter=format_list,
            borrowed_only=borrowed_only,
            missing_cover=missing_cover,
            missing_id=missing_id,
            tags=tags_list,
            collections=collections_list,
            genres=genres_list,
            publishers=publishers_list,
        )

        for row in results:
            combined_items_data.append(
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
                    "publisher": row.get("publisher"),
                    "cover_url": row["cover_url"],
                    "cover_status": (row.get("manifestation_meta") or {}).get("cover_status"),
                    "manifestation_meta": row.get("manifestation_meta"),
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
    else:
        query = Item.query.options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))

        if borrowed_only:
            query = query.filter(Item.lent_to_user_id == user_id)
        elif include_public:
            # Social lending catalogue: include own items, borrowed items, AND public
            # available items from other users so borrowers can discover lendable items.
            query = query.filter(
                db.or_(
                    Item.owner_id == user_id,
                    Item.lent_to_user_id == user_id,
                    db.and_(
                        Item.owner_id != user_id,
                        Item.is_hidden.is_(False),
                        Item.collection_status == "available",
                    ),
                )
            )
        else:
            query = query.filter(db.or_(Item.owner_id == user_id, Item.lent_to_user_id == user_id))

        needs_mfn_join = bool(category_list or format_list or missing_cover or missing_id)
        needs_work_join = bool(genres_list or publishers_list or sort_by in ("title", "title-desc", "author"))
        if needs_mfn_join or needs_work_join:
            query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
            query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
            query = query.outerjoin(Work, Expression.work_id == Work.id)

        if category_list:
            query = query.filter(Expression.content_type.in_(category_list))

        if format_list:
            query = query.filter(Manifestation.meta["format"].as_string().in_(format_list))

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
            pubs_conditions = []
            for p in publishers_list:
                p_term = f"%{p.strip()}%"
                pubs_conditions.append(
                    db.or_(
                        Manifestation.publisher.ilike(p_term),
                        Manifestation.meta["Publisher"].as_string().ilike(p_term),
                        Manifestation.meta["publisher"].as_string().ilike(p_term),
                        db.and_(Expression.content_type == "music", Manifestation.meta["label"].as_string().ilike(p_term)),
                    )
                )
            query = query.filter(db.or_(*pubs_conditions))

        if statuses_filter:
            statuses_list = parse_csv_param(statuses_filter)
            query = apply_statuses_filter(query, statuses_list, user_id=user_id, borrowed_only=borrowed_only)

        physical_items = query.all()

        for item in physical_items:
            manifestation = item.manifestation
            work_title = ""
            authors = []
            if manifestation and manifestation.expression and manifestation.expression.work:
                work = manifestation.expression.work
                work_title = work.title or ""
                authors = work.meta.get("authors", []) if work.meta else []

            is_owner = str(item.owner_id) == str(g.user_id) if hasattr(g, "user_id") else False
            is_borrowed = bool(item.lent_to_user_id and str(item.lent_to_user_id) == str(g.user_id)) if hasattr(g, "user_id") else False
            combined_items_data.append(
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
                    "publisher": manifestation.publisher if manifestation else None,
                    "cover_url": manifestation.cover_url
                    or (manifestation.meta.get("cover_url") if manifestation and manifestation.meta else None),
                    "cover_status": manifestation.meta.get("cover_status") if manifestation and manifestation.meta else None,
                    "manifestation_meta": manifestation.meta if manifestation else None,
                    "authors": authors,
                    "content_type": manifestation.expression.content_type if manifestation and manifestation.expression else None,
                    "is_owner": is_owner,
                    "is_borrowed": is_borrowed,
                    "tags": [link.tag.name for link in getattr(item, "tag_links", [])],
                    "added_at": item.added_at.isoformat() if item.added_at else None,
                    "updated_at": (item.updated_at or item.added_at).isoformat() if (item.updated_at or item.added_at) else None,
                }
            )

    combined_items_data.extend(virtual_items)

    if sort_by == "title":
        combined_items_data.sort(key=lambda x: (x["title"] or "").lower())
    elif sort_by == "title-desc":
        combined_items_data.sort(key=lambda x: (x["title"] or "").lower(), reverse=True)
    elif sort_by == "author":
        combined_items_data.sort(key=lambda x: (x["authors"][0] if x["authors"] else "").lower())
    elif sort_by == "added":

        def get_added(x):
            val = x["added_at"]
            if not val:
                return ""
            if isinstance(val, str):
                return val
            return val.isoformat() if hasattr(val, "isoformat") else str(val)

        combined_items_data.sort(key=get_added, reverse=True)
    else:

        def get_updated(x):
            val = x.get("updated_at") or x.get("added_at")
            if not val:
                return ""
            if isinstance(val, str):
                return val
            return val.isoformat() if hasattr(val, "isoformat") else str(val)

        combined_items_data.sort(key=get_updated, reverse=True)

    total = len(combined_items_data)
    paginated_items = combined_items_data[offset : offset + limit]

    return jsonify(
        {
            "success": True,
            "data": paginated_items,
            "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
            "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + limit) < total},
            "error": None,
        }
    )


def _get_virtual_item_detail(item_id: int) -> tuple[Response, int] | Response:
    intent_id = -item_id
    intent = db.session.get(UserWorkIntent, intent_id)
    if not intent:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    # Wishlist entries are shareable with other authenticated users by default
    # (e.g. gift ideas for friends/family) unless the owner hides them --
    # mirrors Item.is_hidden. Anonymous callers never see wishlist items,
    # regardless of is_hidden (BOLA: 404, not 401, to avoid confirming the id
    # exists to an unauthenticated caller).
    user_id = getattr(g, "user_id", None)
    if user_id is None:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    is_owner = str(intent.user_id) == str(user_id)
    user = db.session.get(User, user_id)
    is_admin = bool(user) and any(role.name == "admin" for role in getattr(user, "roles", []))

    if not (is_owner or is_admin) and intent.is_hidden:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    work = intent.work
    manifestation = None
    for expr in work.expressions:
        if expr.manifestations:
            manifestation = expr.manifestations[0]
            break

    owner = db.session.get(User, intent.user_id)
    owner_name = (owner.display_name or owner.email) if owner else None

    if not manifestation:
        # Build work-level-only detail (mirrors get_virtual_items list view behavior)
        item_data = {
            "id": item_id,
            "owner_id": str(intent.user_id),
            "is_owner": is_owner,
            "is_borrowed": False,
            "owner_name": owner_name,
            "owner_count": 0,
            "status": intent.status,
            "collection_status": "wish_list",
            "is_hidden": intent.is_hidden,
            "manifestation_id": None,
            "tags": [],
            "meta": {},
            "isbn": None,
            "manifestation_meta": None,
            "cover_url": None,
            "cover_status": None,
            "work": {
                "id": work.id,
                "title": work.title,
                "authors": work.meta.get("authors", []) if work.meta else [],
                "meta": work.meta,
                "container_work_id": None,
            },
        }
        return jsonify({"success": True, "data": item_data, "error": None})

    item_data = {
        "id": item_id,
        "owner_id": str(intent.user_id),
        "is_owner": is_owner,
        "is_borrowed": False,
        "owner_name": owner_name,
        "owner_count": 0,
        "status": intent.status,
        "collection_status": "wish_list",
        "is_hidden": intent.is_hidden,
        "manifestation_id": manifestation.id,
        "tags": [],
        "meta": {},
        "isbn": manifestation.isbn13,
        "manifestation_meta": manifestation.meta,
        "cover_url": manifestation.cover_url or (manifestation.meta.get("cover_url") if manifestation.meta else None),
        "cover_status": manifestation.meta.get("cover_status") if manifestation.meta else None,
    }

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


def _get_physical_item_detail(item_id: int) -> tuple[Response, int] | Response:
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    user_id = getattr(g, "user_id", None)
    is_owner = (str(item.owner_id) == str(user_id)) if user_id else False
    is_borrowed = user_id and str(item.lent_to_user_id) == str(user_id)
    is_admin = False
    has_read_owners = False

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
        item_data["publisher"] = manifestation.publisher
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


@api_bp.route("/items/<int(signed=True):item_id>", methods=["GET"])
@limiter.limit("300 per hour", override_defaults=True)
@optional_auth
def get_item_detail(item_id: int):
    if item_id < 0:
        return _get_virtual_item_detail(item_id)
    return _get_physical_item_detail(item_id)


def _parse_update_payload(req) -> tuple[ItemUpdateSchema | None, Response | tuple[Response, int] | None]:
    """Helper to parse and validate request payload."""
    data = req.get_json(silent=True)
    if not isinstance(data, dict):
        return None, invalid_json_payload_response()

    try:
        return ItemUpdateSchema(**data), None
    except ValidationError as e:
        return None, (jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400)


def _update_virtual_item(item_id: int, user_id: uuid.UUID | None) -> tuple[Response, int] | Response:
    intent_id = -item_id
    returned_id = None
    err = None

    try:
        with db.session.begin_nested():
            intent = UserWorkIntent.query.filter_by(id=intent_id).with_for_update().first()

            if not intent or not user_id or not verify_item_ownership(item_id, user_id):
                return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

            payload, parse_err = _parse_update_payload(request)
            if parse_err:
                return parse_err
            assert payload is not None

            # Enforce FRBR Ontology Boundary Rules:
            # If not transitioning away from wishlist status, reject physical traits
            wants_tags = payload.tags is not None
            is_transitioning = payload.collection_status != "wish_list" if payload.collection_status else wants_tags
            if not is_transitioning:
                data = request.get_json(silent=True) or {}
                physical_fields = {
                    "barcode",
                    "condition",
                    "physical_condition",
                    "lent_to",
                    "lent_to_user_id",
                    "lent_to_name",
                    "loan_status",
                }
                if any(field in data for field in physical_fields) or (payload.lent_to_user_id or payload.lent_to_name):
                    err = (
                        jsonify(
                            {
                                "success": False,
                                "error": "FRBR Ontology Violation: Wishlist placeholder items (ID < 0) cannot accept physical state mutations.",
                            }
                        ),
                        400,
                    )

            if not err and payload.is_hidden is not None:
                intent.is_hidden = payload.is_hidden

            # If transitioning away from wishlist status, convert to physical item
            if not err and is_transitioning:
                data = request.get_json(silent=True) or {}
                manifestation_id = data.get("manifestation_id")
                manifestation = None

                if manifestation_id:
                    manifestation = db.session.get(Manifestation, manifestation_id)
                    if not manifestation:
                        err = jsonify({"success": False, "data": None, "error": "Invalid manifestation_id"}), 400
                else:
                    work = intent.work
                    for expr in work.expressions:
                        if expr.manifestations:
                            manifestation = expr.manifestations[0]
                            break

                    if not manifestation:
                        # Auto-create placeholder expression and manifestation to preserve FRBR graph purity
                        expr = Expression(work_id=work.id, content_type="text", language="en")
                        db.session.add(expr)
                        db.session.flush()

                        manifestation = Manifestation(expression_id=expr.id, meta={"Title": work.title, "placeholder": True})
                        db.session.add(manifestation)
                        db.session.flush()

                if not err:
                    assert manifestation is not None
                    # Assign dynamically passed collection_status (Library vs Wishlist)
                    item_meta = dict(payload.meta) if payload.meta else {}
                    item_meta["intent_id"] = intent.id
                    item_meta["origin"] = "wishlist_transition"

                    new_item = Item(
                        manifestation_id=manifestation.id,
                        owner_id=intent.user_id,
                        status=payload.status or intent.status,
                        collection_status=payload.collection_status if payload.collection_status else "wish_list",
                        is_hidden=payload.is_hidden or False,
                        lent_to_user_id=uuid.UUID(payload.lent_to_user_id) if payload.lent_to_user_id else None,
                        lent_to_name=payload.lent_to_name,
                        meta=item_meta,
                    )
                    db.session.add(new_item)
                    db.session.flush()

                    sync_tags(new_item.id, intent.user_id, payload.tags)

                    # Implement state machine: do not delete intent, set status to fulfilled
                    intent.status = "fulfilled"
                    db.session.add(intent)
                    db.session.flush()
                    returned_id = new_item.id
            elif not err:
                if payload.status:
                    intent.status = payload.status
                    db.session.add(intent)
                returned_id = item_id

        if err:
            db.session.rollback()
            return err

        db.session.commit()
        return jsonify({"success": True, "data": {"id": returned_id}})

    except db.exc.SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.critical(
            "Database mutation failure handling resource transition for virtual ID %s: %s", item_id, str(exc), exc_info=True
        )
        return jsonify({"success": False, "error": "Internal storage transaction failure encountered during state resolution."}), 500


def _update_physical_item(item_id: int, user_id: uuid.UUID | None, user: User | None) -> tuple[Response, int] | Response:
    item = db.session.get(Item, item_id)
    is_owner = (str(item.owner_id) == str(user_id)) if item and user_id else False
    is_borrower = item is not None and item.lent_to_user_id is not None and str(item.lent_to_user_id) == str(user_id)
    is_admin = any(role.name == "admin" for role in getattr(user, "roles", [])) if user else False
    has_update_permission = user.has_permission(PermissionName.UPDATE_ITEM) if user else False

    if not item or not (is_owner or is_borrower or is_admin or has_update_permission):
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    payload, err = _parse_update_payload(request)
    if err:
        return err
    assert payload is not None

    if not (is_owner or is_admin or has_update_permission):
        # Must be borrower. Borrowers can only update progress status.
        disallowed = [f for f in payload.model_fields_set if f != "status"]
        if disallowed:
            return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    if payload.status and payload.status != item.status:
        old_status = item.status
        item.status = payload.status
        log = ItemStatusLog(item_id=item.id, user_id=user_id, old_status=old_status, new_status=item.status)
        db.session.add(log)

    # Check if final status will be "lent"
    final_collection_status = payload.collection_status if payload.collection_status is not None else item.collection_status
    validation_error = None
    if final_collection_status == "lent":
        final_lent_to_user_id = payload.lent_to_user_id if "lent_to_user_id" in payload.model_fields_set else item.lent_to_user_id
        final_lent_to_name = payload.lent_to_name if "lent_to_name" in payload.model_fields_set else item.lent_to_name
        if not final_lent_to_user_id and not (final_lent_to_name and final_lent_to_name.strip()):
            validation_error = jsonify({"error": "Lent items require either a borrower user ID or a name.", "code": 400}), 400

    if payload.collection_status and payload.collection_status != item.collection_status:
        old_c_status = item.collection_status
        item.collection_status = payload.collection_status
        log = ItemStatusLog(item_id=item.id, user_id=user_id, old_status=old_c_status, new_status=item.collection_status)
        db.session.add(log)
        # If we transition away from "lent", auto-clear borrower details
        if old_c_status == "lent" and payload.collection_status != "lent":
            if "lent_to_user_id" not in payload.model_fields_set:
                item.lent_to_user_id = None
            if "lent_to_name" not in payload.model_fields_set:
                item.lent_to_name = None

    if "lent_to_user_id" in payload.model_fields_set:
        item.lent_to_user_id = uuid.UUID(payload.lent_to_user_id) if payload.lent_to_user_id else None
    if "lent_to_name" in payload.model_fields_set:
        item.lent_to_name = payload.lent_to_name
    if payload.is_hidden is not None:
        item.is_hidden = payload.is_hidden

    # Optional metadata update from extra fields or meta field
    metadata = payload.model_extra or {}
    if isinstance(payload.meta, dict):
        metadata.update(payload.meta)

    # BOLA protection: block sensitive fields
    forbidden = {"owner_id", "id", "created_at"}
    if validation_error is None and any(k in metadata for k in forbidden):
        validation_error = jsonify({"success": False, "error": "Invalid payload: forbidden fields"}), 400

    if validation_error is not None:
        return validation_error

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


@api_bp.route("/items/<int(signed=True):item_id>", methods=["PUT"])
@require_auth
def update_item(item_id: int):
    """Update an item by ID.

    Negative IDs are virtual wishlist intents (``UserWorkIntent``) and are
    routed to ``_update_virtual_item``.  Zero and positive IDs that do not
    exist are handled by ``_update_physical_item``.  ``@require_physical_item``
    is intentionally **not** applied here because this route also accepts
    virtual-item transitions (wishlist → library); the FRBR boundary for
    irreversible physical mutations is enforced inside ``_update_virtual_item``.
    """
    user_id = getattr(g, "user_id", None)
    user = db.session.get(User, user_id) if user_id else None

    # Route virtual wishlist items to their dedicated handler.
    # ID == 0 explicitly returns a 400 Bad Request to enforce strictly positive IDs.
    if item_id < 0:
        return _update_virtual_item(item_id, user_id)
    if item_id == 0:
        return jsonify({"error": "Cannot mutate virtual items (id <= 0). Physical item IDs must be strictly positive.", "code": 400}), 400
    return _update_physical_item(item_id, user_id, user)


def _delete_virtual_item(item_id: int, user_id: uuid.UUID | None) -> tuple[Response, int] | Response:
    intent_id = -item_id
    intent = db.session.get(UserWorkIntent, intent_id)
    if not intent:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    if not user_id or not verify_item_ownership(item_id, user_id):
        return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

    db.session.delete(intent)
    db.session.commit()
    return jsonify({"success": True, "data": {"id": item_id}, "error": None})


def _delete_physical_item(item_id: int, user_id: uuid.UUID | None) -> tuple[Response, int] | Response:
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    if not user_id or not verify_item_ownership(item_id, user_id):
        return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True, "data": {"id": item_id}, "error": None})


@api_bp.route("/items/<int(signed=True):item_id>", methods=["DELETE"])
@require_auth
@require_permission(PermissionName.DELETE_ITEM)
@require_item_access()
def delete_item(item_id: int):
    user_id = getattr(g, "user_id", None)
    try:
        if item_id < 0:
            return _delete_virtual_item(item_id, user_id)
        return _delete_physical_item(item_id, user_id)
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        return jsonify({"success": False, "data": None, "error": str(e)}), 500


@api_bp.route("/items/<int(signed=True):item_id>/collections", methods=["GET"])
@require_auth
@require_physical_item
@require_item_access()
def get_item_collections(item_id: int) -> Response | tuple[Response, int]:
    """List the named collections an item belongs to."""
    user_id = getattr(g, "user_id", None)
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404
    if not user_id or not verify_item_ownership(item_id, user_id):
        return jsonify({"success": False, "error": "Forbidden"}), 403

    links = (
        db.session.query(UserCollection)
        .join(UserCollectionItem, UserCollectionItem.collection_id == UserCollection.id)
        .filter(UserCollectionItem.item_id == item_id)
        .all()
    )
    collections_data = [{"id": c.id, "name": c.name, "parent_id": c.parent_id} for c in links]
    return jsonify({"success": True, "data": {"collections": collections_data}, "error": None})


def _guard_add_item_to_collection(item_id: int) -> tuple[dict | None, tuple[Response, int] | None]:
    """Validate preconditions for adding an item to a collection.

    Returns:
        (dict, None) on success with validated payload data.
        (None, tuple[Response, int]) on validation failure.
    """
    user_id = getattr(g, "user_id", None)

    payload_json = request.get_json(silent=True)
    try:
        payload = ItemCollectionLinkSchema(**(payload_json or {}))
    except ValidationError as e:
        return None, (jsonify({"success": False, "error": e.errors()}), 400)

    item = db.session.get(Item, item_id)
    if not item:
        return None, (jsonify({"success": False, "error": "Item not found"}), 404)
    if not user_id or not verify_item_ownership(item_id, user_id):
        return None, (jsonify({"success": False, "error": "Forbidden"}), 403)

    collection = (
        db.session.query(UserCollection)
        .filter(
            UserCollection.id == payload.collection_id,
            UserCollection.owner_id == item.owner_id,
        )
        .first()
    )
    if not collection:
        return None, (jsonify({"success": False, "error": "Collection not found"}), 404)

    existing = (
        db.session.query(UserCollectionItem)
        .filter(
            UserCollectionItem.collection_id == payload.collection_id,
            UserCollectionItem.item_id == item_id,
        )
        .first()
    )
    if existing:
        return None, (jsonify({"success": False, "error": "Item is already in this collection"}), 409)

    return {"collection_id": payload.collection_id}, None


@api_bp.route("/items/<int(signed=True):item_id>/collections", methods=["POST"])
@limiter.limit("60 per minute", override_defaults=True)
@require_auth
@require_permission(PermissionName.WRITE_ITEM)
@require_physical_item
@require_item_access()
def add_item_to_collection(item_id: int) -> Response | tuple[Response, int]:
    """Link an owned item to a named collection.

    Creates a UserCollectionItem association. The item must belong to the
    authenticated user. Virtual wishlist items (item_id < 0) are rejected
    because they have no physical copy to shelve.
    """
    validated, err = _guard_add_item_to_collection(item_id)
    if err is not None:
        return err
    assert validated is not None  # Narrowed by err check above

    collection_id = validated["collection_id"]

    try:
        link = UserCollectionItem(collection_id=collection_id, item_id=item_id)
        db.session.add(link)
        db.session.commit()
        return jsonify({"success": True, "data": {"item_id": item_id, "collection_id": collection_id}})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        logger.error("Database error linking item %s to collection %s: %s", item_id, collection_id, str(e))
        return jsonify({"success": False, "error": "An internal database error occurred while processing the request."}), 500


@api_bp.route("/items/<int(signed=True):item_id>/collections/<int:collection_id>", methods=["DELETE"])
@limiter.limit("60 per minute", override_defaults=True)
@require_auth
@require_permission(PermissionName.WRITE_ITEM)
@require_physical_item
@require_item_access()
def remove_item_from_collection(item_id: int, collection_id: int) -> Response | tuple[Response, int]:
    """Unlink an owned item from a named collection.

    Removes the UserCollectionItem association without deleting the Item itself.
    """
    user_id = getattr(g, "user_id", None)

    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404
    if not user_id or not verify_item_ownership(item_id, user_id):
        return jsonify({"success": False, "error": "Forbidden"}), 403

    link = (
        db.session.query(UserCollectionItem)
        .filter(
            UserCollectionItem.collection_id == collection_id,
            UserCollectionItem.item_id == item_id,
        )
        .first()
    )
    if not link:
        return jsonify({"success": False, "error": "Item is not in this collection"}), 404

    try:
        db.session.delete(link)
        db.session.commit()
        return jsonify({"success": True, "data": {"item_id": item_id, "collection_id": collection_id}})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        logger.error("Database error unlinking item %s from collection %s: %s", item_id, collection_id, str(e))
        return jsonify({"success": False, "error": "An internal database error occurred while processing the request."}), 500


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
    payload = None
    error_response = None
    if not isinstance(payload_json, dict):
        if payload_json is None and not request.data:
            payload_json = {}
        else:
            error_response = invalid_json_payload_response()

    if not error_response:
        assert isinstance(payload_json, dict)
        try:
            payload = ItemCreateSchema(**payload_json)
        except (ValidationError, TypeError) as e:
            error_response = jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    if error_response:
        return error_response
    assert payload is not None

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

    if payload.collection_status == "lent":
        if not payload.lent_to_user_id and not (payload.lent_to_name or "").strip():
            return jsonify({"error": "Lent items require either a borrower user ID or a name.", "code": 400}), 400

    item = Item(
        manifestation_id=manifestation.id,
        owner_id=user_id,
        status=payload.status or "want_to_read",
        collection_status=payload.collection_status,
        lent_to_user_id=uuid.UUID(payload.lent_to_user_id) if payload.lent_to_user_id else None,
        lent_to_name=payload.lent_to_name,
        meta={},
    )
    db.session.add(item)
    try:
        db.session.flush()
        log_initial_item_status(item.id, user_id, item.status, item.collection_status)
        sync_tags(item.id, user_id, payload.tags)
        db.session.commit()
        return jsonify({"success": True, "data": {"item_id": item.id, "manifestation_id": manifestation.id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        current_app.logger.exception("Failed to add item for ISBN %s for user %s: %s", isbn, user_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to create item"}), 500


def _add_wishlist_by_manifestation(user_id: uuid.UUID, manifestation: Manifestation, payload: ItemCreateSchema) -> tuple[Response, int]:
    """Helper to route wishlist creation to UserWorkIntent."""
    work = manifestation.expression.work if manifestation.expression and manifestation.expression.work else None
    if not work:
        return (
            jsonify({"success": False, "data": None, "error": "Work not found for manifestation"}),
            500,
        )

    from app.db.core import CATEGORY_PROGRESS_STATUSES

    content_type = manifestation.expression.content_type if manifestation.expression else "text"
    statuses = CATEGORY_PROGRESS_STATUSES.get(content_type, ("want_to_read",))
    default_progress = payload.status or next((s for s in statuses if s.startswith("want_to_")), statuses[0])

    intent = UserWorkIntent.query.filter_by(user_id=user_id, work_id=work.id).first()
    if not intent:
        intent = UserWorkIntent(user_id=user_id, work_id=work.id, status=default_progress)
        db.session.add(intent)
        db.session.flush()

    db.session.commit()
    return (
        jsonify(
            {
                "success": True,
                "data": {"item_id": None, "intent_id": intent.id, "manifestation_id": manifestation.id},
                "error": None,
            }
        ),
        200,
    )


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
    payload = None
    error_response = None
    if not isinstance(payload_json, dict):
        if payload_json is None and not request.data:
            payload_json = {}
        else:
            error_response = invalid_json_payload_response()

    if not error_response:
        try:
            assert isinstance(payload_json, dict)
            payload = ItemCreateSchema(**payload_json)
        except (ValidationError, TypeError) as e:
            error_response = jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    if error_response:
        return error_response
    assert payload is not None

    if payload.collection_status == "lent":
        if not payload.lent_to_user_id and not (payload.lent_to_name or "").strip():
            return jsonify({"error": "Lent items require either a borrower user ID or a name.", "code": 400}), 400

    if payload.collection_status == "wish_list":
        return _add_wishlist_by_manifestation(user_id, manifestation, payload)

    item = Item(
        manifestation_id=manifestation.id,
        owner_id=user_id,
        status=payload.status or "want_to_read",
        collection_status=payload.collection_status,
        lent_to_user_id=uuid.UUID(payload.lent_to_user_id) if payload.lent_to_user_id else None,
        lent_to_name=payload.lent_to_name,
        meta={},
    )
    db.session.add(item)
    db.session.flush()
    log_initial_item_status(item.id, user_id, item.status, item.collection_status)
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
    payload = None
    error_response = None
    if not isinstance(payload_json, dict):
        error_response = invalid_json_payload_response()
    else:
        try:
            payload = ItemBulkCreateSchema(**payload_json)
        except ValidationError as e:
            error_response = jsonify({"error": f"Invalid payload: {str(e)}", "code": 400}), 400

    if error_response:
        return error_response
    assert payload is not None

    if payload.collection_status == "lent":
        return jsonify({"error": "Lent items require either a borrower user ID or a name.", "code": 400}), 400

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
            statuses = CATEGORY_PROGRESS_STATUSES.get(category, ("want_to_read",))
            if payload.collection_status == "wish_list":
                status = next((s for s in statuses if s.startswith("want_to_")), statuses[0])
            else:
                status = statuses[0]

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
        db.session.flush()
        for item in created_items:
            log_initial_item_status(item.id, user_id, item.status, item.collection_status)
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

    statuses = CATEGORY_PROGRESS_STATUSES.get(category, ("want_to_read",))
    if payload.collection_status == "wish_list":
        default_status = next((s for s in statuses if s.startswith("want_to_")), statuses[0])
    else:
        default_status = statuses[0]

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

        if payload.collection_status == "lent":
            lent_to_name = payload.lent_to_name
            if not payload.lent_to_user_id and not (lent_to_name and lent_to_name.strip()):
                return jsonify({"error": "Lent items require either a borrower user ID or a name.", "code": 400}), 400

        item = Item(
            manifestation_id=manifestation.id,
            owner_id=user_id,
            status=payload.status or default_status,
            collection_status=payload.collection_status,
            lent_to_user_id=uuid.UUID(payload.lent_to_user_id) if payload.lent_to_user_id else None,
            lent_to_name=payload.lent_to_name,
            meta={},
        )
        db.session.add(item)
        db.session.flush()
        log_initial_item_status(item.id, user_id, item.status, item.collection_status)
        sync_tags(item.id, user_id, payload.tags)
        db.session.commit()

        return jsonify({"success": True, "data": {"item_id": item.id, "manifestation_id": manifestation.id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        current_app.logger.exception("Failed to create manual item for user %s: %s", user_id, e)
        return jsonify({"success": False, "data": None, "error": "Failed to create item"}), 500


@api_bp.route("/items/<int(signed=True):item_id>/logs", methods=["GET"])
@require_auth
def get_item_logs(item_id: int) -> Response | tuple[Response, int]:
    """Get the status timeline for an item."""
    if item_id < 0:
        return jsonify({"success": True, "data": []})

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

    is_borrower = item.lent_to_user_id is not None and str(item.lent_to_user_id) == str(user_id)
    if not (is_owner or is_borrower or is_admin or has_update_permission):
        return jsonify({"success": False, "data": None, "error": "Forbidden"}), 403

    from app.core.taxonomy import PROGRESS_STATUSES

    logs = (
        db.session.query(ItemStatusLog)
        .filter(ItemStatusLog.item_id == item_id)
        .order_by(ItemStatusLog.changed_at.desc(), ItemStatusLog.id.desc())
        .all()
    )

    category = "text"
    if item.manifestation and item.manifestation.expression:
        category = item.manifestation.expression.content_type or "text"

    data = []
    for entry in logs:
        if entry.old_status is None:
            if entry.new_status in PROGRESS_STATUSES:
                log_type = "creation"
            else:
                log_type = "collection"
        elif entry.new_status in PROGRESS_STATUSES:
            log_type = "progress"
        else:
            log_type = "collection"

        operator_name = "System"
        if entry.user:
            if str(entry.user_id) == str(user_id):
                operator_name = "You"
            else:
                operator_name = entry.user.display_name or entry.user.email or "Unknown User"

        data.append(
            {
                "old_status": entry.old_status,
                "new_status": entry.new_status,
                "changed_at": entry.changed_at.isoformat(),
                "log_type": log_type,
                "operator_name": operator_name,
                "category": category,
            }
        )

    return jsonify({"success": True, "data": data, "error": None})


@api_bp.route("/items/<int(signed=True):item_id>/visibility", methods=["PATCH"])
@require_auth
def toggle_item_visibility(item_id: int):
    """
    Toggles the is_hidden flag for a specific item or wishlist entry.
    Hidden items/entries do not appear to other authenticated users (e.g. on a
    shared wishlist or public profile).
    """
    user_id = getattr(g, "user_id", None)

    data = request.get_json() or {}
    if "is_hidden" not in data:
        return jsonify({"error": "Missing 'is_hidden' boolean field.", "code": 400}), 400

    new_val = data["is_hidden"]
    if not isinstance(new_val, bool):
        return jsonify({"error": "Field 'is_hidden' must be a boolean.", "code": 400}), 400

    if item_id < 0:
        intent = db.session.get(UserWorkIntent, -item_id)
        if not intent or str(intent.user_id) != str(user_id):
            # Return 404 even if forbidden to prevent data leakage (BOLA protection)
            return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

        intent.is_hidden = new_val
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Item visibility updated to {'hidden' if intent.is_hidden else 'public'}.",
                "is_hidden": intent.is_hidden,
            }
        )

    item = db.session.get(Item, item_id)

    if not item or str(item.owner_id) != str(user_id):
        # Return 404 even if forbidden to prevent data leakage (BOLA protection)
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    item.is_hidden = new_val
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"Item visibility updated to {'hidden' if item.is_hidden else 'public'}.",
            "is_hidden": item.is_hidden,
        }
    )


@api_bp.route("/qrcode/<int(signed=True):item_id>", methods=["GET"])
@require_auth
@require_item_access(bola=True)
def get_item_qrcode(item_id: int) -> Response | tuple[Response, int]:
    """
    Generates a QR code image for a specific item to allow physical copy tracking.
    Supports ?format=svg and ?format=png (default).
    """
    import io
    import os
    import xml.etree.ElementTree as ET

    import qrcode
    from flask import send_file

    if item_id < 0:
        # Wishlist entries have no physical copy to tag.
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    frontend_url = os.environ.get("NEXT_PUBLIC_FRONTEND_URL", "http://localhost:3000")
    item_url = f"{frontend_url}/item/{item_id}"

    # Enable High error correction (30%) to handle the embedded logo in the center
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(item_url)
    qr.make(fit=True)

    img_format = request.args.get("format", "png").lower()

    if img_format == "svg":
        import re

        import qrcode.image.svg

        img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        root = img._img

        # Extract dimensions, safely ignoring units like 'mm' or 'px'
        width_str = root.get("width", "290")
        width_match = re.search(r"[\d.]+", width_str)
        width = float(width_match.group(0)) if width_match else 290.0
        center_x = width / 2.0
        center_y = width / 2.0
        logo_size = width * 0.22
        padding = width * 0.02

        rect_size = logo_size + 2 * padding
        rect_x = center_x - rect_size / 2.0
        rect_y = center_y - rect_size / 2.0

        # Append white quiet zone rect
        rect = ET.Element(
            "rect",
            x=str(rect_x),
            y=str(rect_y),
            width=str(rect_size),
            height=str(rect_size),
            fill="white",
        )
        root.append(rect)

        # Load SVG path from logo file
        logo_path = os.path.join(current_app.root_path, "../resources/images/iqoqo-logo.svg")
        try:
            with open(logo_path, encoding="utf-8") as f:
                logo_svg = f.read()

            root_logo = ET.fromstring(logo_svg)
            path_el_logo = None
            for el in root_logo.iter():
                if el.tag.endswith("path"):
                    path_el_logo = el
                    break

            if path_el_logo is not None:
                d_attr = path_el_logo.get("d")
                if d_attr:
                    scale = logo_size / 200.0
                    offset_x = center_x - logo_size / 2.0
                    offset_y = center_y - logo_size / 2.0

                    path_el = ET.Element(
                        "path",
                        d=d_attr,
                        fill="#d15500",
                        transform=f"translate({offset_x},{offset_y}) scale({scale})",
                    )
                    root.append(path_el)
        except (ET.ParseError, OSError, AttributeError, ValueError, KeyError) as e:
            current_app.logger.error("Failed to embed logo in SVG QR code: %s", e)

        img_io = io.BytesIO()
        img.save(img_io)
        img_io.seek(0)
        return send_file(img_io, mimetype="image/svg+xml")

    # PNG Format
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    from PIL import ImageDraw

    W, H = img.size
    center_x = W // 2
    center_y = H // 2
    logo_size = int(W * 0.22)
    padding = int(W * 0.02)

    # Draw quiet zone white square in center
    draw = ImageDraw.Draw(img)
    half_rect = (logo_size + 2 * padding) // 2
    draw.rectangle(
        [center_x - half_rect, center_y - half_rect, center_x + half_rect, center_y + half_rect],
        fill="white",
    )

    logo_path = os.path.join(current_app.root_path, "../resources/images/iqoqo-logo.svg")
    try:
        with open(logo_path, encoding="utf-8") as f:
            logo_svg = f.read()

        import re

        root_logo = ET.fromstring(logo_svg)
        path_el_logo = None
        for el in root_logo.iter():
            if el.tag.endswith("path"):
                path_el_logo = el
                break

        if path_el_logo is not None:
            d_attr = path_el_logo.get("d")
            if d_attr:
                # Parse path command tokens
                tokens = re.findall(r"([a-zA-Z])|([-+]?\d*\.\d+|[-+]?\d+)", d_attr)
                commands: list[tuple[str, list[float]]] = []
                for cmd, val in tokens:
                    if cmd:
                        commands.append((cmd, []))
                    elif val:
                        if commands:
                            commands[-1][1].append(float(val))

                polygons: list[list[tuple[float, float]]] = []
                current_polygon: list[tuple[float, float]] = []
                cx, cy = 0.0, 0.0
                start_x, start_y = 0.0, 0.0

                for cmd, args in commands:
                    if cmd == "M":
                        if current_polygon:
                            polygons.append(current_polygon)
                        cx, cy = args[0], args[1]
                        start_x, start_y = cx, cy
                        current_polygon = [(cx, cy)]
                        for idx in range(2, len(args), 2):
                            cx, cy = args[idx], args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd == "m":
                        if current_polygon:
                            polygons.append(current_polygon)
                        cx += args[0]
                        cy += args[1]
                        start_x, start_y = cx, cy
                        current_polygon = [(cx, cy)]
                        for idx in range(2, len(args), 2):
                            cx += args[idx]
                            cy += args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd == "L":
                        for idx in range(0, len(args), 2):
                            cx, cy = args[idx], args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd == "l":
                        for idx in range(0, len(args), 2):
                            cx += args[idx]
                            cy += args[idx + 1]
                            current_polygon.append((cx, cy))
                    elif cmd == "c":
                        for idx in range(0, len(args), 6):
                            dx1, dy1, dx2, dy2, dx, dy = args[idx : idx + 6]
                            x1, y1 = cx + dx1, cy + dy1
                            x2, y2 = cx + dx2, cy + dy2
                            x3, y3 = cx + dx, cy + dy
                            steps = 5
                            for s in range(1, steps + 1):
                                t = s / steps
                                b0 = (1 - t) ** 3
                                b1 = 3 * ((1 - t) ** 2) * t
                                b2 = 3 * (1 - t) * (t**2)
                                b3 = t**3
                                px = b0 * cx + b1 * x1 + b2 * x2 + b3 * x3
                                py = b0 * cy + b1 * y1 + b2 * y2 + b3 * y3
                                current_polygon.append((px, py))
                            cx, cy = x3, y3
                    elif cmd == "C":
                        for idx in range(0, len(args), 6):
                            x1, y1, x2, y2, x3, y3 = args[idx : idx + 6]
                            steps = 5
                            for s in range(1, steps + 1):
                                t = s / steps
                                b0 = (1 - t) ** 3
                                b1 = 3 * ((1 - t) ** 2) * t
                                b2 = 3 * (1 - t) * (t**2)
                                b3 = t**3
                                px = b0 * cx + b1 * x1 + b2 * x2 + b3 * x3
                                py = b0 * cy + b1 * y1 + b2 * y2 + b3 * y3
                                current_polygon.append((px, py))
                            cx, cy = x3, y3
                    elif cmd in ("z", "Z"):
                        if current_polygon:
                            current_polygon.append((start_x, start_y))
                            polygons.append(current_polygon)
                            current_polygon = []
                        cx, cy = start_x, start_y

                if current_polygon:
                    polygons.append(current_polygon)

                scale = logo_size / 200.0
                offset_x = center_x - logo_size / 2.0
                offset_y = center_y - logo_size / 2.0

                for p_idx, poly in enumerate(polygons):
                    scaled_poly = [(offset_x + x * scale, offset_y + y * scale) for x, y in poly]
                    if len(scaled_poly) >= 3:
                        # Alternate colors for cutouts vs solid fills
                        color = "white" if p_idx in (1, 5, 7) else "#d15500"
                        draw.polygon(scaled_poly, fill=color)
    except (ET.ParseError, OSError, AttributeError, ValueError, KeyError) as e:
        current_app.logger.error("Failed to embed logo in PNG QR code: %s", e)

    img_io = io.BytesIO()
    img.save(img_io, "PNG")
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")
