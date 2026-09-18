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
"""Public API endpoints for iqoqo v0.7.0.
Handles public profile retrieval, public item grids, and "check if I have it" functionality.
"""

import datetime
from typing import Any, cast

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.core.frbr_service import serialize_collection_to_rdf, stream_collection_to_rdf
from app.core.limiter import limiter
from app.db.models import Expression, Item, Manifestation, SharedCollection, User, Work, db

public_bp = Blueprint("public", __name__, url_prefix="/public")


@public_bp.after_request
def add_cors_headers(response: Response) -> Response:
    """Ensure all public endpoints provide open CORS for AI agents and Linked Data crawlers."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization"
    return response


def _negotiate_rdf_format(default_format: str = "json-ld") -> tuple[str, str]:
    """Negotiate RDF format and mimetype from Accept header and format query param.

    Returns:
        tuple[str, str]: (rdf_format, rdf_mimetype)
    """
    accept_header = request.headers.get("Accept", "")
    format_arg = request.args.get("format", "").lower()

    if "application/n-triples" in accept_header or format_arg in ("nt", "n-triples") or accept_header == "text/plain":
        return "nt", "application/n-triples"
    if "text/turtle" in accept_header or "application/x-turtle" in accept_header or format_arg == "turtle":
        return "turtle", "text/turtle"
    if "application/ld+json" in accept_header or format_arg in ("json-ld", "jsonld"):
        return "json-ld", "application/ld+json"

    if default_format == "json-ld":
        return "json-ld", "application/ld+json"
    return "turtle", "text/turtle"


def generate_rss_xml(
    title: str,
    link: str,
    description: str,
    items: list[Any],
    *,
    use_item_guid: bool = False,
) -> str:
    """Generates standard safe RSS 2.0 XML payload for collection streams.

    Args:
        title: Feed channel title.
        link: Canonical URL of the collection.
        description: Channel description.
        items: List of Item ORM objects or dicts to render as feed entries.
        use_item_guid: When True, uses the unique item ID (``iqoqo-item-{id}``) as
            the ``<guid>`` and ``/item/{id}`` as ``<link>``.  This is required for
            per-user and shared-collection feeds where multiple items may share the
            same manifestation.  Set to False (default) for global manifestation feeds.
    """
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        f"  <title>{title}</title>",
        f"  <link>{link}</link>",
        f"  <description>{description}</description>",
        f'  <lastBuildDate>{datetime.datetime.now(datetime.UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>',
    ]

    for item in items[:50]:  # Constrain feed length payload dynamically
        if isinstance(item, dict):
            item_id = item.get("id")
            title_val = item.get("title", "Untitled")
            creator = item.get("creator") or item.get("author") or "Unknown Creator"
            m_id = item.get("manifestation_id", item_id)
            pub_date_val = item.get("created_at") or datetime.datetime.now(datetime.UTC)
        else:
            item_id = item.id
            m_id = item.manifestation_id
            title_val = item.manifestation.title if item.manifestation else "Untitled"
            authors = []
            if item.manifestation:
                if item.manifestation.expression and item.manifestation.expression.work and item.manifestation.expression.work.meta:
                    authors = item.manifestation.expression.work.meta.get("authors", []) or item.manifestation.expression.work.meta.get(
                        "Authors", []
                    )
                if not authors and item.manifestation.meta:
                    authors = item.manifestation.meta.get("authors", []) or item.manifestation.meta.get("Authors", [])
            creator = ", ".join(authors) if authors else "Unknown Creator"
            pub_date_val = item.added_at or datetime.datetime.now(datetime.UTC)

        item_title = title_val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        item_desc = creator.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if isinstance(pub_date_val, str):
            pub_date = pub_date_val
        else:
            pub_date = pub_date_val.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # For user/shared feeds each entry must have a unique guid.
        # Manifestation IDs repeat across users — using item ID avoids Feedly deduplication.
        if use_item_guid and item_id:
            entry_guid = f"iqoqo-item-{item_id}"
            entry_link = f"{link.rstrip('/')}/item/{item_id}"
        else:
            entry_guid = f"iqoqo-manifestation-{m_id}"
            entry_link = f"{link.rstrip('/')}/manifestation/{m_id}"

        xml_lines.append("  <item>")
        xml_lines.append(f"    <title>{item_title}</title>")
        xml_lines.append(f"    <description>{item_desc}</description>")
        xml_lines.append(f"    <link>{entry_link}</link>")
        xml_lines.append(f'    <guid isPermaLink="false">{entry_guid}</guid>')
        xml_lines.append(f"    <pubDate>{pub_date}</pubDate>")
        xml_lines.append("  </item>")

    xml_lines.append("</channel>")
    xml_lines.append("</rss>")
    return "\n".join(xml_lines)


def fetch_global_fresh_arrivals(limit: int = 50, level: str = "manifestations") -> list[Any]:
    """Fetch global fresh arrivals with granular level grouping."""
    if level not in ("manifestations", "expressions", "works"):
        level = "manifestations"
    if level == "works":
        if db.engine.dialect.name == "postgresql":
            subq = (
                select(Item.id, Item.updated_at)
                .join(User, Item.owner_id == User.id)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
                .where(Item.is_hidden.is_(False), User.visibility == "public", Item.status != "wish_list")
                .distinct(Work.id)
                .order_by(Work.id, Item.updated_at.desc())
                .subquery()
            )
            top_ids_stmt = select(subq.c.id).order_by(subq.c.updated_at.desc()).limit(limit)
            item_ids = list(db.session.execute(top_ids_stmt).scalars().all())
        else:
            rn = func.row_number().over(partition_by=Work.id, order_by=Item.updated_at.desc()).label("rn")
            subq = (
                select(Item.id, Item.updated_at, rn)
                .join(User, Item.owner_id == User.id)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
                .where(Item.is_hidden.is_(False), User.visibility == "public", Item.status != "wish_list")
                .subquery()
            )
            top_ids_stmt = select(subq.c.id).where(subq.c.rn == 1).order_by(subq.c.updated_at.desc()).limit(limit)
            item_ids = list(db.session.execute(top_ids_stmt).scalars().all())

        if not item_ids:
            return []
        items_stmt = (
            select(Item)
            .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
            .where(Item.id.in_(item_ids))
        )
        items_map = {item.id: item for item in db.session.execute(items_stmt).scalars().all()}
        return [items_map[iid] for iid in item_ids if iid in items_map]

    if level == "expressions":
        if db.engine.dialect.name == "postgresql":
            subq = (
                select(Item.id, Item.updated_at)
                .join(User, Item.owner_id == User.id)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .where(Item.is_hidden.is_(False), User.visibility == "public", Item.status != "wish_list")
                .distinct(Expression.id)
                .order_by(Expression.id, Item.updated_at.desc())
                .subquery()
            )
            top_ids_stmt = select(subq.c.id).order_by(subq.c.updated_at.desc()).limit(limit)
            item_ids = list(db.session.execute(top_ids_stmt).scalars().all())
        else:
            rn = func.row_number().over(partition_by=Expression.id, order_by=Item.updated_at.desc()).label("rn")
            subq = (
                select(Item.id, Item.updated_at, rn)
                .join(User, Item.owner_id == User.id)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .where(Item.is_hidden.is_(False), User.visibility == "public", Item.status != "wish_list")
                .subquery()
            )
            top_ids_stmt = select(subq.c.id).where(subq.c.rn == 1).order_by(subq.c.updated_at.desc()).limit(limit)
            item_ids = list(db.session.execute(top_ids_stmt).scalars().all())

        if not item_ids:
            return []
        items_stmt = (
            select(Item)
            .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
            .where(Item.id.in_(item_ids))
        )
        items_map = {item.id: item for item in db.session.execute(items_stmt).scalars().all()}
        return [items_map[iid] for iid in item_ids if iid in items_map]

    if db.engine.dialect.name == "postgresql":
        subq = (
            select(Item.id, Item.updated_at)
            .join(User, Item.owner_id == User.id)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .where(Item.is_hidden.is_(False), User.visibility == "public", Item.status != "wish_list")
            .distinct(Manifestation.id)
            .order_by(Manifestation.id, Item.updated_at.desc())
            .subquery()
        )
        top_ids_stmt = select(subq.c.id).order_by(subq.c.updated_at.desc()).limit(limit)
        item_ids = list(db.session.execute(top_ids_stmt).scalars().all())
    else:
        rn = func.row_number().over(partition_by=Manifestation.id, order_by=Item.updated_at.desc()).label("rn")
        subq = (
            select(Item.id, Item.updated_at, rn)
            .join(User, Item.owner_id == User.id)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .where(Item.is_hidden.is_(False), User.visibility == "public", Item.status != "wish_list")
            .subquery()
        )
        top_ids_stmt = select(subq.c.id).where(subq.c.rn == 1).order_by(subq.c.updated_at.desc()).limit(limit)
        item_ids = list(db.session.execute(top_ids_stmt).scalars().all())

    if not item_ids:
        return []
    items_stmt = (
        select(Item)
        .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
        .where(Item.id.in_(item_ids))
    )
    items_map = {item.id: item for item in db.session.execute(items_stmt).scalars().all()}
    return [items_map[iid] for iid in item_ids if iid in items_map]


def fetch_user_public_collection(username: str, limit: int = 50) -> list[Any]:
    """Fetch user public collection with eager loading across all FRBR tiers."""
    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalar_one_or_none()
    if not user:
        return []
    stmt = (
        select(Item)
        .options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work))
        .where(Item.owner_id == user.id, Item.is_hidden.is_(False))
        .order_by(Item.updated_at.desc())
        .limit(limit)
    )
    return list(db.session.execute(stmt).scalars().unique().all())


def fetch_shared_collection_by_token(token: str, limit: int = 50) -> list[Any]:
    """Fetch items from a shared collection by token with eager loading across all FRBR tiers."""
    stmt = select(SharedCollection).where(SharedCollection.share_token == token)
    collection = db.session.execute(stmt).scalar_one_or_none()
    if not collection:
        return []
    if collection.is_expired:
        return []
    user = db.session.get(User, collection.user_id)
    if not user:
        return []

    query = select(Item).where(Item.owner_id == user.id, Item.is_hidden.is_(False))
    filters = collection.filters

    if "status" in filters:
        status_val = filters["status"]
        query = query.where(or_(Item.status == status_val, Item.collection_status == status_val))

    if "tags" in filters:
        query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
        query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
        tags_list = filters["tags"]
        if tags_list:
            query = query.where(Expression.content_type.in_(tags_list))

    if "query" in filters:
        search_query = filters["query"]
        if search_query:
            if "tags" not in filters:
                query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
                query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
            query = query.outerjoin(Work, Expression.work_id == Work.id)
            query = query.where(
                or_(
                    Work.title.ilike(f"%{search_query}%"),
                    Manifestation.isbn13 == search_query,
                    Manifestation.upc == search_query,
                    db.cast(Work.meta, db.String).ilike(f"%{search_query}%"),
                    db.cast(Manifestation.meta, db.String).ilike(f"%{search_query}%"),
                )
            )

    query = query.order_by(Item.updated_at.desc()).limit(limit)
    return list(
        db.session.execute(query.options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work)))
        .scalars()
        .unique()
        .all()
    )


@public_bp.route("/feed.xml", methods=["GET"])
@limiter.limit("60 per minute")
def global_fresh_feed():
    """Exposes global raw manifestation additions supporting granular FRBR level filtering."""
    view_filter = request.args.get("view", "manifestations")  # manifestations | expressions | works
    items = fetch_global_fresh_arrivals(limit=50, level=view_filter)

    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    rss_data = generate_rss_xml(
        title=f"iqoqo Fresh Arrivals - {view_filter.capitalize()}",
        link=base_url,
        description="Live tracking stream of global physical catalog updates.",
        items=items,
    )
    return Response(rss_data, mimetype="application/rss+xml", headers={"Content-Type": "application/rss+xml; charset=utf-8"})


@public_bp.route("/u/<string:username>/feed.xml", methods=["GET"])
@limiter.limit("60 per minute")
def user_collection_feed(username: str):
    """Exposes personal collection feed streams."""
    items = fetch_user_public_collection(username=username, limit=50)
    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    rss_data = generate_rss_xml(
        title=f"{username}'s Library Feed",
        link=f"{base_url}/u/{username}",
        description=f"Live feed of items curated by user {username}.",
        items=items,
        use_item_guid=True,
    )
    return Response(rss_data, mimetype="application/rss+xml", headers={"Content-Type": "application/rss+xml; charset=utf-8"})


@public_bp.route("/share/<string:token>/feed.xml", methods=["GET"])
@limiter.limit("60 per minute")
def shared_collection_feed(token: str):
    """Exposes public shared collection feed streams via safe access token lookup."""
    items = fetch_shared_collection_by_token(token=token, limit=50)
    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    rss_data = generate_rss_xml(
        title="Shared Collection Catalog Feed",
        link=f"{base_url}/share/{token}",
        description="Live tracking feed for this specific shared collection space.",
        items=items,
        use_item_guid=True,
    )
    return Response(rss_data, mimetype="application/rss+xml", headers={"Content-Type": "application/rss+xml; charset=utf-8"})


@public_bp.route("/u/<string:username>", methods=["GET"])
def get_public_profile(username: str):
    """Retrieve a user's public profile stats and basic info."""
    stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(stmt).scalar_one_or_none()

    if not user:
        return jsonify({"error": "Public profile not found or user has disabled public sharing."}), 404

    count_stmt = select(func.count(Item.id)).where(Item.owner_id == user.id, Item.is_hidden.is_(False))  # pylint: disable=not-callable
    item_count = db.session.execute(count_stmt).scalar()

    return jsonify(
        {
            "success": True,
            "data": {
                "username": user.public_username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "bio": user.bio,
                "public_item_count": item_count,
            },
        }
    )


