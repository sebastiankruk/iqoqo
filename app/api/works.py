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
"""API routes for Work and Expression level specialized views."""

from flask import Response, g, jsonify, request
from sqlalchemy.orm import selectinload

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import optional_auth, require_auth, require_permission
from app.api.filters import apply_genre_filter
from app.core.permissions import PermissionName
from app.db.models import Expression, Item, Manifestation, UserWorkIntent, Work, WorkPart, db


@api_bp.route("/works/shelf", methods=["GET"])
@optional_auth
def get_works_catalog() -> Response:
    """
    Return a global catalog view of all Conceptual Works with optional
    filtering.  When the user is authenticated their owned items and
    work-level intents are annotated onto each result so the frontend can
    show an "already owned" badge.

    Query parameters: q, category, tags, collections, genres, publishers,
    limit, offset.
    """
    user_id = getattr(g, "user_id", None)
    search_q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    tags_filter = request.args.get("tags")
    collections_filter = request.args.get("collections")
    genres_filter = request.args.get("genres")
    publishers_filter = request.args.get("publishers")
    statuses_filter = request.args.get("statuses")
    formats_filter = request.args.get("formats")

    tags_list = [t.strip() for t in tags_filter.split(",") if t.strip()] if tags_filter else None
    collections_list = [c.strip() for c in collections_filter.split(",") if c.strip()] if collections_filter else None
    genres_list = [gen.strip() for gen in genres_filter.split(",") if gen.strip()] if genres_filter else None
    publishers_list = [p.strip() for p in publishers_filter.split(",") if p.strip()] if publishers_filter else None
    statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()] if statuses_filter else None
    formats_list = [f.strip() for f in formats_filter.split(",") if f.strip()] if formats_filter else None

    limit_arg = request.args.get("limit")
    limit = int(limit_arg) if limit_arg is not None else 1000
    if limit_arg is not None:
        limit = min(max(limit, 1), 100)

    offset = request.args.get("offset", 0, type=int)
    offset = max(offset, 0)

    # Always use the global catalog query (no owner-scope filter).
    # User-owned annotations (items, intents) are attached later.
    base_query = (
        db.session.query(Work.id)
        .join(Expression, Expression.work_id == Work.id)
        .join(Manifestation, Manifestation.expression_id == Expression.id)
    )
    has_item_joined = False

    if category:
        base_query = base_query.filter(Expression.content_type == category)

    if search_q:
        pattern = f"%{search_q}%"
        base_query = base_query.filter(
            db.or_(
                Work.title.ilike(pattern),
                db.cast(Work.meta["authors"], db.String).ilike(pattern),
                db.cast(Work.meta["creators"], db.String).ilike(pattern),
            )
        )

    if tags_list:
        from app.db.models import ItemTag, Tag

        if not has_item_joined:
            if user_id:
                base_query = base_query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == user_id))
            else:
                base_query = base_query.join(Item, Manifestation.id == Item.manifestation_id)
            has_item_joined = True
        base_query = base_query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
        tags_conditions = [Tag.name.ilike(f.strip()) for f in tags_list]
        base_query = base_query.filter(db.or_(*tags_conditions))

    if collections_list and user_id:
        from app.db.models import UserCollection, UserCollectionItem

        if not has_item_joined:
            base_query = base_query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == user_id))
            has_item_joined = True
        base_query = base_query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
            UserCollection, UserCollectionItem.collection_id == UserCollection.id
        )
        coll_conditions = [UserCollection.name.ilike(c.strip()) for c in collections_list]
        base_query = base_query.filter(db.or_(*coll_conditions), UserCollection.owner_id == user_id)

    if genres_list:
        base_query = apply_genre_filter(base_query, genres_list)

    if publishers_list:
        pubs_conditions = [Manifestation.publisher.ilike(f"%{p.strip()}%") for p in publishers_list]
        base_query = base_query.filter(db.or_(*pubs_conditions))

    if statuses_list and user_id:
        if not has_item_joined:
            base_query = base_query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == user_id))
            has_item_joined = True
        base_query = base_query.filter(db.or_(Item.status.in_(statuses_list), Item.collection_status.in_(statuses_list)))

    if formats_list:
        base_query = base_query.filter(Manifestation.meta["format"].as_string().in_(formats_list))

    # Get the total count of distinct works matching the filters
    total_count = base_query.with_entities(Work.id).distinct().count()

    # Get the paginated list of work IDs
    work_ids = [
        row[0]
        for row in base_query.with_entities(Work.id, Work.title).distinct().order_by(Work.title.asc()).offset(offset).limit(limit).all()
    ]

    works = (
        db.session.query(Work)
        .options(selectinload(Work.expressions).selectinload(Expression.manifestations))  # type: ignore[arg-type]
        .filter(Work.id.in_(work_ids))
        .all()
    )

    manifestation_ids = []
    for w in works:
        for expr in w.expressions:  # type: ignore[attr-defined]
            for manif in expr.manifestations:
                manifestation_ids.append(manif.id)

    owned_items = []
    if user_id and manifestation_ids:
        owned_items = db.session.query(Item).filter(Item.owner_id == user_id, Item.manifestation_id.in_(manifestation_ids)).all()

    owned_items_map = {item.manifestation_id: item for item in owned_items}

    # Fetch user work intents for the loaded works
    intents = []
    if user_id and work_ids:
        intents = db.session.query(UserWorkIntent).filter(UserWorkIntent.user_id == user_id, UserWorkIntent.work_id.in_(work_ids)).all()
    intents_map = {intent.work_id: intent for intent in intents}

    works_map: dict[int, dict] = {}
    for work in works:
        creators: list[str] = []
        if work.meta:
            creators = work.meta.get("creators") or work.meta.get("authors") or []

        owned_manifestations = []
        total_items = 0
        has_intent = work.id in intents_map

        for expr in work.expressions:  # type: ignore[attr-defined]
            if category and (expr.content_type or "").lower() != category:
                continue

            for manif in expr.manifestations:
                owned_item = owned_items_map.get(manif.id)
                effective_cover = manif.cover_url or (manif.meta.get("cover_url") if manif.meta else None)

                if owned_item:
                    if not effective_cover and owned_item.meta:
                        effective_cover = owned_item.meta.get("cover_url")

                    owned_manifestations.append(
                        {
                            "manifestation_id": manif.id,
                            "item_id": owned_item.id,
                            "format": manif.meta.get("format", "Unknown") if manif.meta else "Unknown",
                            "cover_url": effective_cover,
                        }
                    )
                    total_items += 1
                else:
                    owned_manifestations.append(
                        {
                            "manifestation_id": manif.id,
                            "item_id": None,
                            "format": manif.meta.get("format", "Unknown") if manif.meta else "Unknown",
                            "cover_url": effective_cover,
                            "intent_status": intents_map[work.id].status if has_intent else None,
                        }
                    )

        works_map[work.id] = {
            "work_id": work.id,
            "title": work.title,
            "creators": creators,
            "owned_manifestations": owned_manifestations,
            "total_items": total_items,
        }

    # Sort the resulting list by title to match the ID query order
    result_data = sorted(works_map.values(), key=lambda x: x["title"].lower())

    return jsonify(
        {
            "success": True,
            "data": result_data,
            "total": total_count,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count,
            },
        }
    )


