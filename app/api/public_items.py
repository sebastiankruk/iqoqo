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
"""Public item, feed, shared collection, and sitemap endpoints for iqoqo v0.7.0.

Handles public collection feeds, item grids, shared collection tokens, and sitemaps.
"""

import datetime
from typing import Any

import sqlalchemy as sa
from flask import Response, current_app, g, has_request_context, jsonify, request, stream_with_context
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from app.api.decorators import optional_auth
from app.api.public_rdf import MAX_SHARED_COLLECTION_LIMIT, _parse_safe_rdf_limit, public_bp
from app.core.frbr_service import serialize_collection_to_rdf, stream_collection_to_rdf
from app.core.iri import get_lod_base_url
from app.core.limiter import limiter
from app.core.search_service import (
    SearchService,
    _meta_text,
    build_ilike_search_clause,
    escape_ilike_term,
    normalize_diacritics,
)
from app.db.contributions import Contributor, WorkContribution
from app.db.models import Expression, Item, Manifestation, SharedCollection, User, UserWorkIntent, Work, db


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


def fetch_user_public_collection(username: str, limit: int = 50, stream: bool = False) -> list[Any] | Any:
    """Fetch user public collection with eager loading across all FRBR tiers.

    Args:
        username: The public username to fetch items for.
        limit: Maximum number of items to return.
        stream: If True, returns an iterator instead of a list for memory-efficient streaming.

    Returns:
        List of items or iterator if stream=True.
    """
    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalar_one_or_none()
    if not user:
        return [] if not stream else iter([])
    stmt = (
        select(Item)
        .options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work))
        .where(Item.owner_id == user.id, Item.is_hidden.is_(False))
        .order_by(Item.updated_at.desc())
        .limit(limit)
    )
    if stream:
        # Return an iterator for memory-efficient streaming
        return db.session.execute(stmt).scalars().yield_per(50)
    return list(db.session.execute(stmt).scalars().unique().all())


def _resolve_shared_visibilities(collection: SharedCollection, viewer_id: Any = None) -> tuple[tuple[str, ...], bool, bool]:
    """Resolve permitted Item visibilities and cache privacy for a shared collection.

    Implements Token Scope + Friend Bonus:
    - ``all`` -> ``("public", "friends_only", "shared", "private")``, ``include_hidden=True``, private cache
    - ``friends_and_public`` -> ``("public", "friends_only", "shared")``, ``include_hidden=False``, private cache
    - ``public_only`` (default) -> owner or accepted friend receives Friend Bonus
      (``("public", "friends_only", "shared")``, private cache); others receive ``("public",)``, public cache.
    """
    from app.core.friend_service import is_friend_of

    filters = collection.filters if isinstance(collection.filters, dict) else {}
    scope = filters.get("visibility_scope", "public_only")
    if scope == "all":
        return (("public", "friends_only", "shared", "private"), True, True)
    if scope == "friends_and_public":
        return (("public", "friends_only", "shared"), False, True)
    if viewer_id is not None and is_friend_of(viewer_id, collection.user_id):
        return (("public", "friends_only", "shared"), False, True)
    return (("public",), False, False)


def _build_shared_visibility_predicate(allowed_vis: tuple[str, ...], include_hidden: bool) -> Any:
    """Build SQLAlchemy WHERE predicate enforcing resolved visibility and hidden state."""
    if include_hidden:
        return or_(Item.visibility.in_(allowed_vis), Item.visibility.is_(None))
    non_public_vis = tuple(v for v in allowed_vis if v != "public")
    if "public" in allowed_vis and non_public_vis:
        return or_(
            sa.and_(Item.visibility == "public", Item.is_hidden.is_(False)),
            Item.visibility.in_(non_public_vis),
        )
    if "public" in allowed_vis:
        return sa.and_(Item.visibility == "public", Item.is_hidden.is_(False))
    if non_public_vis:
        return Item.visibility.in_(non_public_vis)
    return sa.false()


def _apply_share_cache_headers(headers: dict[str, str], is_private_cache: bool) -> dict[str, str]:
    """Set Cache-Control and Vary headers protecting private or friend-bonus share responses."""
    updated = dict(headers)
    updated["Vary"] = "Authorization, Cookie"
    if is_private_cache:
        updated["Cache-Control"] = "private, no-store"
    else:
        updated["Cache-Control"] = "public, max-age=300"
    return updated


