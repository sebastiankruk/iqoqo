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
from app.db.models import Expression, Item, Manifestation, Work, WorkPart, db


@api_bp.route("/works/shelf", methods=["GET"])
@require_auth
def get_user_works() -> Response:
    """
    Returns a specialized view of the user's shelf grouped by Conceptual Work.
    This resolves the F15 Complex Work/Series requirement by allowing the UI
    to display a 'Series' or 'Work' card that contains multiple manifestations.

    Supports optional query parameters:
    - q: filter by work title or creator name (case-insensitive substring match)
    - category: filter by expression content_type (e.g. 'text', 'music', 'movie')
    """
    user_id = getattr(g, "user_id", None)
    search_q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    tags_filter = request.args.get("tags")
    collections_filter = request.args.get("collections")
    genres_filter = request.args.get("genres")
    publishers_filter = request.args.get("publishers")

    tags_list = [t.strip() for t in tags_filter.split(",") if t.strip()] if tags_filter else None
    collections_list = [c.strip() for c in collections_filter.split(",") if c.strip()] if collections_filter else None
    genres_list = [gen.strip() for gen in genres_filter.split(",") if gen.strip()] if genres_filter else None
    publishers_list = [p.strip() for p in publishers_filter.split(",") if p.strip()] if publishers_filter else None

    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)

    # Base query for works owned by the user
    base_query = (
        db.session.query(Work.id)
        .join(Expression, Expression.work_id == Work.id)
        .join(Manifestation, Manifestation.expression_id == Expression.id)
        .join(Item, Item.manifestation_id == Manifestation.id)
        .filter(Item.owner_id == user_id)
    )

    if category:
        base_query = base_query.filter(Expression.content_type == category)

    if search_q:
        # Search title and creators (authors)
        # Using a pattern search for both fields
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

        base_query = base_query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
        base_query = base_query.filter(Tag.name.in_(tags_list))

    if collections_list:
        from app.db.models import UserCollection, UserCollectionItem

        base_query = base_query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
            UserCollection, UserCollectionItem.collection_id == UserCollection.id
        )
        base_query = base_query.filter(UserCollection.name.in_(collections_list), UserCollection.owner_id == user_id)

    if genres_list:
        base_query = apply_genre_filter(base_query, genres_list)

    if publishers_list:
        base_query = base_query.filter(Manifestation.publisher.in_(publishers_list))

    # Get the total count of distinct works matching the filters
    total_count = base_query.with_entities(Work.id).distinct().count()

    # Get the paginated list of work IDs
    work_ids = [row[0] for row in base_query.with_entities(Work.id, Work.title).distinct().order_by(Work.title.asc()).offset(offset).limit(limit).all()]

    items = (
        db.session.query(Item)
        .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
        .join(Manifestation, Item.manifestation_id == Manifestation.id)
        .join(Expression, Manifestation.expression_id == Expression.id)
        .filter(Item.owner_id == user_id, Expression.work_id.in_(work_ids))
        .all()
    )

    works_map: dict[int, dict] = {}
    for item in items:
        if not item.manifestation or not item.manifestation.expression or not item.manifestation.expression.work:
            continue

        expr = item.manifestation.expression
        work = expr.work

        # Re-apply category filter (redundant but safe given how we fetch items)
        if category and (expr.content_type or "").lower() != category:
            continue

        creators: list[str] = []
        if work.meta:
            creators = work.meta.get("creators") or work.meta.get("authors") or []

        if work.id not in works_map:
            works_map[work.id] = {
                "work_id": work.id,
                "title": work.title,
                "creators": creators,
                "owned_manifestations": [],
                "total_items": 0,
            }

        man_dict = next(
            (m for m in works_map[work.id]["owned_manifestations"] if m["manifestation_id"] == item.manifestation.id),
            None,
        )
        if not man_dict:
            effective_cover = None
            if item.manifestation:
                effective_cover = item.manifestation.cover_url or (
                    item.manifestation.meta.get("cover_url") if item.manifestation.meta else None
                )
            if not effective_cover and item.meta:
                effective_cover = item.meta.get("cover_url")

            works_map[work.id]["owned_manifestations"].append(
                {
                    "manifestation_id": item.manifestation.id,
                    "item_id": item.id,
                    "format": item.manifestation.meta.get("format", "Unknown") if item.manifestation.meta else "Unknown",
                    "cover_url": effective_cover,
                }
            )

        works_map[work.id]["total_items"] += 1

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
@require_auth
def get_user_expressions() -> Response:
    """
    Returns a specialized view of the user's shelf grouped by Expression.
    Allows browsing distinct variations (translations, abridgements) of works.

    Supports optional query parameters:
    - q: filter by work title or creator name (case-insensitive substring match)
    - category: filter by expression content_type (e.g. 'text', 'music', 'movie')
    """
    user_id = getattr(g, "user_id", None)
    search_q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()

    query = (
        db.session.query(Item)
        .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
        .join(Manifestation, Item.manifestation_id == Manifestation.id)
        .join(Expression, Manifestation.expression_id == Expression.id)
        .join(Work, Expression.work_id == Work.id)
        .filter(Item.owner_id == user_id)
    )

    if category:
        query = query.filter(Expression.content_type == category)

    if search_q:
        pattern = f"%{search_q}%"
        query = query.filter(
            db.or_(
                Work.title.ilike(pattern),
                db.cast(Work.meta["authors"], db.String).ilike(pattern),
                db.cast(Work.meta["creators"], db.String).ilike(pattern),
            )
        )

    # Apply taxonomy filters
    tags_filter = request.args.get("tags")
    collections_filter = request.args.get("collections")
    genres_filter = request.args.get("genres")
    publishers_filter = request.args.get("publishers")

    tags_list = [t.strip() for t in tags_filter.split(",") if t.strip()] if tags_filter else None
    collections_list = [c.strip() for c in collections_filter.split(",") if c.strip()] if collections_filter else None
    genres_list = [gen.strip() for gen in genres_filter.split(",") if gen.strip()] if genres_filter else None
    publishers_list = [p.strip() for p in publishers_filter.split(",") if p.strip()] if publishers_filter else None

    if tags_list:
        from app.db.models import ItemTag, Tag

        query = query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
        query = query.filter(Tag.name.in_(tags_list))

    if collections_list:
        from app.db.models import UserCollection, UserCollectionItem

        query = query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
            UserCollection, UserCollectionItem.collection_id == UserCollection.id
        )
        query = query.filter(UserCollection.name.in_(collections_list), UserCollection.owner_id == user_id)

    if genres_list:
        query = apply_genre_filter(query, genres_list)

    if publishers_list:
        query = query.filter(Manifestation.publisher.in_(publishers_list))

    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)

    # Base query for distinct expression IDs
    base_expr_query = query.with_entities(Expression.id).distinct()
    total_count = base_expr_query.count()

    expr_ids = [row[0] for row in base_expr_query.order_by(Expression.id.asc()).offset(offset).limit(limit).all()]

    items = (
        db.session.query(Item)
        .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
        .join(Manifestation, Item.manifestation_id == Manifestation.id)
        .join(Expression, Manifestation.expression_id == Expression.id)
        .filter(Item.owner_id == user_id, Expression.id.in_(expr_ids))
        .all()
    )

    expr_map: dict[int, dict] = {}
    for item in items:
        if not item.manifestation or not item.manifestation.expression:
            continue

        expr = item.manifestation.expression
        work = expr.work

        creators: list[str] = []
        if work and work.meta:
            creators = work.meta.get("creators") or work.meta.get("authors") or []

        work_title = work.title if work else "Unknown"

        if expr.id not in expr_map:
            expr_map[expr.id] = {
                "expression_id": expr.id,
                "content_type": expr.content_type,
                "language": expr.language,
                "work_title": work_title,
                "creators": creators,
                "owned_manifestations": [],
                "total_items": 0,
            }

        man_dict = next((m for m in expr_map[expr.id]["owned_manifestations"] if m["manifestation_id"] == item.manifestation.id), None)
        if not man_dict:
            # Cascade cover: prefer the manifestation cover, fall back to meta fields
            effective_cover = None
            if item.manifestation:
                effective_cover = item.manifestation.cover_url or (
                    item.manifestation.meta.get("cover_url") if item.manifestation.meta else None
                )
            if not effective_cover and item.meta:
                effective_cover = item.meta.get("cover_url")
            expr_map[expr.id]["owned_manifestations"].append(
                {
                    "manifestation_id": item.manifestation.id,
                    "item_id": item.id,
                    "format": item.manifestation.meta.get("format", "Unknown") if item.manifestation.meta else "Unknown",
                    "cover_url": effective_cover,
                }
            )

        expr_map[expr.id]["total_items"] += 1

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