@api_bp.route("/expressions/shelf", methods=["GET"])
@optional_auth
def get_expressions_catalog() -> Response:
    """
    Return a global catalog view of all Expressions with optional
    filtering.  When the user is authenticated their owned items and
    work-level intents are annotated onto each result so the frontend can
    show an "already owned" badge.

    Query parameters: q, category, tags, collections, genres, publishers,
    limit, offset.
    """
    user_id = getattr(g, "user_id", None)
    search_q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    tags_filter = request.args.get("tags")
    collections_filter = request.args.get("collections")
    genres_filter = request.args.get("genres")
    publishers_filter = request.args.get("publishers")
    statuses_filter = request.args.get("statuses")
    formats_filter = request.args.get("formats")

    tags_list = [t.strip() for t in tags_filter.split(",") if t.strip()] if tags_filter else None
    collections_list = [c.strip() for c in collections_filter.split(",") if c.strip()] if collections_filter else None
    genres_list = [gen.strip() for gen in genres_filter.split(",") if gen.strip()] if genres_filter else None
    publishers_list = [p.strip() for p in publishers_filter.split(",") if p.strip()] if publishers_filter else None
    statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()] if statuses_filter else None
    formats_list = [f.strip() for f in formats_filter.split(",") if f.strip()] if formats_filter else None

    limit_arg = request.args.get("limit")
    limit = int(limit_arg) if limit_arg is not None else 1000
    if limit_arg is not None:
        limit = min(max(limit, 1), 100)

    offset = request.args.get("offset", 0, type=int)
    offset = max(offset, 0)

    # Always use the global catalog query (no owner-scope filter).
    # User-owned annotations (items, intents) are attached later.
    base_query = (
        db.session.query(Expression.id)
        .join(Work, Expression.work_id == Work.id)
        .join(Manifestation, Manifestation.expression_id == Expression.id)
    )
    has_item_joined = False

    if category:
        base_query = base_query.filter(Expression.content_type == category)

    if search_q:
        pattern = f"%{search_q}%"
        base_query = base_query.filter(
            db.or_(
                Work.title.ilike(pattern),
                db.cast(Work.meta["authors"], db.String).ilike(pattern),
                db.cast(Work.meta["creators"], db.String).ilike(pattern),
            )
        )

    if tags_list:
        from app.db.models import ItemTag, Tag

        if not has_item_joined:
            if user_id:
                base_query = base_query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == user_id))
            else:
                base_query = base_query.join(Item, Manifestation.id == Item.manifestation_id)
            has_item_joined = True
        base_query = base_query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
        tags_conditions = [Tag.name.ilike(f.strip()) for f in tags_list]
        base_query = base_query.filter(db.or_(*tags_conditions))

    if collections_list and user_id:
        from app.db.models import UserCollection, UserCollectionItem

        if not has_item_joined:
            base_query = base_query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == user_id))
            has_item_joined = True
        base_query = base_query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
            UserCollection, UserCollectionItem.collection_id == UserCollection.id
        )
        coll_conditions = [UserCollection.name.ilike(c.strip()) for c in collections_list]
        base_query = base_query.filter(db.or_(*coll_conditions), UserCollection.owner_id == user_id)

    if genres_list:
        base_query = apply_genre_filter(base_query, genres_list)

    if publishers_list:
        pubs_conditions = [Manifestation.publisher.ilike(f"%{p.strip()}%") for p in publishers_list]
        base_query = base_query.filter(db.or_(*pubs_conditions))

    if statuses_list and user_id:
        if not has_item_joined:
            base_query = base_query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == user_id))
            has_item_joined = True
        base_query = base_query.filter(db.or_(Item.status.in_(statuses_list), Item.collection_status.in_(statuses_list)))

    if formats_list:
        base_query = base_query.filter(Manifestation.meta["format"].as_string().in_(formats_list))

    # Base query for distinct expression IDs
    base_expr_query = base_query.with_entities(Expression.id).distinct()
    total_count = base_expr_query.count()

    expr_ids = [row[0] for row in base_expr_query.order_by(Expression.id.asc()).offset(offset).limit(limit).all()]

    expressions = (
        db.session.query(Expression)
        .options(selectinload(Expression.work), selectinload(Expression.manifestations))  # type: ignore[arg-type]
        .filter(Expression.id.in_(expr_ids))
        .all()
    )

    manifestation_ids = []
    for expr in expressions:
        for manif in expr.manifestations:  # type: ignore[attr-defined]
            manifestation_ids.append(manif.id)

    owned_items = []
    if user_id and manifestation_ids:
        owned_items = db.session.query(Item).filter(Item.owner_id == user_id, Item.manifestation_id.in_(manifestation_ids)).all()

    owned_items_map = {item.manifestation_id: item for item in owned_items}

    # Fetch user work intents for the loaded expressions
    work_ids = [expr.work_id for expr in expressions if expr.work_id]
    intents = []
    if user_id and work_ids:
        intents = db.session.query(UserWorkIntent).filter(UserWorkIntent.user_id == user_id, UserWorkIntent.work_id.in_(work_ids)).all()
    intents_map = {intent.work_id: intent for intent in intents}

    expr_map: dict[int, dict] = {}
    for expr in expressions:
        work = expr.work
        creators: list[str] = []
        if work and work.meta:
            creators = work.meta.get("creators") or work.meta.get("authors") or []
        work_title = work.title if work else "Unknown"

        owned_manifestations = []
        total_items = 0
        has_intent = work and work.id in intents_map

        for manif in expr.manifestations:  # type: ignore[attr-defined]
            owned_item = owned_items_map.get(manif.id)
            effective_cover = manif.cover_url or (manif.meta.get("cover_url") if manif.meta else None)

            if owned_item:
                if not effective_cover and owned_item.meta:
                    effective_cover = owned_item.meta.get("cover_url")

                owned_manifestations.append(
                    {
                        "manifestation_id": manif.id,
                        "item_id": owned_item.id,
                        "format": manif.meta.get("format", "Unknown") if manif.meta else "Unknown",
                        "cover_url": effective_cover,
                    }
                )
                total_items += 1
            else:
                owned_manifestations.append(
                    {
                        "manifestation_id": manif.id,
                        "item_id": None,
                        "format": manif.meta.get("format", "Unknown") if manif.meta else "Unknown",
                        "cover_url": effective_cover,
                        "intent_status": intents_map[work.id].status if has_intent else None,
                    }
                )

        expr_map[expr.id] = {
            "expression_id": expr.id,
            "content_type": expr.content_type,
            "language": expr.language,
            "work_title": work_title,
            "creators": creators,
            "owned_manifestations": owned_manifestations,
            "total_items": total_items,
        }

    # Sort by work title for consistent display
    result_data = sorted(expr_map.values(), key=lambda x: x["work_title"].lower())

    return jsonify(
        {
            "success": True,
            "data": result_data,
            "total": total_count,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count,
            },
        }
    )