def is_shared_collection_private_cache(token: str, viewer_id: Any = None) -> bool:
    """Return True when responses for ``token`` and ``viewer_id`` must bypass shared public caches."""
    resolved_viewer = viewer_id if viewer_id is not None else (getattr(g, "user_id", None) if has_request_context() else None)
    collection = db.session.execute(select(SharedCollection).where(SharedCollection.share_token == token)).scalar_one_or_none()
    if not collection or collection.is_expired:
        return False
    _, _, is_private_cache = _resolve_shared_visibilities(collection, viewer_id=resolved_viewer)
    return is_private_cache


def fetch_shared_collection_with_cache_policy(
    token: str,
    limit: int = 50,
    stream: bool = False,
    offset: int = 0,
    viewer_id: Any = None,
) -> tuple[list[Any] | Any, bool]:
    """Fetch shared collection items and whether the response must use private caching in one pass."""
    resolved_viewer = viewer_id if viewer_id is not None else (getattr(g, "user_id", None) if has_request_context() else None)
    stmt = select(SharedCollection).where(SharedCollection.share_token == token)
    collection = db.session.execute(stmt).scalar_one_or_none()
    if not collection or collection.is_expired:
        return ([] if not stream else iter([])), False
    user = db.session.get(User, collection.user_id)
    if not user:
        return ([] if not stream else iter([])), False

    allowed_vis, include_hidden, is_private_cache = _resolve_shared_visibilities(collection, viewer_id=resolved_viewer)
    query = select(Item).where(Item.owner_id == user.id, _build_shared_visibility_predicate(allowed_vis, include_hidden))
    filters = collection.filters

    if "status" in filters:
        status_val = filters["status"]
        statuses = status_val if isinstance(status_val, list) else [status_val]
        statuses = [s for s in statuses if isinstance(s, str) and s]
        if statuses:
            query = query.where(or_(Item.status.in_(statuses), Item.collection_status.in_(statuses)))
        else:
            query = query.where(sa.false())

    if "tags" in filters:
        query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
        query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
        tags_list = filters["tags"]
        if tags_list:
            query = query.where(Expression.content_type.in_(tags_list))

    pg_search_paginated = False
    if "query" in filters:
        search_query = filters["query"]
        if search_query:
            if db.engine.dialect.name == "postgresql":
                statuses_list = statuses if "status" in filters else None
                tags_list = filters.get("tags")
                _, results = SearchService.search_items(
                    q=search_query,
                    user_id=user.id,
                    limit=limit,
                    offset=max(0, offset),
                    statuses=statuses_list,
                    category=tags_list,
                    owner_only=True,
                    include_hidden=include_hidden or any(v != "public" for v in allowed_vis),
                    visibility=list(allowed_vis),
                )
                item_ids = [r["item_id"] for r in results]
                if not item_ids:
                    return ([] if not stream else iter([])), is_private_cache
                query = query.where(Item.id.in_(item_ids))
                pg_search_paginated = True
            else:
                if "tags" not in filters:
                    query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
                    query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
                query = query.outerjoin(Work, Expression.work_id == Work.id)
                query = query.where(build_ilike_search_clause(search_query))

    query = query.order_by(Item.updated_at.desc())
    if not pg_search_paginated:
        query = query.limit(limit).offset(max(0, offset))

    if stream:
        # Return an iterator for memory-efficient streaming
        return (
            db.session.execute(
                query.options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work))
            )
            .scalars()
            .yield_per(50)
        ), is_private_cache

    return (
        list(
            db.session.execute(
                query.options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work))
            )
            .scalars()
            .unique()
            .all()
        ),
        is_private_cache,
    )