@public_bp.route("/u/<string:username>/items", methods=["GET"])
def get_public_items(username: str):
    """Retrieve public items for a user."""
    accept_header = request.headers.get("Accept", "")
    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    format_arg = request.args.get("format", "").lower()
    is_stream = request.args.get("stream", "").lower() in ("true", "1")

    # Content negotiation for RDF formats (JSON-LD, Turtle, N-Triples)
    rdf_format: str | None = None
    rdf_mimetype: str = ""

    if "application/n-triples" in accept_header or format_arg in ("nt", "n-triples") or accept_header == "text/plain":
        rdf_format = "nt"
        rdf_mimetype = "application/n-triples"
    elif "application/ld+json" in accept_header or format_arg in ("json-ld", "jsonld"):
        rdf_format = "json-ld"
        rdf_mimetype = "application/ld+json"
    elif "text/turtle" in accept_header or "application/x-turtle" in accept_header or format_arg == "turtle":
        rdf_format = "turtle"
        rdf_mimetype = "text/turtle"

    if rdf_format:
        limit_val = request.args.get("limit", 100, type=int)
        items = fetch_user_public_collection(username=username, limit=limit_val)
        collection_uri = f"{base_url}/u/{username}"
        if is_stream:
            return Response(
                stream_with_context(stream_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)),
                mimetype=rdf_mimetype,
                headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
            )
        rdf_payload = serialize_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)
        return Response(rdf_payload, mimetype=rdf_mimetype, headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"})

    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalar_one_or_none()
    if not user:
        return jsonify({"error": "User not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 24, type=int), 100)

    stmt = (
        select(Item)
        .options(selectinload(Item.manifestation))
        .where(Item.owner_id == user.id, Item.is_hidden.is_(False))
        .order_by(Item.updated_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    items = list(db.session.execute(stmt).scalars().all())

    total_stmt = select(func.count(Item.id)).where(Item.owner_id == user.id, Item.is_hidden.is_(False))  # pylint: disable=not-callable
    total = db.session.execute(total_stmt).scalar()

    return jsonify(
        {
            "success": True,
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "manifestation_id": item.manifestation_id,
                        "status": item.status,
                        "collection_status": item.collection_status,
                        "title": item.manifestation.title,
                        "authors": item.manifestation.meta.get("authors", []) if item.manifestation.meta else [],
                        "cover_url": item.manifestation.cover_url
                        or (item.manifestation.meta.get("cover_url") if item.manifestation.meta else None),
                        "added_at": item.added_at.isoformat() if item.added_at else None,
                    }
                    for item in items
                ],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page if total else 0,
            },
        }
    )


@public_bp.route("/share/<string:token>", methods=["GET"])
def get_shared_collection(token: str):
    """Retrieve items based on a specific SharedCollection token filters."""
    accept_header = request.headers.get("Accept", "")
    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    format_arg = request.args.get("format", "").lower()
    is_stream = request.args.get("stream", "").lower() in ("true", "1")

    # Content negotiation for RDF formats (JSON-LD, Turtle, N-Triples)
    rdf_format: str | None = None
    rdf_mimetype: str = ""

    if "application/n-triples" in accept_header or format_arg in ("nt", "n-triples") or accept_header == "text/plain":
        rdf_format = "nt"
        rdf_mimetype = "application/n-triples"
    elif "application/ld+json" in accept_header or format_arg in ("json-ld", "jsonld"):
        rdf_format = "json-ld"
        rdf_mimetype = "application/ld+json"
    elif "text/turtle" in accept_header or "application/x-turtle" in accept_header or format_arg == "turtle":
        rdf_format = "turtle"
        rdf_mimetype = "text/turtle"

    if rdf_format:
        limit_val = request.args.get("limit", 100, type=int)
        items = fetch_shared_collection_by_token(token=token, limit=limit_val)
        collection_uri = f"{base_url}/share/{token}"
        if is_stream:
            return Response(
                stream_with_context(stream_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)),
                mimetype=rdf_mimetype,
                headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
            )
        rdf_payload = serialize_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)
        return Response(rdf_payload, mimetype=rdf_mimetype, headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"})

    stmt = select(SharedCollection).where(SharedCollection.share_token == token)
    collection = db.session.execute(stmt).scalar_one_or_none()
    if not collection:
        return jsonify({"error": "Collection not found"}), 404
    if collection.is_expired:
        return jsonify({"error": "Collection not found"}), 404

    user = db.session.get(User, collection.user_id)
    if not user:
        return jsonify({"error": "Author not found"}), 404

    query = select(Item).where(Item.owner_id == user.id, Item.is_hidden.is_(False))

    filters = collection.filters

    if "status" in filters:
        # The frontend sends 'status' which could map to either Item.status or Item.collection_status
        status_val = filters["status"]
        query = query.where(or_(Item.status == status_val, Item.collection_status == status_val))

    if "tags" in filters:
        # tags array maps to Expression.content_type
        # We need to join Expression if it's not already joined
        query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
        query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
        tags_list = filters["tags"]
        if tags_list:
            query = query.where(Expression.content_type.in_(tags_list))

    if "query" in filters:
        search_query = filters["query"]
        if search_query:
            # Join Work and Manifestation if not joined
            if "tags" not in filters:
                query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
                query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
            query = query.outerjoin(Work, Expression.work_id == Work.id)

            query = query.where(
                or_(
                    Work.title.ilike(f"%{search_query}%"),
                    Manifestation.isbn13 == search_query,
                    Manifestation.upc == search_query,
                    db.cast(Work.meta, db.String).ilike(f"%{search_query}%"),
                    db.cast(Manifestation.meta, db.String).ilike(f"%{search_query}%"),
                )
            )

    items = list(db.session.execute(query.options(selectinload(Item.manifestation))).scalars().all())

    items_list = [
        {
            "id": item.id,
            "manifestation_id": item.manifestation_id,
            "status": item.status,
            "collection_status": item.collection_status,
            "title": item.manifestation.title,
            "authors": item.manifestation.meta.get("authors", []) if item.manifestation.meta else [],
            "cover_url": item.manifestation.cover_url or (item.manifestation.meta.get("cover_url") if item.manifestation.meta else None),
        }
        for item in items
    ]

    is_wish_list = False
    if "status" in filters:
        status_val = filters["status"]
        if status_val in ("wish_list", "want_to_read", "want_to_listen", "want_to_watch", "want_to_play"):
            is_wish_list = True

    if is_wish_list:
        from app.api.items import get_virtual_items

        virtual_items = get_virtual_items(
            user_id=user.id,
            statuses_filter=filters["status"],
            category_list=filters.get("tags"),
            format_list=None,
            q=filters.get("query"),
            publishers_list=None,
            missing_cover=False,
            missing_id=False,
            genres_list=None,
        )
        # Add virtual items (they have a compatible schema)
        for vi in virtual_items:
            items_list.append(
                {
                    "id": vi.get("id"),
                    "manifestation_id": vi.get("manifestation_id"),
                    "status": vi.get("status"),
                    "collection_status": vi.get("collection_status"),
                    "title": vi.get("title"),
                    "authors": vi.get("authors", []),
                    "cover_url": vi.get("cover_url"),
                }
            )

    return jsonify(
        {
            "success": True,
            "data": {
                "collection_name": collection.name,
                "collection_description": collection.description,
                "author": user.public_username or user.display_name or "A user",
                "items": items_list,
            },
        }
    )


@public_bp.route("/u/<string:username>/check", methods=["POST"])
def check_inventory(username: str):
    """
    Smart check if a user has a specific item.
    Returns Item if owned, otherwise Manifestation if exists in catalog.
    """
    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalar_one_or_none()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    query_term = data.get("query", "").strip()
    if not query_term:
        return jsonify({"error": "Query parameter is required"}), 400

    # 1. Search for Item owned by user
    # Join Item -> Manifestation -> Expression -> Work
    item_stmt = (
        select(Item)
        .join(Manifestation)
        .join(Manifestation.expression)
        .join(Work)
        .where(
            Item.owner_id == user.id,
            Item.is_hidden.is_(False),
            or_(
                Work.title.ilike(f"%{query_term}%"),
                Manifestation.isbn13 == query_term,
                Manifestation.upc == query_term,
                db.cast(Manifestation.meta, db.String).ilike(f"%{query_term}%"),
            ),
        )
        .order_by(Work.title.asc())
    )
    items = db.session.execute(item_stmt.options(selectinload(Item.manifestation)).limit(5)).scalars().all()

    if items:
        return jsonify(
            {
                "success": True,
                "data": [
                    {
                        "type": "item",
                        "id": item.id,
                        "manifestation_id": item.manifestation_id,
                        "title": item.manifestation.title,
                        "status": item.status,
                        "collection_status": item.collection_status,
                        "cover_url": item.manifestation.cover_url,
                    }
                    for item in items
                ],
            }
        )

    # 2. If no item, search for Manifestation in catalog
    manifestation_stmt = (
        select(Manifestation)
        .join(Manifestation.expression)
        .join(Work)
        .where(
            or_(
                Work.title.ilike(f"%{query_term}%"),
                Manifestation.isbn13 == query_term,
                Manifestation.upc == query_term,
                db.cast(Manifestation.meta, db.String).ilike(f"%{query_term}%"),
            )
        )
        .order_by(Work.title.asc())
    )
    manifestations = db.session.execute(manifestation_stmt.limit(5)).scalars().all()

    if manifestations:
        return jsonify(
            {
                "success": True,
                "data": [
                    {
                        "type": "manifestation",
                        "id": m.id,
                        "title": m.title,
                        "publisher": m.publisher,
                        "cover_url": m.cover_url,
                    }
                    for m in manifestations
                ],
            }
        )

    return jsonify({"success": True, "data": []})


def generate_sitemap_xml(base_url: str) -> str:
    """Generate an XML sitemap listing public user profiles, shared collections, and catalog manifestations."""
    # Public users
    users = db.session.execute(select(User.public_username).where(User.visibility == "public")).scalars().all()

    # Active shared collections (not expired)
    now = datetime.datetime.now(datetime.UTC)
    shares = (
        db.session.execute(
            select(SharedCollection.share_token).where(or_(SharedCollection.expires_at.is_(None), SharedCollection.expires_at > now))
        )
        .scalars()
        .all()
    )

    # Public catalog manifestations (bounded up to 50,000 URLs)
    manifestations = db.session.execute(select(Manifestation.id).limit(50000)).scalars().all()

    urls: list[str] = []
    for username in users:
        if not username:
            continue
        loc_profile = f"{base_url}/u/{username}"
        loc_api = f"{base_url}/api/public/u/{username}/items"
        urls.append(f"  <url><loc>{loc_profile}</loc><changefreq>weekly</changefreq></url>")
        urls.append(f"  <url><loc>{loc_api}</loc><changefreq>weekly</changefreq></url>")

    for token in shares:
        if not token:
            continue
        loc_share = f"{base_url}/share/{token}"
        loc_api_share = f"{base_url}/api/public/share/{token}"
        urls.append(f"  <url><loc>{loc_share}</loc><changefreq>monthly</changefreq></url>")
        urls.append(f"  <url><loc>{loc_api_share}</loc><changefreq>monthly</changefreq></url>")

    for mid in manifestations:
        loc_m = f"{base_url}/manifestation/{mid}"
        urls.append(f"  <url><loc>{loc_m}</loc><changefreq>monthly</changefreq></url>")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
    )


@public_bp.route("/sitemap.xml", methods=["GET"])
@limiter.limit("60 per minute")
def sitemap() -> Response:
    """Generate an XML sitemap listing public user profiles, shared collections, and catalog items."""
    base_url = request.url_root.rstrip("/")
    xml = generate_sitemap_xml(base_url)
    resp = Response(xml, content_type="application/xml; charset=utf-8")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


@public_bp.route("/manifestations/<int:manifestation_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_manifestation(manifestation_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for a Manifestation entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples.
    """
    stmt = (
        select(Manifestation)
        .options(
            joinedload(Manifestation.expression).joinedload(Expression.work),
        )
        .where(Manifestation.id == manifestation_id)
    )
    manifestation = db.session.execute(stmt).scalars().first()
    if not manifestation:
        return jsonify({"error": "Manifestation not found"}), 404

    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/manifestation/{manifestation.id}"
    rdf_payload = serialize_collection_to_rdf(
        [manifestation],
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/works/<int:work_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_work(work_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for a Work entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples,
    linking expressions and manifestations embodied by the work.
    """
    stmt = (
        select(Work)
        .options(
            selectinload(cast(Any, Work.expressions)).selectinload(cast(Any, Expression.manifestations)),
        )
        .where(Work.id == work_id)
    )
    work = db.session.execute(stmt).scalars().first()
    if not work:
        return jsonify({"error": "Work not found"}), 404

    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/work/{work.id}"
    expressions_list: list[Any] = getattr(work, "expressions", [])
    manifestations = [m for expr in expressions_list for m in getattr(expr, "manifestations", [])]
    items_to_serialize: list[Any] = manifestations if manifestations else [work]

    rdf_payload = serialize_collection_to_rdf(
        items_to_serialize,
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/expressions/<int:expression_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_expression(expression_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for an Expression entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples.
    """
    stmt = (
        select(Expression)
        .options(
            joinedload(Expression.work),
            selectinload(cast(Any, Expression.manifestations)),
        )
        .where(Expression.id == expression_id)
    )
    expression = db.session.execute(stmt).scalars().first()
    if not expression:
        return jsonify({"error": "Expression not found"}), 404

    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/expression/{expression.id}"
    expr_manifestations: list[Any] = list(getattr(expression, "manifestations", []))
    items_to_serialize: list[Any] = expr_manifestations if expr_manifestations else [expression]

    rdf_payload = serialize_collection_to_rdf(
        items_to_serialize,
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/items/<int:item_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_item(item_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for an Item entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples.
    Only non-hidden items are accessible publicly.
    """
    stmt = (
        select(Item)
        .options(
            joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work),
        )
        .where(Item.id == item_id, Item.is_hidden.is_(False))
    )
    item = db.session.execute(stmt).scalars().first()
    if not item:
        return jsonify({"error": "Item not found"}), 404

    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/item/{item.id}"
    rdf_payload = serialize_collection_to_rdf(
        [item],
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