@api_bp.route("/works/<int:work_id>/parts", methods=["GET"])
@optional_auth
def get_work_parts(work_id: int) -> Response | tuple[Response, int]:
    """Get the series/parts associated with a given complex work."""
    work = db.session.get(Work, work_id)
    if not work:
        return jsonify({"error": "Work not found", "code": 404}), 404

    user_id = getattr(g, "user_id", None)
    owned_items_map = {}
    if user_id:
        items = Item.query.filter_by(owner_id=user_id).all()
        for item in items:
            owned_items_map[item.manifestation_id] = item.id

    parts = []
    for wp in work.parts:  # type: ignore[attr-defined]
        part_work = wp.part

        manifestation_id = None
        cover_url = None
        item_id = None

        for expr in part_work.expressions:
            for manif in expr.manifestations:
                if not manifestation_id:
                    manifestation_id = manif.id
                    cover_url = manif.cover_url or (manif.meta.get("cover_url") if manif.meta else None)

                if manif.id in owned_items_map:
                    item_id = owned_items_map[manif.id]
                    m_cover = manif.cover_url or (manif.meta.get("cover_url") if manif.meta else None)
                    if m_cover:
                        cover_url = m_cover
                    manifestation_id = manif.id
                    break
            if item_id:
                break

        parts.append(
            {
                "part_work_id": part_work.id,
                "title": part_work.title,
                "sequence": wp.sequence,
                "manifestation_id": manifestation_id,
                "cover_url": cover_url,
                "item_id": item_id,
            }
        )

    return jsonify({"success": True, "data": sorted(parts, key=lambda x: x["sequence"])})


@api_bp.route("/works/<int:work_id>/parts", methods=["POST"])
@require_auth
@require_permission(PermissionName.WRITE_METADATA)
def add_work_part(work_id: int) -> Response | tuple[Response, int]:
    """Add a part to a complex work (series/anthology)."""
    data = request.get_json()
    if not data or "part_work_id" not in data:
        return invalid_json_payload_response()

    part_id = data["part_work_id"]
    seq = data.get("sequence", 0)

    if work_id == part_id:
        return jsonify({"error": "A work cannot be its own part", "code": 400}), 400

    container = db.session.get(Work, work_id)
    part = db.session.get(Work, part_id)

    if not container or not part:
        return jsonify({"error": "Work not found", "code": 404}), 404

    wp = WorkPart.query.filter_by(container_work_id=work_id, part_work_id=part_id).first()
    if not wp:
        wp = WorkPart(container_work_id=work_id, part_work_id=part_id, sequence=seq)
        db.session.add(wp)
    else:
        wp.sequence = seq

    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/works/<int:work_id>/parts/<int:part_id>", methods=["DELETE"])
@require_auth
@require_permission(PermissionName.WRITE_METADATA)
def remove_work_part(work_id: int, part_id: int) -> Response | tuple[Response, int]:
    """Remove a part from a complex work."""
    wp = WorkPart.query.filter_by(container_work_id=work_id, part_work_id=part_id).first()
    if wp:
        db.session.delete(wp)
        db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/works/<int:work_id>/intent", methods=["GET"])