def fetch_shared_collection_by_token(
    token: str,
    limit: int = 50,
    stream: bool = False,
    offset: int = 0,
    viewer_id: Any = None,
    _cache_policy_out: dict[str, bool] | None = None,
) -> list[Any] | Any:
    """Fetch items from a shared collection by token with eager loading across all FRBR tiers.

    Args:
        token: The share token to look up.
        limit: Maximum number of items to return.
        stream: If True, returns an iterator instead of a list for memory-efficient streaming.
        offset: SQL offset for paginated queries.
        viewer_id: Optional authenticated caller ID used for Friend Bonus resolution.
        _cache_policy_out: Optional dict populated with ``{"is_private_cache": bool}`` to avoid a second DB lookup.

    Returns:
        List of items or iterator if stream=True.
    """
    items, is_private_cache = fetch_shared_collection_with_cache_policy(
        token=token,
        limit=limit,
        stream=stream,
        offset=offset,
        viewer_id=viewer_id,
    )
    if _cache_policy_out is not None:
        _cache_policy_out["is_private_cache"] = is_private_cache
    return items


@public_bp.route("/feed.xml", methods=["GET"])
@limiter.limit("60 per minute")
def global_fresh_feed():
    """Exposes global raw manifestation additions supporting granular FRBR level filtering."""
    view_filter = request.args.get("view", "manifestations")  # manifestations | expressions | works
    items = fetch_global_fresh_arrivals(limit=50, level=view_filter)

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rss_data = generate_rss_xml(
        title=f"iqoqo Fresh Arrivals - {view_filter.capitalize()}",
        link=base_url,
        description="Live tracking stream of global physical catalog updates.",
        items=items,
    )
    return Response(
        rss_data,
        mimetype="application/rss+xml",
        headers={"Content-Type": "application/rss+xml; charset=utf-8", "Cache-Control": "public, max-age=300"},
    )


@public_bp.route("/u/<string:username>/feed.xml", methods=["GET"])
@limiter.limit("60 per minute")
def user_collection_feed(username: str):
    """Exposes personal collection feed streams."""
    items = fetch_user_public_collection(username=username, limit=50)
    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rss_data = generate_rss_xml(
        title=f"{username}'s Library Feed",
        link=f"{base_url}/u/{username}",
        description=f"Live feed of items curated by user {username}.",
        items=items,
        use_item_guid=True,
    )
    return Response(
        rss_data,
        mimetype="application/rss+xml",
        headers={"Content-Type": "application/rss+xml; charset=utf-8", "Cache-Control": "public, max-age=300"},
    )


@public_bp.route("/share/<string:token>/feed.xml", methods=["GET"])
@optional_auth
@limiter.limit("60 per minute")
def shared_collection_feed(token: str):
    """Exposes public shared collection feed streams via safe access token lookup."""
    viewer_id = getattr(g, "user_id", None)
    cache_policy_box: dict[str, bool] = {}
    items = fetch_shared_collection_by_token(
        token=token,
        limit=50,
        viewer_id=viewer_id,
        _cache_policy_out=cache_policy_box,
    )
    is_private_cache = (
        cache_policy_box["is_private_cache"]
        if "is_private_cache" in cache_policy_box
        else is_shared_collection_private_cache(token, viewer_id=viewer_id)
    )
    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rss_data = generate_rss_xml(
        title="Shared Collection Catalog Feed",
        link=f"{base_url}/share/{token}",
        description="Live tracking feed for this specific shared collection space.",
        items=items,
        use_item_guid=True,
    )
    return Response(
        rss_data,
        mimetype="application/rss+xml",
        headers=_apply_share_cache_headers({"Content-Type": "application/rss+xml; charset=utf-8"}, is_private_cache),
    )