@require_auth
def get_work_intent(work_id: int) -> Response | tuple[Response, int]:
    """Get the current user's intent for a given Conceptual Work (F1)."""
    user_id = getattr(g, "user_id", None)
    work = db.session.get(Work, work_id)
    if not work:
        return jsonify({"error": "Work not found", "code": 404}), 404

    intent = UserWorkIntent.query.filter_by(user_id=user_id, work_id=work_id).first()
    status = intent.status if intent else None
    return jsonify({"success": True, "data": {"status": status}})


@api_bp.route("/works/<int:work_id>/intent", methods=["POST"])
@require_auth
def set_work_intent(work_id: int) -> Response | tuple[Response, int]:
    """Set or update the current user's intent for a given Conceptual Work (F1)."""
    user_id = getattr(g, "user_id", None)
    work = db.session.get(Work, work_id)
    if not work:
        return jsonify({"error": "Work not found", "code": 404}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    status = data.get("status")
    if not status:
        intent = UserWorkIntent.query.filter_by(user_id=user_id, work_id=work_id).first()
        if intent:
            db.session.delete(intent)
            db.session.commit()
        return jsonify({"success": True, "data": {"status": None}})

    from app.core.taxonomy import PROGRESS_STATUSES

    if status not in PROGRESS_STATUSES:
        return jsonify({"error": f"Invalid intent status. Valid values: {list(PROGRESS_STATUSES)}", "code": 400}), 400

    intent = UserWorkIntent.query.filter_by(user_id=user_id, work_id=work_id).first()
    if intent:
        intent.status = status
    else:
        intent = UserWorkIntent(user_id=user_id, work_id=work_id, status=status)
        db.session.add(intent)

    db.session.commit()
    return jsonify({"success": True, "data": {"status": status}})


@api_bp.route("/works/<int:work_id>/intent", methods=["DELETE"])
@require_auth
def delete_work_intent(work_id: int) -> Response | tuple[Response, int]:
    """Delete the current user's intent for a given Conceptual Work (F1)."""
    user_id = getattr(g, "user_id", None)
    work = db.session.get(Work, work_id)
    if not work:
        return jsonify({"error": "Work not found", "code": 404}), 404

    intent = UserWorkIntent.query.filter_by(user_id=user_id, work_id=work_id).first()
    if intent:
        db.session.delete(intent)
        db.session.commit()

    return jsonify({"success": True, "data": {"status": None}})