@public_bp.route("/u/<string:username>/items", methods=["GET"])
@optional_auth
@limiter.limit("60 per minute")
def get_public_items(username: str):
    """Retrieve public items for a user."""
    accept_header = request.headers.get("Accept", "")
    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    format_arg = request.args.get("format", "").lower()
    is_stream = request.args.get("stream", "").lower() in ("true", "1")

    user_stmt = select(User).where(func.lower(User.public_username) == username.lower())
    user = db.session.execute(user_stmt).scalar_one_or_none()
    if not user:
        return jsonify({"error": "User not found"}), 404

    viewer_id = getattr(g, "user_id", None)
    is_owner = bool(viewer_id and str(viewer_id) == str(user.id))

    from app.core.friend_service import is_friend_of

    is_friend = is_friend_of(viewer_id, user.id) if viewer_id else False

    if user.visibility == "private" and not is_owner:
        return jsonify({"error": "User not found"}), 404
    if user.visibility == "friends_only" and not (is_owner or is_friend):
        return jsonify({"error": "User not found"}), 404

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
        limit_val = _parse_safe_rdf_limit()
        items = fetch_user_public_collection(username=username, limit=limit_val, stream=is_stream)
        collection_uri = f"{base_url}/u/{username}"
        if is_stream:
            return Response(
                stream_with_context(stream_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)),
                mimetype=rdf_mimetype,
                headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
            )
        # For non-streaming, convert iterator to list if needed
        if not isinstance(items, list):
            items = list(items)
        rdf_payload = serialize_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)
        return Response(rdf_payload, mimetype=rdf_mimetype, headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"})

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 24, type=int), 100)

    if is_owner or is_friend:
        visibility_cond = or_(Item.is_hidden.is_(False), Item.visibility.in_(["public", "friends_only", "shared"]))
    else:
        visibility_cond = Item.is_hidden.is_(False)

    stmt = (
        select(Item)
        .options(selectinload(Item.manifestation))
        .where(Item.owner_id == user.id, visibility_cond)
        .order_by(Item.updated_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    items = list(db.session.execute(stmt).scalars().all())

    total_stmt = select(func.count(Item.id)).where(Item.owner_id == user.id, visibility_cond)  # pylint: disable=not-callable
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


def _serialize_shared_collection_item(item: Item) -> dict[str, Any]:
    """Serialize a shared collection Item with top-level FRBR F2/F3 pressing metadata."""
    m = item.manifestation
    m_meta = (m.meta if m and isinstance(m.meta, dict) else None) or {}
    expr = m.expression if m else None
    work = expr.work if expr else None

    authors = (work.meta.get("authors") if work and isinstance(work.meta, dict) else None) or m_meta.get("authors") or []
    cover_url = (m.cover_url if m else None) or m_meta.get("cover_url")
    content_type = (expr.content_type if expr else None) or m_meta.get("content_type")
    item_format = (
        (getattr(m, "format", None) if m else None)
        or (getattr(m, "format_type", None) if m else None)
        or m_meta.get("format")
        or m_meta.get("music_release_format")
    )
    ean = m_meta.get("ean") or (m.isbn13 if m and m.isbn13 and len(str(m.isbn13)) == 13 else None)
    upc = m_meta.get("upc")
    publisher = (
        (getattr(m, "publisher", None) if m else None) or m_meta.get("record_label") or m_meta.get("label") or m_meta.get("publisher")
    )
    publication_year = (
        m_meta.get("release_year")
        or m_meta.get("publication_year")
        or m_meta.get("year")
        or (getattr(m, "publication_date", None) if m else None)
    )
    catalog_number = m_meta.get("catalog_number") or m_meta.get("catno")
    country = m_meta.get("country") or m_meta.get("country_of_origin")
    lod_links = m_meta.get("lod_links") if isinstance(m_meta.get("lod_links"), dict) else None

    return {
        "id": item.id,
        "manifestation_id": item.manifestation_id,
        "status": item.status,
        "collection_status": item.collection_status,
        "title": m.title if m else "Untitled",
        "authors": authors,
        "cover_url": cover_url,
        "content_type": content_type,
        "format": item_format,
        "ean": ean,
        "upc": upc,
        "publisher": publisher,
        "publication_year": publication_year,
        "catalog_number": catalog_number,
        "country": country,
        "lod_links": lod_links,
    }


@public_bp.route("/share/<string:token>", methods=["GET"])
@optional_auth
@limiter.limit("60 per minute")
def get_shared_collection(token: str):
    """Retrieve items based on a specific SharedCollection token filters."""
    viewer_id = getattr(g, "user_id", None)
    accept_header = request.headers.get("Accept", "")
    accept_lower = accept_header.lower()
    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    format_arg = request.args.get("format", "").strip().lower()
    is_stream = request.args.get("stream", "").lower() in ("true", "1")
    page_arg = request.args.get("page", type=int)
    per_page_arg = request.args.get("per_page", type=int)

    page_num = max(1, page_arg) if page_arg is not None else None
    per_page_num = max(1, min(per_page_arg if per_page_arg is not None else 48, 200)) if page_num is not None else None
    offset_val = (page_num - 1) * per_page_num if (page_num is not None and per_page_num is not None) else 0

    valid_formats = {"", "json", "nt", "n-triples", "json-ld", "jsonld", "turtle", "ttl", "rdfxml", "xml", "rdf+xml"}
    if format_arg not in valid_formats:
        return jsonify({"error": f"Unsupported format: {format_arg}", "code": 400}), 400

    # Content negotiation for RDF formats (JSON-LD, Turtle, RDF/XML, N-Triples)
    rdf_format: str | None = None
    rdf_mimetype: str = ""

    if "application/n-triples" in accept_lower or format_arg in ("nt", "n-triples") or accept_lower == "text/plain":
        rdf_format = "nt"
        rdf_mimetype = "application/n-triples"
    elif "application/ld+json" in accept_lower or "application/json+ld" in accept_lower or format_arg in ("json-ld", "jsonld"):
        rdf_format = "json-ld"
        rdf_mimetype = "application/ld+json"
    elif "text/turtle" in accept_lower or "application/x-turtle" in accept_lower or format_arg in ("turtle", "ttl"):
        rdf_format = "turtle"
        rdf_mimetype = "text/turtle"
    elif "application/rdf+xml" in accept_lower or format_arg in ("rdfxml", "xml", "rdf+xml"):
        rdf_format = "xml"
        rdf_mimetype = "application/rdf+xml"

    if rdf_format:
        cache_policy_box: dict[str, bool] = {}
        if page_num is not None and per_page_num is not None:
            items = fetch_shared_collection_by_token(
                token=token,
                limit=per_page_num,
                offset=offset_val,
                stream=is_stream,
                viewer_id=viewer_id,
                _cache_policy_out=cache_policy_box,
            )
        else:
            limit_val = _parse_safe_rdf_limit(default=1000, max_limit=MAX_SHARED_COLLECTION_LIMIT)
            items = fetch_shared_collection_by_token(
                token=token,
                limit=limit_val,
                stream=is_stream,
                viewer_id=viewer_id,
                _cache_policy_out=cache_policy_box,
            )
        is_private_cache = (
            cache_policy_box["is_private_cache"]
            if "is_private_cache" in cache_policy_box
            else is_shared_collection_private_cache(token, viewer_id=viewer_id)
        )
        collection_uri = f"{base_url}/share/{token}"
        rdf_headers = _apply_share_cache_headers({"Content-Type": f"{rdf_mimetype}; charset=utf-8"}, is_private_cache)
        if is_stream:
            return Response(
                stream_with_context(stream_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)),
                mimetype=rdf_mimetype,
                headers=rdf_headers,
            )
        # For non-streaming, convert iterator to list if needed
        if not isinstance(items, list):
            items = list(items)
        rdf_payload = serialize_collection_to_rdf(items, base_url, output_format=rdf_format, collection_uri=collection_uri)
        return Response(
            rdf_payload,
            mimetype=rdf_mimetype,
            headers=rdf_headers,
        )

    stmt = select(SharedCollection).where(SharedCollection.share_token == token)
    collection = db.session.execute(stmt).scalar_one_or_none()
    if not collection:
        return jsonify({"error": "Collection not found"}), 404
    if collection.is_expired:
        return jsonify({"error": "Collection not found"}), 404

    user = db.session.get(User, collection.user_id)
    if not user:
        return jsonify({"error": "Author not found"}), 404

    allowed_vis, include_hidden, is_private_cache = _resolve_shared_visibilities(collection, viewer_id=viewer_id)
    query = select(Item).where(Item.owner_id == user.id, _build_shared_visibility_predicate(allowed_vis, include_hidden))

    filters = collection.filters

    if "status" in filters:
        # 'status' maps to either Item.status or Item.collection_status.
        #
        # The value may be a single status or a list of them. It is a list
        # whenever the sharer had several statuses selected on /collection,
        # which its filters allow -- and the share dialog used to pass only
        # statuses[0], silently publishing a link to a subset of what was on
        # screen. Accepting both shapes keeps every already-shared link working
        # while making the multi-status case mean what the sharer intended.
        status_val = filters["status"]
        statuses = status_val if isinstance(status_val, list) else [status_val]
        statuses = [s for s in statuses if isinstance(s, str) and s]
        if statuses:
            query = query.where(or_(Item.status.in_(statuses), Item.collection_status.in_(statuses)))
        else:
            # A malformed value must not widen the link to the whole library.
            query = query.where(sa.false())

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
            if db.engine.dialect.name == "postgresql":
                statuses_list = statuses if "status" in filters else None
                tags_list = filters.get("tags")
                _, results = SearchService.search_items(
                    q=search_query,
                    user_id=user.id,
                    limit=MAX_SHARED_COLLECTION_LIMIT,
                    offset=0,
                    statuses=statuses_list,
                    category=tags_list,
                    owner_only=True,
                    include_hidden=include_hidden or any(v != "public" for v in allowed_vis),
                    visibility=list(allowed_vis),
                )
                item_ids = [r["item_id"] for r in results]
                if not item_ids:
                    query = query.where(sa.false())
                else:
                    query = query.where(Item.id.in_(item_ids))
            else:
                # Join Work and Manifestation if not joined
                if "tags" not in filters:
                    query = query.outerjoin(Manifestation, Item.manifestation_id == Manifestation.id)
                    query = query.outerjoin(Expression, Manifestation.expression_id == Expression.id)
                query = query.outerjoin(Work, Expression.work_id == Work.id)
                query = query.where(build_ilike_search_clause(search_query))

    total_count = int(
        db.session.execute(select(func.count()).select_from(query.subquery())).scalar_one() or 0
    )  # pylint: disable=not-callable
    limit_val = (
        per_page_num
        if (page_num is not None and per_page_num is not None)
        else _parse_safe_rdf_limit(default=1000, max_limit=MAX_SHARED_COLLECTION_LIMIT)
    )
    items = list(
        db.session.execute(
            query.order_by(Item.updated_at.desc())
            .limit(limit_val)
            .offset(offset_val)
            .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
        )
        .scalars()
        .unique()
        .all()
    )

    items_list = [_serialize_shared_collection_item(item) for item in items]

    status_filter = filters.get("status")
    status_list: list[str] = []
    if status_filter:
        raw_list = status_filter if isinstance(status_filter, list) else [status_filter]
        status_list = [s for s in raw_list if isinstance(s, str) and s]

    _INTENT_LEVEL_STATUSES = {"want_to_read", "want_to_listen", "want_to_watch", "want_to_play", "want_to_build"}
    wish_list_statuses = _INTENT_LEVEL_STATUSES | {"wish_list"}
    is_wish_list = any(s in wish_list_statuses for s in status_list)
    intent_total = 0

    if is_wish_list:
        # Query UserWorkIntent directly for shared collection visibility.
        # Hidden intents are excluded unless the collection visibility scope allows them ('all').
        intent_conditions = [UserWorkIntent.user_id == user.id]
        if not include_hidden:
            intent_conditions.append(UserWorkIntent.is_hidden.is_(False))
        intent_stmt = (
            select(UserWorkIntent)
            .options(joinedload(UserWorkIntent.work).selectinload(Work.expressions).selectinload(Expression.manifestations))
            .where(*intent_conditions)
        )
        matched_intents = [s for s in status_list if s in _INTENT_LEVEL_STATUSES]
        if matched_intents:
            intent_stmt = intent_stmt.where(UserWorkIntent.status.in_(matched_intents))
        else:
            intent_stmt = intent_stmt.where(UserWorkIntent.status != "fulfilled")

        if filters.get("query"):
            search_term = str(filters["query"]).strip()
            if search_term:
                escaped_term = escape_ilike_term(search_term)
                raw_pat = f"%{escaped_term}%"
                is_pg = db.engine.dialect.name == "postgresql"
                norm_pat = f"%{escape_ilike_term(normalize_diacritics(search_term))}%"

                # Field-scoped searches avoiding full Work.meta JSON blob dump
                title_match = (
                    or_(
                        Work.title.ilike(raw_pat, escape="\\"),
                        func.immutable_unaccent(Work.title).ilike(norm_pat, escape="\\"),
                    )
                    if is_pg
                    else Work.title.ilike(raw_pat, escape="\\")
                )
                author_meta_match = (
                    or_(
                        _meta_text(Work.meta["authors"]).ilike(raw_pat, escape="\\"),
                        _meta_text(Work.meta["author"]).ilike(raw_pat, escape="\\"),
                        func.immutable_unaccent(_meta_text(Work.meta["authors"])).ilike(norm_pat, escape="\\"),
                        func.immutable_unaccent(_meta_text(Work.meta["author"])).ilike(norm_pat, escape="\\"),
                    )
                    if is_pg
                    else or_(
                        _meta_text(Work.meta["authors"]).ilike(raw_pat, escape="\\"),
                        _meta_text(Work.meta["author"]).ilike(raw_pat, escape="\\"),
                    )
                )
                contrib_match = (
                    or_(
                        Contributor.name.ilike(raw_pat, escape="\\"),
                        func.immutable_unaccent(Contributor.name).ilike(norm_pat, escape="\\"),
                    )
                    if is_pg
                    else Contributor.name.ilike(raw_pat, escape="\\")
                )

                intent_stmt = intent_stmt.join(Work, UserWorkIntent.work_id == Work.id).where(
                    or_(
                        title_match,
                        author_meta_match,
                        exists(
                            select(1)
                            .select_from(WorkContribution)
                            .join(Contributor, Contributor.id == WorkContribution.contributor_id)
                            .where(
                                WorkContribution.work_id == Work.id,
                                contrib_match,
                            )
                        ),
                    )
                )

        intent_total = int(
            db.session.execute(select(func.count()).select_from(intent_stmt.subquery())).scalar_one() or 0
        )  # pylint: disable=not-callable
        ordered_intent_stmt = intent_stmt.order_by(UserWorkIntent.updated_at.desc().nullslast(), UserWorkIntent.id.desc())
        if page_num is not None and per_page_num is not None:
            remaining_limit = max(0, limit_val - len(items_list))
            intent_offset = max(0, offset_val - total_count)
            intents = (
                list(db.session.execute(ordered_intent_stmt.limit(remaining_limit).offset(intent_offset)).scalars().all())
                if remaining_limit > 0
                else []
            )
        else:
            intents = list(db.session.execute(ordered_intent_stmt.limit(limit_val)).scalars().all())
        for intent in intents:
            work = intent.work
            manifestation = None
            if work:
                for expr in work.expressions:
                    if expr.manifestations:
                        manifestation = expr.manifestations[0]
                        break

            items_list.append(
                {
                    "id": intent.id,
                    "manifestation_id": manifestation.id if manifestation else None,
                    "status": intent.status,
                    "collection_status": "wish_list",
                    "title": work.title if work else None,
                    "authors": work.meta.get("authors", []) if work and work.meta else [],
                    "cover_url": (
                        manifestation.cover_url or (manifestation.meta.get("cover_url") if manifestation and manifestation.meta else None)
                        if manifestation
                        else None
                    ),
                }
            )

    effective_per_page = per_page_num if per_page_num is not None else limit_val
    total_items = total_count + (intent_total if is_wish_list else 0)
    total_pages = (total_items + effective_per_page - 1) // effective_per_page if total_items else 0

    visibility_scope = filters.get("visibility_scope", "public_only") if isinstance(filters, dict) else "public_only"
    response = jsonify(
        {
            "success": True,
            "data": {
                "collection_name": collection.name,
                "collection_description": collection.description,
                "visibility_scope": visibility_scope,
                "author": user.public_username or user.display_name or "A user",
                "total": total_items,
                "page": page_num if page_num is not None else 1,
                "per_page": effective_per_page,
                "pages": total_pages,
                "items": items_list,
            },
        }
    )
    response.headers["Vary"] = "Authorization, Cookie"
    if is_private_cache:
        response.headers["Cache-Control"] = "private, no-store"
    else:
        response.headers["Cache-Control"] = "public, max-age=300"
    return response


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

    # Public catalog works (bounded up to 50,000 URLs)
    works = db.session.execute(select(Work.id).limit(50000)).scalars().all()
    for wid in works:
        loc_w = f"{base_url}/work/{wid}"
        urls.append(f"  <url><loc>{loc_w}</loc><changefreq>monthly</changefreq></url>")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"
    )


@public_bp.route("/sitemap.xml", methods=["GET"])
@limiter.limit("60 per minute")
def sitemap() -> Response:
    """Generate an XML sitemap listing public user profiles, shared collections, and catalog items."""
    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    xml = generate_sitemap_xml(base_url)
    resp = Response(xml, content_type="application/xml; charset=utf-8")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp
