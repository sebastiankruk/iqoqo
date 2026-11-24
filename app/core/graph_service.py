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
"""Bounded, visibility-safe FRBR & semantic neighborhood graph builder."""

from __future__ import annotations

import uuid
from collections import deque
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import selectinload

from app.api.filters import escape_ilike_term
from app.core.friend_service import get_friend_user_ids
from app.core.search_service import _meta_text, normalize_diacritics
from app.db.contributions import Contributor, ExpressionContribution, WorkContribution, WorkPart, WorkSeriesMembership
from app.db.core import Expression, Item, Manifestation, SemanticLink, Work, WorkExpansionLink
from app.db.federation import FederationConsent
from app.db.games import ContainerAggregation
from app.db.models import db
from app.db.video import ManifestationContribution

VALID_GRAPH_ENTITY_TYPES: tuple[str, ...] = (
    "work",
    "expression",
    "manifestation",
    "item",
    "person",
    "contributor",
    "series",
)
VALID_GRAPH_SEARCH_TYPES: tuple[str, ...] = VALID_GRAPH_ENTITY_TYPES
DEFAULT_GRAPH_SEARCH_TYPES: tuple[str, ...] = ("person", "series", "work", "manifestation", "item")
VALID_LIBRARY_ENTITY_TYPES: tuple[str, ...] = (
    "work",
    "series",
    "contributor",
    "expression",
    "manifestation",
    "item",
    "map",
    "lod",
)
VALID_EDGE_CATEGORIES: tuple[str, ...] = ("frbr", "series", "parts_expansions", "contributors", "maps", "lod")
MAX_GRAPH_DEPTH = 4
MAX_GRAPH_NODES = 150
MAX_GRAPH_EDGES = 400
MAX_GRAPH_EDGES_CEILING = 600
MAX_NEIGHBORS_PER_NODE_DEEP = 25


def get_federation_opted_out_user_ids() -> set[uuid.UUID]:
    """Return user UUIDs that have opted out of federated/public collection exposure."""
    rows = db.session.execute(select(FederationConsent.user_id).where(FederationConsent.federated_collection.is_(False))).scalars().all()
    return {uid for uid in rows if uid is not None}


def build_sql_item_visibility_clause(
    viewer_uuid: uuid.UUID | None,
    viewer_friend_ids: set[uuid.UUID],
    opted_out_user_ids: set[uuid.UUID],
) -> Any:
    """Build SQLAlchemy WHERE clause enforcing 3-tier Item visibility + FederationConsent."""
    non_friend_opted_out = opted_out_user_ids - viewer_friend_ids
    pub_clause = and_(
        Item.visibility == "public",
        Item.is_hidden.is_(False),
        ~Item.owner_id.in_(non_friend_opted_out) if non_friend_opted_out else True,
    )
    vis_clauses: list[Any] = [pub_clause]
    if viewer_uuid is not None:
        vis_clauses.append(Item.owner_id == viewer_uuid)
        if viewer_friend_ids:
            vis_clauses.append(and_(Item.owner_id.in_(viewer_friend_ids), Item.visibility.in_(("friends_only", "shared"))))
    return or_(*vis_clauses)


def is_item_visible_to_viewer(
    item: Item,
    viewer_user_id: uuid.UUID | str | None,
    viewer_friend_ids: set[uuid.UUID],
    opted_out_user_ids: set[uuid.UUID] | None = None,
) -> bool:
    """Return True if *item* satisfies three-tier visibility and FederationConsent rules."""
    effective_visibility = (item.visibility or ("private" if item.is_hidden else "public")).lower()

    viewer_uuid: uuid.UUID | None = None
    if viewer_user_id:
        try:
            viewer_uuid = uuid.UUID(str(viewer_user_id)) if not isinstance(viewer_user_id, uuid.UUID) else viewer_user_id
        except (ValueError, TypeError):
            viewer_uuid = None

    if viewer_uuid is not None and item.owner_id == viewer_uuid:
        return True

    if viewer_uuid is not None and effective_visibility in ("friends_only", "shared") and item.owner_id in viewer_friend_ids:
        return True

    if effective_visibility == "public" and not item.is_hidden:
        if opted_out_user_ids and item.owner_id in opted_out_user_ids and item.owner_id not in viewer_friend_ids:
            return False
        return True

    return False


def _node_key(entity_type: str, entity_id: int | str) -> str:
    return f"{entity_type}:{entity_id}"


def _work_node_dict(work: Work, *, hop: int, is_anchor: bool) -> dict[str, Any]:
    authors = work.meta.get("authors", []) if isinstance(work.meta, dict) else []
    subtitle_parts: list[str] = []
    if work.work_kind:
        subtitle_parts.append(work.work_kind)
    if work.issn:
        subtitle_parts.append(f"ISSN {work.issn}")
    elif isinstance(authors, list) and authors:
        first_authors = [str(a) for a in authors[:2] if a]
        if first_authors:
            subtitle_parts.append(", ".join(first_authors))

    return {
        "id": _node_key("work", work.id),
        "entity_type": "work",
        "entity_id": work.id,
        "label": work.title or f"Work #{work.id}",
        "subtitle": " • ".join(subtitle_parts) if subtitle_parts else None,
        "work_kind": work.work_kind,
        "issn": work.issn,
        "hop": hop,
        "is_anchor": is_anchor,
        "url": f"/work/{work.id}",
    }


def _expression_node_dict(expr: Expression, *, hop: int, is_anchor: bool) -> dict[str, Any]:
    work_title = expr.work.title if getattr(expr, "work", None) else f"Work #{expr.work_id}"
    details = [part for part in (expr.content_type, expr.language, expr.kind) if part]
    return {
        "id": _node_key("expression", expr.id),
        "entity_type": "expression",
        "entity_id": expr.id,
        "label": f"{work_title} ({expr.language or expr.content_type or 'Expression'})",
        "subtitle": " • ".join(details) if details else "Expression",
        "hop": hop,
        "is_anchor": is_anchor,
        "url": f"/expression/{expr.id}",
    }


def _manifestation_node_dict(manifestation: Manifestation, *, hop: int, is_anchor: bool) -> dict[str, Any]:
    base_title = manifestation.title or f"Manifestation #{manifestation.id}"
    if manifestation.issue_number:
        issue_tag = (
            f"#{manifestation.issue_number}({manifestation.cumulative_issue_number})"
            if manifestation.cumulative_issue_number is not None
            else f"#{manifestation.issue_number}"
        )
        label = f"{base_title} {issue_tag}"
    else:
        label = base_title

    year = manifestation.publication_year or (manifestation.publication_date.year if manifestation.publication_date else None)
    fmt = manifestation.format or manifestation.format_type
    details = [str(p) for p in (fmt, manifestation.publisher, year) if p]
    return {
        "id": _node_key("manifestation", manifestation.id),
        "entity_type": "manifestation",
        "entity_id": manifestation.id,
        "label": label,
        "subtitle": " • ".join(details) if details else "Manifestation",
        "hop": hop,
        "is_anchor": is_anchor,
        "url": f"/manifestation/{manifestation.id}",
    }


def _item_node_dict(item: Item, *, hop: int, is_anchor: bool) -> dict[str, Any]:
    effective_visibility = (item.visibility or ("private" if item.is_hidden else "public")).lower()
    details = [p for p in (item.collection_status, item.status, effective_visibility) if p]
    return {
        "id": _node_key("item", item.id),
        "entity_type": "item",
        "entity_id": item.id,
        "label": f"Copy #{item.id}",
        "subtitle": " • ".join(details) if details else "Item",
        "visibility": effective_visibility,
        "hop": hop,
        "is_anchor": is_anchor,
        "url": f"/item/{item.id}",
    }


def _contributor_node_dict(contributor: Contributor, *, hop: int, is_anchor: bool = False) -> dict[str, Any]:
    contributor_type = contributor.type or "person"
    return {
        "id": _node_key("contributor", contributor.id),
        "entity_type": "contributor",
        "entity_id": contributor.id,
        "contributor_type": contributor_type,
        "label": contributor.name or f"Contributor #{contributor.id}",
        "subtitle": contributor_type,
        "hop": hop,
        "is_anchor": is_anchor,
        "url": f"/collection?q={quote_plus(contributor.name)}" if contributor.name else None,
    }


def _map_node_dict(manifestation_id: int, idx: int, attachment: dict[str, Any], *, hop: int) -> dict[str, Any]:
    att_id = str(attachment.get("id") or idx)
    details = [str(p) for p in (attachment.get("type"), attachment.get("scale")) if p]
    return {
        "id": f"map:{manifestation_id}:{att_id}",
        "entity_type": "map",
        "entity_id": f"{manifestation_id}:{att_id}",
        "label": str(attachment.get("title") or f"Map #{idx + 1}"),
        "subtitle": " • ".join(details) if details else "Map Attachment",
        "external_uri": attachment.get("image_url"),
        "hop": hop,
        "is_anchor": False,
        "url": f"/manifestation/{manifestation_id}",
    }


def _lod_node_dict(link: SemanticLink, *, hop: int) -> dict[str, Any]:
    fallback_label = link.external_uri.rstrip("/").rsplit("/", 1)[-1] or link.authority
    return {
        "id": _node_key("lod", link.id),
        "entity_type": "lod",
        "entity_id": link.id,
        "label": link.pref_label or fallback_label,
        "subtitle": link.authority,
        "authority": link.authority,
        "external_uri": link.external_uri,
        "hop": hop,
        "is_anchor": False,
        "url": link.external_uri,
    }


class GraphService:
    """Service layer for constructing bounded FRBR and semantic relation neighborhoods."""

    @staticmethod
    def build_neighborhood(
        entity_type: str,
        entity_id: int,
        *,
        viewer_user_id: uuid.UUID | str | None = None,
        depth: int = 1,
        max_nodes: int = MAX_GRAPH_NODES,
        max_edges: int = MAX_GRAPH_EDGES,
        edge_categories: set[str] | None = None,
    ) -> dict[str, Any] | None:
        """Build a bounded BFS neighborhood graph centered at ``(entity_type, entity_id)``.

        Returns ``None`` if the anchor entity does not exist or is an ``Item``
        whose visibility forbids access by ``viewer_user_id``.
        """
        norm_type = (entity_type or "").strip().lower()
        if norm_type not in VALID_GRAPH_ENTITY_TYPES:
            return None

        requested_depth = depth
        effective_depth = max(1, min(int(depth), MAX_GRAPH_DEPTH))
        effective_max_nodes = max(1, min(int(max_nodes), MAX_GRAPH_NODES))
        effective_max_edges = max(1, min(int(max_edges), MAX_GRAPH_EDGES_CEILING))
        allowed_categories = edge_categories & set(VALID_EDGE_CATEGORIES) if edge_categories is not None else set(VALID_EDGE_CATEGORIES)

        viewer_friend_ids = get_friend_user_ids(viewer_user_id) if viewer_user_id else set()
        opted_out_user_ids = get_federation_opted_out_user_ids()

        anchor_orm = GraphService._load_anchor(norm_type, entity_id, viewer_user_id, viewer_friend_ids, opted_out_user_ids)
        if anchor_orm is None:
            return None

        canonical_type = "contributor" if norm_type in ("person", "contributor") else ("work" if norm_type == "series" else norm_type)

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        node_truncated = False
        edge_truncated = False
        queue: deque[tuple[str, Any, int]] = deque()

        root_key = _node_key(canonical_type, entity_id)
        nodes[root_key] = GraphService._serialize_node(canonical_type, anchor_orm, hop=0, is_anchor=True)
        queue.append((canonical_type, anchor_orm, 0))

        def try_add_node(node_key: str, node_payload: dict[str, Any]) -> bool:
            nonlocal node_truncated
            if node_key in nodes:
                return True
            if len(nodes) >= effective_max_nodes:
                node_truncated = True
                return False
            nodes[node_key] = node_payload
            return True

        def add_edge(source: str, target: str, relation: str, category: str, label: str | None = None) -> None:
            nonlocal edge_truncated
            if source not in nodes or target not in nodes:
                return
            edge_sig = (source, target, relation)
            if edge_sig in seen_edges:
                return
            if len(edges) >= effective_max_edges:
                edge_truncated = True
                return
            seen_edges.add(edge_sig)
            edges.append(
                {
                    "id": f"{source}--{relation}--{target}",
                    "source": source,
                    "target": target,
                    "relation": relation,
                    "category": category,
                    "label": label or relation.replace("_", " "),
                }
            )

        def enqueue_neighbor(n_type: str, n_orm: Any, next_hop: int) -> str | None:
            n_key = _node_key(n_type, n_orm.id)
            already_present = n_key in nodes
            if not try_add_node(n_key, GraphService._serialize_node(n_type, n_orm, hop=next_hop, is_anchor=False)):
                return None
            if not already_present and next_hop < effective_depth:
                queue.append((n_type, n_orm, next_hop))
            return n_key

        per_node_cap = MAX_NEIGHBORS_PER_NODE_DEEP if effective_depth >= 3 else None

        while queue:
            cur_type, cur_orm, cur_hop = queue.popleft()
            if cur_hop >= effective_depth:
                continue
            next_hop = cur_hop + 1
            cur_key = _node_key(cur_type, cur_orm.id)
            node_added = 0

            def bounded_enqueue(n_type: str, n_orm: Any, hop_val: int) -> str | None:
                nonlocal node_added, node_truncated
                n_key = _node_key(n_type, n_orm.id)
                was_present = n_key in nodes
                if per_node_cap is not None and not was_present and node_added >= per_node_cap:
                    node_truncated = True
                    return None
                res = enqueue_neighbor(n_type, n_orm, hop_val)
                if res is not None and not was_present:
                    node_added += 1
                return res

            def bounded_try_add(n_key: str, n_payload: dict[str, Any]) -> bool:
                nonlocal node_added, node_truncated
                was_present = n_key in nodes
                if per_node_cap is not None and not was_present and node_added >= per_node_cap:
                    node_truncated = True
                    return False
                ok = try_add_node(n_key, n_payload)
                if ok and not was_present:
                    node_added += 1
                return ok

            if cur_type == "work":
                GraphService._expand_work(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    viewer_user_id,
                    viewer_friend_ids,
                    opted_out_user_ids,
                    bounded_enqueue,
                    bounded_try_add,
                    add_edge,
                )
            elif cur_type == "expression":
                GraphService._expand_expression(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    bounded_enqueue,
                    bounded_try_add,
                    add_edge,
                )
            elif cur_type == "manifestation":
                GraphService._expand_manifestation(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    viewer_user_id,
                    viewer_friend_ids,
                    opted_out_user_ids,
                    bounded_enqueue,
                    bounded_try_add,
                    add_edge,
                )
            elif cur_type == "item":
                GraphService._expand_item(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    bounded_enqueue,
                    add_edge,
                )
            elif cur_type == "contributor":
                GraphService._expand_contributor(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    bounded_enqueue,
                    bounded_try_add,
                    add_edge,
                )

        truncated = node_truncated or edge_truncated
        truncated_reason: str | None = None
        if node_truncated and edge_truncated:
            truncated_reason = "both"
        elif node_truncated:
            truncated_reason = "node_cap"
        elif edge_truncated:
            truncated_reason = "edge_cap"

        return {
            "anchor": {"entity_type": canonical_type, "entity_id": entity_id, "node_id": root_key},
            "mode": "neighborhood",
            "nodes": list(nodes.values()),
            "edges": edges,
            "meta": {
                "depth": effective_depth,
                "requested_depth": requested_depth,
                "max_nodes": effective_max_nodes,
                "max_edges": effective_max_edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "truncated": truncated,
                "truncated_reason": truncated_reason,
            },
        }

    @staticmethod
    def build_library_graph(
        *,
        viewer_user_id: uuid.UUID | str | None = None,
        entity_types: set[str] | None = None,
        edge_categories: set[str] | None = None,
        max_nodes: int = MAX_GRAPH_NODES,
        max_edges: int = MAX_GRAPH_EDGES,
    ) -> dict[str, Any]:
        """Build a bounded, visibility-safe full-library concept graph (no single anchor)."""
        effective_max_nodes = max(1, min(int(max_nodes), MAX_GRAPH_NODES))
        effective_max_edges = max(1, min(int(max_edges), MAX_GRAPH_EDGES_CEILING))
        allowed_entities = entity_types & set(VALID_LIBRARY_ENTITY_TYPES) if entity_types is not None else set(VALID_LIBRARY_ENTITY_TYPES)
        allowed_categories = edge_categories & set(VALID_EDGE_CATEGORIES) if edge_categories is not None else set(VALID_EDGE_CATEGORIES)

        viewer_friend_ids = get_friend_user_ids(viewer_user_id) if viewer_user_id else set()
        opted_out_user_ids = get_federation_opted_out_user_ids()

        viewer_uuid: uuid.UUID | None = None
        if viewer_user_id:
            try:
                viewer_uuid = uuid.UUID(str(viewer_user_id)) if not isinstance(viewer_user_id, uuid.UUID) else viewer_user_id
            except (ValueError, TypeError):
                viewer_uuid = None

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        node_truncated = False
        edge_truncated = False

        def try_add_node(node_key: str, node_payload: dict[str, Any]) -> bool:
            nonlocal node_truncated
            if node_key in nodes:
                return True
            if len(nodes) >= effective_max_nodes:
                node_truncated = True
                return False
            nodes[node_key] = node_payload
            return True

        def add_edge(source: str, target: str, relation: str, category: str, label: str | None = None) -> None:
            nonlocal edge_truncated
            if category not in allowed_categories:
                return
            if source not in nodes or target not in nodes:
                return
            edge_sig = (source, target, relation)
            if edge_sig in seen_edges:
                return
            if len(edges) >= effective_max_edges:
                edge_truncated = True
                return
            seen_edges.add(edge_sig)
            edges.append(
                {
                    "id": f"{source}--{relation}--{target}",
                    "source": source,
                    "target": target,
                    "relation": relation,
                    "category": category,
                    "label": label or relation.replace("_", " "),
                }
            )

        active_tiers = [t for t in VALID_LIBRARY_ENTITY_TYPES if t in allowed_entities]
        tier_quota = effective_max_nodes if len(active_tiers) <= 1 else max(1, effective_max_nodes // len(active_tiers))
        quota_truncated = False

        # 1. Works & Series (partitioned quota + SQL work_kind filter before LIMIT)
        want_work = "work" in allowed_entities
        want_series = "series" in allowed_entities
        if want_work or want_series:
            work_limit = (
                effective_max_nodes
                if len(active_tiers) <= 1 or set(active_tiers) <= {"work", "series"}
                else min(effective_max_nodes, tier_quota * (2 if (want_work and want_series) else 1))
            )
            work_stmt = select(Work).order_by(Work.id.asc()).limit(work_limit + 1)
            if want_series and not want_work:
                work_stmt = work_stmt.where(Work.work_kind == "series")
            elif want_work and not want_series:
                work_stmt = work_stmt.where(or_(Work.work_kind.is_(None), Work.work_kind != "series"))
            work_rows = list(db.session.execute(work_stmt).scalars().all())
            if len(work_rows) > work_limit:
                quota_truncated = True
                work_rows = work_rows[:work_limit]
            for w in work_rows:
                payload = _work_node_dict(w, hop=0, is_anchor=False)
                if w.work_kind == "series" and want_series:
                    payload["entity_type"] = "series"
                if not try_add_node(payload["id"], payload):
                    break

        present_work_ids = [int(k.split(":")[1]) for k in nodes if k.startswith("work:")]

        # 2. Expressions (prioritize children of selected Works)
        if "expression" in allowed_entities and not node_truncated:
            expr_quota = effective_max_nodes if len(active_tiers) <= 1 else tier_quota
            expr_rows: list[Expression] = []
            if present_work_ids:
                expr_rows = (
                    db.session.execute(
                        select(Expression)
                        .options(selectinload(Expression.work))
                        .where(Expression.work_id.in_(present_work_ids))
                        .order_by(Expression.id.asc())
                        .limit(expr_quota)
                    )
                    .scalars()
                    .all()
                )
            if len(expr_rows) < expr_quota:
                seen_e = {e.id for e in expr_rows}
                extra_stmt = (
                    select(Expression)
                    .options(selectinload(Expression.work))
                    .order_by(Expression.id.asc())
                    .limit(expr_quota - len(expr_rows))
                )
                if seen_e:
                    extra_stmt = extra_stmt.where(~Expression.id.in_(seen_e))
                expr_rows.extend(db.session.execute(extra_stmt).scalars().all())
            for e in expr_rows:
                payload = _expression_node_dict(e, hop=0, is_anchor=False)
                if not try_add_node(payload["id"], payload):
                    break

        present_expr_ids = [int(k.split(":")[1]) for k in nodes if k.startswith("expression:")]

        # 3. Manifestations (& Maps) (prioritize children of selected Expressions/Works)
        want_man = "manifestation" in allowed_entities
        want_map = "map" in allowed_entities
        if (want_man or want_map) and not node_truncated:
            man_quota = effective_max_nodes if len(active_tiers) <= 1 else tier_quota
            man_rows: list[Manifestation] = []
            if present_expr_ids:
                man_rows = (
                    db.session.execute(
                        select(Manifestation)
                        .where(Manifestation.expression_id.in_(present_expr_ids))
                        .order_by(Manifestation.id.asc())
                        .limit(man_quota)
                    )
                    .scalars()
                    .all()
                )
            elif present_work_ids:
                man_rows = (
                    db.session.execute(
                        select(Manifestation)
                        .join(Expression, Manifestation.expression_id == Expression.id)
                        .where(Expression.work_id.in_(present_work_ids))
                        .order_by(Manifestation.id.asc())
                        .limit(man_quota)
                    )
                    .scalars()
                    .all()
                )
            if len(man_rows) < man_quota:
                seen_m = {m.id for m in man_rows}
                extra_m_stmt = select(Manifestation).order_by(Manifestation.id.asc()).limit(man_quota - len(man_rows))
                if seen_m:
                    extra_m_stmt = extra_m_stmt.where(~Manifestation.id.in_(seen_m))
                man_rows.extend(db.session.execute(extra_m_stmt).scalars().all())
            for m in man_rows:
                if want_man:
                    m_payload = _manifestation_node_dict(m, hop=0, is_anchor=False)
                    if not try_add_node(m_payload["id"], m_payload):
                        break
                if want_map and isinstance(m.meta, dict) and not node_truncated:
                    atts = m.meta.get("map_attachments") or []
                    if isinstance(atts, list):
                        for idx, att in enumerate(atts):
                            if isinstance(att, dict):
                                map_payload = _map_node_dict(m.id, idx, att, hop=0)
                                if try_add_node(map_payload["id"], map_payload) and want_man:
                                    add_edge(
                                        _node_key("manifestation", m.id),
                                        map_payload["id"],
                                        "has_map",
                                        "maps",
                                        str(att.get("type") or "map"),
                                    )

        present_man_ids = [int(k.split(":")[1]) for k in nodes if k.startswith("manifestation:")]

        # 4. Physical Items (3-tier visibility + FederationConsent; never UserWorkIntent)
        if "item" in allowed_entities and not node_truncated:
            item_quota = effective_max_nodes if len(active_tiers) <= 1 else tier_quota
            vis_where = build_sql_item_visibility_clause(viewer_uuid, viewer_friend_ids, opted_out_user_ids)
            item_rows: list[Item] = []
            if present_man_ids:
                item_rows = (
                    db.session.execute(
                        select(Item)
                        .where(and_(vis_where, Item.manifestation_id.in_(present_man_ids)))
                        .order_by(Item.id.asc())
                        .limit(item_quota)
                    )
                    .scalars()
                    .all()
                )
            if len(item_rows) < item_quota:
                seen_it = {it.id for it in item_rows}
                extra_it_stmt = select(Item).where(vis_where).order_by(Item.id.asc()).limit(item_quota - len(item_rows))
                if seen_it:
                    extra_it_stmt = extra_it_stmt.where(~Item.id.in_(seen_it))
                item_rows.extend(db.session.execute(extra_it_stmt).scalars().all())
            for it in item_rows:
                if is_item_visible_to_viewer(it, viewer_user_id, viewer_friend_ids, opted_out_user_ids):
                    it_payload = _item_node_dict(it, hop=0, is_anchor=False)
                    if not try_add_node(it_payload["id"], it_payload):
                        break

        # 5. Contributors (prioritize contributors connected to selected Works)
        if "contributor" in allowed_entities and not node_truncated:
            contrib_quota = effective_max_nodes if len(active_tiers) <= 1 else tier_quota
            contrib_rows: list[Contributor] = []
            if present_work_ids:
                contrib_ids_sub = select(WorkContribution.contributor_id).where(WorkContribution.work_id.in_(present_work_ids))
                contrib_rows = (
                    db.session.execute(
                        select(Contributor).where(Contributor.id.in_(contrib_ids_sub)).order_by(Contributor.id.asc()).limit(contrib_quota)
                    )
                    .scalars()
                    .all()
                )
            if len(contrib_rows) < contrib_quota:
                seen_c = {c.id for c in contrib_rows}
                extra_c_stmt = select(Contributor).order_by(Contributor.id.asc()).limit(contrib_quota - len(contrib_rows))
                if seen_c:
                    extra_c_stmt = extra_c_stmt.where(~Contributor.id.in_(seen_c))
                contrib_rows.extend(db.session.execute(extra_c_stmt).scalars().all())
            for c in contrib_rows:
                payload = _contributor_node_dict(c, hop=0)
                if not try_add_node(payload["id"], payload):
                    break

        # 6. Accepted LOD SemanticLinks (prioritize links attached to present nodes)
        if "lod" in allowed_entities and not node_truncated:
            lod_quota = effective_max_nodes if len(active_tiers) <= 1 else tier_quota
            lod_rows: list[SemanticLink] = []
            anchor_filters: list[Any] = []
            if present_work_ids:
                anchor_filters.append(and_(SemanticLink.entity_type == "work", SemanticLink.entity_id.in_(present_work_ids)))
            if present_expr_ids:
                anchor_filters.append(and_(SemanticLink.entity_type == "expression", SemanticLink.entity_id.in_(present_expr_ids)))
            if present_man_ids:
                anchor_filters.append(and_(SemanticLink.entity_type == "manifestation", SemanticLink.entity_id.in_(present_man_ids)))
            if anchor_filters:
                lod_rows = (
                    db.session.execute(
                        select(SemanticLink)
                        .where(and_(SemanticLink.status == "accepted", or_(*anchor_filters)))
                        .order_by(SemanticLink.id.asc())
                        .limit(lod_quota)
                    )
                    .scalars()
                    .all()
                )
            if len(lod_rows) < lod_quota:
                seen_l = {sl.id for sl in lod_rows}
                extra_l_stmt = (
                    select(SemanticLink)
                    .where(SemanticLink.status == "accepted")
                    .order_by(SemanticLink.id.asc())
                    .limit(lod_quota - len(lod_rows))
                )
                if seen_l:
                    extra_l_stmt = extra_l_stmt.where(~SemanticLink.id.in_(seen_l))
                lod_rows.extend(db.session.execute(extra_l_stmt).scalars().all())
            for sl in lod_rows:
                lod_payload = _lod_node_dict(sl, hop=0)
                if try_add_node(lod_payload["id"], lod_payload):
                    add_edge(_node_key(sl.entity_type, sl.entity_id), lod_payload["id"], "same_as", "lod", f"sameAs ({sl.authority})")

        # 7. Connect edges between present nodes
        present_item_ids = [int(k.split(":")[1]) for k in nodes if k.startswith("item:")]
        present_person_ids = [int(k.split(":")[1]) for k in nodes if k.startswith("contributor:")]

        if "frbr" in allowed_categories:
            if present_expr_ids and present_work_ids:
                for e in db.session.execute(select(Expression).where(Expression.id.in_(present_expr_ids))).scalars().all():
                    add_edge(_node_key("expression", e.id), _node_key("work", e.work_id), "realizes", "frbr", "realizes")
            if present_man_ids and present_expr_ids:
                for m in db.session.execute(select(Manifestation).where(Manifestation.id.in_(present_man_ids))).scalars().all():
                    add_edge(_node_key("manifestation", m.id), _node_key("expression", m.expression_id), "embodies", "frbr", "embodies")
            if present_item_ids and present_man_ids:
                for it in db.session.execute(select(Item).where(Item.id.in_(present_item_ids))).scalars().all():
                    add_edge(
                        _node_key("item", it.id), _node_key("manifestation", it.manifestation_id), "exemplifies", "frbr", "exemplifies"
                    )

        if "series" in allowed_categories and present_work_ids:
            for sm in (
                db.session.execute(select(WorkSeriesMembership).where(WorkSeriesMembership.work_id.in_(present_work_ids))).scalars().all()
            ):
                seq_lbl = f"in series (#{sm.sequence})" if sm.sequence else "in series"
                add_edge(_node_key("work", sm.work_id), _node_key("work", sm.series_work_id), "in_series", "series", seq_lbl)

        if "parts_expansions" in allowed_categories:
            if present_work_ids:
                for wp in (
                    db.session.execute(
                        select(WorkPart).where(
                            or_(WorkPart.container_work_id.in_(present_work_ids), WorkPart.part_work_id.in_(present_work_ids))
                        )
                    )
                    .scalars()
                    .all()
                ):
                    part_lbl = f"has part (#{wp.sequence})" if wp.sequence else "has part"
                    add_edge(
                        _node_key("work", wp.container_work_id),
                        _node_key("work", wp.part_work_id),
                        "has_part",
                        "parts_expansions",
                        part_lbl,
                    )
                for wel in (
                    db.session.execute(
                        select(WorkExpansionLink).where(
                            or_(
                                WorkExpansionLink.base_work_id.in_(present_work_ids),
                                WorkExpansionLink.expansion_work_id.in_(present_work_ids),
                            )
                        )
                    )
                    .scalars()
                    .all()
                ):
                    add_edge(
                        _node_key("work", wel.expansion_work_id),
                        _node_key("work", wel.base_work_id),
                        "expands",
                        "parts_expansions",
                        wel.link_type,
                    )
            if present_work_ids:
                for ca in (
                    db.session.execute(select(ContainerAggregation).where(ContainerAggregation.container_work_id.in_(present_work_ids)))
                    .scalars()
                    .all()
                ):
                    if ca.aggregated_type == "work" and ca.aggregated_work_id is not None:
                        add_edge(
                            _node_key("work", ca.container_work_id),
                            _node_key("work", ca.aggregated_work_id),
                            "contains",
                            "parts_expansions",
                            "contains",
                        )
                    elif ca.aggregated_type == "item" and ca.aggregated_item_id is not None:
                        add_edge(
                            _node_key("work", ca.container_work_id),
                            _node_key("item", ca.aggregated_item_id),
                            "contains",
                            "parts_expansions",
                            "contains",
                        )

        if "contributors" in allowed_categories and present_person_ids:
            if present_work_ids:
                for wc in (
                    db.session.execute(select(WorkContribution).where(WorkContribution.work_id.in_(present_work_ids))).scalars().all()
                ):
                    add_edge(
                        _node_key("work", wc.work_id),
                        _node_key("contributor", wc.contributor_id),
                        "contributed_by",
                        "contributors",
                        wc.role,
                    )
            if present_expr_ids:
                for ec in (
                    db.session.execute(select(ExpressionContribution).where(ExpressionContribution.expression_id.in_(present_expr_ids)))
                    .scalars()
                    .all()
                ):
                    add_edge(
                        _node_key("expression", ec.expression_id),
                        _node_key("contributor", ec.contributor_id),
                        "contributed_by",
                        "contributors",
                        ec.role,
                    )
            if present_man_ids:
                for mc in (
                    db.session.execute(
                        select(ManifestationContribution).where(ManifestationContribution.manifestation_id.in_(present_man_ids))
                    )
                    .scalars()
                    .all()
                ):
                    add_edge(
                        _node_key("manifestation", mc.manifestation_id),
                        _node_key("contributor", mc.contributor_id),
                        "contributed_by",
                        "contributors",
                        mc.role,
                    )

        node_truncated = node_truncated or quota_truncated
        truncated = node_truncated or edge_truncated
        truncated_reason: str | None = None
        if node_truncated and edge_truncated:
            truncated_reason = "both"
        elif node_truncated:
            truncated_reason = "node_cap"
        elif edge_truncated:
            truncated_reason = "edge_cap"

        return {
            "anchor": None,
            "mode": "library",
            "nodes": list(nodes.values()),
            "edges": edges,
            "meta": {
                "depth": 0,
                "requested_depth": 0,
                "max_nodes": effective_max_nodes,
                "max_edges": effective_max_edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "truncated": truncated,
                "truncated_reason": truncated_reason,
            },
        }

    @staticmethod
    def _load_anchor(
        entity_type: str,
        entity_id: int,
        viewer_user_id: uuid.UUID | str | None,
        viewer_friend_ids: set[uuid.UUID],
        opted_out_user_ids: set[uuid.UUID] | None = None,
    ) -> Any:
        if entity_type == "work":
            return db.session.get(Work, entity_id)
        if entity_type == "series":
            series_cond = or_(
                Work.work_kind == "series",
                exists(select(WorkSeriesMembership.id).where(WorkSeriesMembership.series_work_id == Work.id)),
                exists(select(WorkPart.container_work_id).where(WorkPart.container_work_id == Work.id)),
            )
            return db.session.execute(select(Work).where(Work.id == entity_id, series_cond)).scalar_one_or_none()
        if entity_type in ("person", "contributor"):
            return db.session.get(Contributor, entity_id)
        if entity_type == "expression":
            return db.session.execute(
                select(Expression).options(selectinload(Expression.work)).where(Expression.id == entity_id)
            ).scalar_one_or_none()
        if entity_type == "manifestation":
            return db.session.execute(
                select(Manifestation)
                .options(selectinload(Manifestation.expression).selectinload(Expression.work))
                .where(Manifestation.id == entity_id)
            ).scalar_one_or_none()
        if entity_type == "item":
            item = db.session.get(Item, entity_id)
            if item is None or not is_item_visible_to_viewer(item, viewer_user_id, viewer_friend_ids, opted_out_user_ids):
                return None
            return item
        return None

    @staticmethod
    def _serialize_node(entity_type: str, orm_obj: Any, *, hop: int, is_anchor: bool) -> dict[str, Any]:
        if entity_type in ("work", "series"):
            return _work_node_dict(orm_obj, hop=hop, is_anchor=is_anchor)
        if entity_type in ("person", "contributor"):
            return _contributor_node_dict(orm_obj, hop=hop, is_anchor=is_anchor)
        if entity_type == "expression":
            return _expression_node_dict(orm_obj, hop=hop, is_anchor=is_anchor)
        if entity_type == "manifestation":
            return _manifestation_node_dict(orm_obj, hop=hop, is_anchor=is_anchor)
        return _item_node_dict(orm_obj, hop=hop, is_anchor=is_anchor)

    @staticmethod
    def _add_semantic_links(
        entity_type: str,
        entity_id: int,
        source_key: str,
        next_hop: int,
        try_add_node: Any,
        add_edge: Any,
    ) -> None:
        links = (
            db.session.execute(
                select(SemanticLink)
                .where(
                    SemanticLink.entity_type == entity_type,
                    SemanticLink.entity_id == entity_id,
                    SemanticLink.status == "accepted",
                )
                .order_by(SemanticLink.id.asc())
            )
            .scalars()
            .all()
        )
        for link in links:
            lod_payload = _lod_node_dict(link, hop=next_hop)
            if try_add_node(lod_payload["id"], lod_payload):
                add_edge(source_key, lod_payload["id"], "same_as", "lod", f"sameAs ({link.authority})")

    @staticmethod
    def _expand_work(
        work: Work,
        work_key: str,
        next_hop: int,
        allowed_categories: set[str],
        viewer_user_id: uuid.UUID | str | None,
        viewer_friend_ids: set[uuid.UUID],
        opted_out_user_ids: set[uuid.UUID],
        enqueue_neighbor: Any,
        try_add_node: Any,
        add_edge: Any,
    ) -> None:
        # 1. FRBR backbone: Work <- realizes - Expression
        if "frbr" in allowed_categories:
            expressions = (
                db.session.execute(select(Expression).where(Expression.work_id == work.id).order_by(Expression.id.asc())).scalars().all()
            )
            for expr in expressions:
                expr_key = enqueue_neighbor("expression", expr, next_hop)
                if expr_key:
                    add_edge(expr_key, work_key, "realizes", "frbr", "realizes")

        # 2. Series links
        if "series" in allowed_categories:
            memberships = (
                db.session.execute(
                    select(WorkSeriesMembership)
                    .options(selectinload(WorkSeriesMembership.series))
                    .where(WorkSeriesMembership.work_id == work.id)
                    .order_by(WorkSeriesMembership.sequence.asc(), WorkSeriesMembership.id.asc())
                )
                .scalars()
                .all()
            )
            for membership in memberships:
                if membership.series:
                    s_key = enqueue_neighbor("work", membership.series, next_hop)
                    if s_key:
                        seq_lbl = f"in series (#{membership.sequence})" if membership.sequence else "in series"
                        add_edge(work_key, s_key, "in_series", "series", seq_lbl)

            series_children = (
                db.session.execute(
                    select(WorkSeriesMembership)
                    .options(selectinload(WorkSeriesMembership.work))
                    .where(WorkSeriesMembership.series_work_id == work.id)
                    .order_by(WorkSeriesMembership.sequence.asc(), WorkSeriesMembership.id.asc())
                )
                .scalars()
                .all()
            )
            for item_membership in series_children:
                if item_membership.work:
                    child_key = enqueue_neighbor("work", item_membership.work, next_hop)
                    if child_key:
                        seq_lbl = f"in series (#{item_membership.sequence})" if item_membership.sequence else "in series"
                        add_edge(child_key, work_key, "in_series", "series", seq_lbl)

        # 3. WorkPart / WorkExpansionLink / ContainerAggregation
        if "parts_expansions" in allowed_categories:
            parts = (
                db.session.execute(
                    select(WorkPart)
                    .where(WorkPart.container_work_id == work.id)
                    .order_by(WorkPart.sequence.asc(), WorkPart.part_work_id.asc())
                )
                .scalars()
                .all()
            )
            if parts:
                part_ids = [wp.part_work_id for wp in parts]
                part_works = {w.id: w for w in db.session.execute(select(Work).where(Work.id.in_(part_ids))).scalars().all()}
                for wp in parts:
                    part_work = part_works.get(wp.part_work_id)
                    if part_work:
                        p_key = enqueue_neighbor("work", part_work, next_hop)
                        if p_key:
                            add_edge(work_key, p_key, "has_part", "parts_expansions", f"has part (#{wp.sequence or 0})")

            containers = (
                db.session.execute(select(WorkPart).where(WorkPart.part_work_id == work.id).order_by(WorkPart.container_work_id.asc()))
                .scalars()
                .all()
            )
            if containers:
                container_ids = [wp.container_work_id for wp in containers]
                container_works = {w.id: w for w in db.session.execute(select(Work).where(Work.id.in_(container_ids))).scalars().all()}
                for wp in containers:
                    container_work = container_works.get(wp.container_work_id)
                    if container_work:
                        c_key = enqueue_neighbor("work", container_work, next_hop)
                        if c_key:
                            add_edge(c_key, work_key, "has_part", "parts_expansions", f"has part (#{wp.sequence or 0})")

            base_link = (
                db.session.execute(
                    select(WorkExpansionLink)
                    .options(selectinload(WorkExpansionLink.base_work))
                    .where(WorkExpansionLink.expansion_work_id == work.id)
                )
                .scalars()
                .first()
            )
            if base_link and base_link.base_work:
                b_key = enqueue_neighbor("work", base_link.base_work, next_hop)
                if b_key:
                    add_edge(work_key, b_key, "is_expansion_of", "parts_expansions", "is expansion of")

            expansion_links = (
                db.session.execute(
                    select(WorkExpansionLink)
                    .options(selectinload(WorkExpansionLink.expansion_work))
                    .where(WorkExpansionLink.base_work_id == work.id)
                    .order_by(WorkExpansionLink.id.asc())
                )
                .scalars()
                .all()
            )
            for exp_link in expansion_links:
                if exp_link.expansion_work:
                    e_key = enqueue_neighbor("work", exp_link.expansion_work, next_hop)
                    if e_key:
                        add_edge(e_key, work_key, "is_expansion_of", "parts_expansions", "is expansion of")

            aggregates = (
                db.session.execute(
                    select(ContainerAggregation)
                    .options(selectinload(ContainerAggregation.aggregated_work), selectinload(ContainerAggregation.aggregated_item))
                    .where(ContainerAggregation.container_work_id == work.id)
                    .order_by(ContainerAggregation.id.asc())
                )
                .scalars()
                .all()
            )
            for agg in aggregates:
                if agg.aggregated_type == "work" and agg.aggregated_work:
                    aw_key = enqueue_neighbor("work", agg.aggregated_work, next_hop)
                    if aw_key:
                        add_edge(work_key, aw_key, "has_part", "parts_expansions", agg.component_name)
                elif agg.aggregated_type == "item" and agg.aggregated_item:
                    if is_item_visible_to_viewer(agg.aggregated_item, viewer_user_id, viewer_friend_ids):
                        ai_key = enqueue_neighbor("item", agg.aggregated_item, next_hop)
                        if ai_key:
                            add_edge(work_key, ai_key, "has_part", "parts_expansions", agg.component_name)

        # 4. Contributors
        if "contributors" in allowed_categories:
            contributions = (
                db.session.execute(
                    select(WorkContribution)
                    .where(WorkContribution.work_id == work.id)
                    .order_by(WorkContribution.sequence.asc(), WorkContribution.id.asc())
                )
                .scalars()
                .all()
            )
            if contributions:
                contrib_ids = [wc.contributor_id for wc in contributions]
                contribs = {c.id: c for c in db.session.execute(select(Contributor).where(Contributor.id.in_(contrib_ids))).scalars().all()}
                for wc in contributions:
                    contrib = contribs.get(wc.contributor_id)
                    if contrib:
                        c_key = enqueue_neighbor("contributor", contrib, next_hop)
                        if c_key:
                            add_edge(work_key, c_key, "contributed_by", "contributors", wc.role)

        # 5. Accepted LOD links
        if "lod" in allowed_categories:
            GraphService._add_semantic_links("work", work.id, work_key, next_hop, try_add_node, add_edge)

    @staticmethod
    def _expand_expression(
        expr: Expression,
        expr_key: str,
        next_hop: int,
        allowed_categories: set[str],
        enqueue_neighbor: Any,
        try_add_node: Any,
        add_edge: Any,
    ) -> None:
        if "frbr" in allowed_categories:
            parent_work = expr.work or db.session.get(Work, expr.work_id)
            if parent_work:
                w_key = enqueue_neighbor("work", parent_work, next_hop)
                if w_key:
                    add_edge(expr_key, w_key, "realizes", "frbr", "realizes")

            manifestations = (
                db.session.execute(
                    select(Manifestation)
                    .where(Manifestation.expression_id == expr.id)
                    .order_by(
                        Manifestation.publication_year.asc().nullslast(),
                        Manifestation.publication_month.asc().nullslast(),
                        Manifestation.id.asc(),
                    )
                    .limit(MAX_GRAPH_NODES)
                )
                .scalars()
                .all()
            )
            for man in manifestations:
                m_key = enqueue_neighbor("manifestation", man, next_hop)
                if m_key:
                    add_edge(m_key, expr_key, "embodies", "frbr", "embodies")

        if "contributors" in allowed_categories:
            contributions = (
                db.session.execute(
                    select(ExpressionContribution)
                    .where(ExpressionContribution.expression_id == expr.id)
                    .order_by(ExpressionContribution.sequence.asc(), ExpressionContribution.id.asc())
                )
                .scalars()
                .all()
            )
            if contributions:
                contrib_ids = [ec.contributor_id for ec in contributions]
                contribs = {c.id: c for c in db.session.execute(select(Contributor).where(Contributor.id.in_(contrib_ids))).scalars().all()}
                for ec in contributions:
                    contrib = contribs.get(ec.contributor_id)
                    if contrib:
                        c_key = enqueue_neighbor("contributor", contrib, next_hop)
                        if c_key:
                            add_edge(expr_key, c_key, "contributed_by", "contributors", ec.role)

        if "lod" in allowed_categories:
            GraphService._add_semantic_links("expression", expr.id, expr_key, next_hop, try_add_node, add_edge)

    @staticmethod
    def _expand_manifestation(
        manifestation: Manifestation,
        man_key: str,
        next_hop: int,
        allowed_categories: set[str],
        viewer_user_id: uuid.UUID | str | None,
        viewer_friend_ids: set[uuid.UUID],
        opted_out_user_ids: set[uuid.UUID],
        enqueue_neighbor: Any,
        try_add_node: Any,
        add_edge: Any,
    ) -> None:
        if "frbr" in allowed_categories:
            parent_expr = manifestation.expression or db.session.get(Expression, manifestation.expression_id)
            if parent_expr:
                e_key = enqueue_neighbor("expression", parent_expr, next_hop)
                if e_key:
                    add_edge(man_key, e_key, "embodies", "frbr", "embodies")

            vis_clauses = [and_(Item.visibility == "public", Item.is_hidden.is_(False))]
            viewer_uuid: uuid.UUID | None = None
            if viewer_user_id:
                try:
                    viewer_uuid = uuid.UUID(str(viewer_user_id)) if not isinstance(viewer_user_id, uuid.UUID) else viewer_user_id
                except (ValueError, TypeError):
                    viewer_uuid = None
            if viewer_uuid is not None:
                vis_clauses.append(Item.owner_id == viewer_uuid)
                if viewer_friend_ids:
                    vis_clauses.append(and_(Item.owner_id.in_(viewer_friend_ids), Item.visibility.in_(("friends_only", "shared"))))

            items = (
                db.session.execute(
                    select(Item)
                    .where(Item.manifestation_id == manifestation.id, or_(*vis_clauses))
                    .order_by(Item.id.asc())
                    .limit(MAX_GRAPH_NODES)
                )
                .scalars()
                .all()
            )
            for item in items:
                if is_item_visible_to_viewer(item, viewer_user_id, viewer_friend_ids, opted_out_user_ids):
                    i_key = enqueue_neighbor("item", item, next_hop)
                    if i_key:
                        add_edge(i_key, man_key, "exemplifies", "frbr", "exemplifies")

        if "maps" in allowed_categories:
            meta = manifestation.meta if isinstance(manifestation.meta, dict) else {}
            attachments = meta.get("map_attachments") or []
            if isinstance(attachments, list):
                for idx, att in enumerate(attachments):
                    if isinstance(att, dict):
                        map_payload = _map_node_dict(manifestation.id, idx, att, hop=next_hop)
                        if try_add_node(map_payload["id"], map_payload):
                            add_edge(man_key, map_payload["id"], "has_map", "maps", str(att.get("type") or "map"))

        if "contributors" in allowed_categories:
            contributions = (
                db.session.execute(
                    select(ManifestationContribution)
                    .where(ManifestationContribution.manifestation_id == manifestation.id)
                    .order_by(ManifestationContribution.sequence.asc(), ManifestationContribution.id.asc())
                )
                .scalars()
                .all()
            )
            if contributions:
                contrib_ids = [mc.contributor_id for mc in contributions]
                contribs = {c.id: c for c in db.session.execute(select(Contributor).where(Contributor.id.in_(contrib_ids))).scalars().all()}
                for mc in contributions:
                    contrib = contribs.get(mc.contributor_id)
                    if contrib:
                        c_key = enqueue_neighbor("contributor", contrib, next_hop)
                        if c_key:
                            add_edge(man_key, c_key, "contributed_by", "contributors", mc.role)

        if "lod" in allowed_categories:
            GraphService._add_semantic_links("manifestation", manifestation.id, man_key, next_hop, try_add_node, add_edge)

    @staticmethod
    def _expand_item(
        item: Item,
        item_key: str,
        next_hop: int,
        allowed_categories: set[str],
        enqueue_neighbor: Any,
        add_edge: Any,
    ) -> None:
        if "frbr" in allowed_categories:
            manifestation = db.session.get(Manifestation, item.manifestation_id)
            if manifestation:
                m_key = enqueue_neighbor("manifestation", manifestation, next_hop)
                if m_key:
                    add_edge(item_key, m_key, "exemplifies", "frbr", "exemplifies")

        if "parts_expansions" in allowed_categories:
            reverse_aggs = (
                db.session.execute(
                    select(ContainerAggregation)
                    .where(
                        ContainerAggregation.aggregated_type == "item",
                        ContainerAggregation.aggregated_item_id == item.id,
                    )
                    .order_by(ContainerAggregation.id.asc())
                )
                .scalars()
                .all()
            )
            if reverse_aggs:
                container_ids = [agg.container_work_id for agg in reverse_aggs]
                containers = {w.id: w for w in db.session.execute(select(Work).where(Work.id.in_(container_ids))).scalars().all()}
                for agg in reverse_aggs:
                    container = containers.get(agg.container_work_id)
                    if container:
                        c_key = enqueue_neighbor("work", container, next_hop)
                        if c_key:
                            add_edge(c_key, item_key, "has_part", "parts_expansions", agg.component_name)

    @staticmethod
    def _expand_contributor(
        contributor: Contributor,
        contrib_key: str,
        next_hop: int,
        allowed_categories: set[str],
        enqueue_neighbor: Any,
        try_add_node: Any,
        add_edge: Any,
    ) -> None:
        if "contributors" in allowed_categories:
            work_contribs = (
                db.session.execute(
                    select(WorkContribution)
                    .where(WorkContribution.contributor_id == contributor.id)
                    .order_by(WorkContribution.sequence.asc(), WorkContribution.id.asc())
                    .limit(MAX_GRAPH_NODES)
                )
                .scalars()
                .all()
            )
            if work_contribs:
                work_ids = [wc.work_id for wc in work_contribs]
                works_by_id = {w.id: w for w in db.session.execute(select(Work).where(Work.id.in_(work_ids))).scalars().all()}
                for wc in work_contribs:
                    w = works_by_id.get(wc.work_id)
                    if w:
                        w_key = enqueue_neighbor("work", w, next_hop)
                        if w_key:
                            add_edge(w_key, contrib_key, "contributed_by", "contributors", wc.role)

            expr_contribs = (
                db.session.execute(
                    select(ExpressionContribution)
                    .where(ExpressionContribution.contributor_id == contributor.id)
                    .order_by(ExpressionContribution.sequence.asc(), ExpressionContribution.id.asc())
                    .limit(MAX_GRAPH_NODES)
                )
                .scalars()
                .all()
            )
            if expr_contribs:
                expr_ids = [ec.expression_id for ec in expr_contribs]
                exprs_by_id = {
                    e.id: e
                    for e in db.session.execute(
                        select(Expression).options(selectinload(Expression.work)).where(Expression.id.in_(expr_ids))
                    )
                    .scalars()
                    .all()
                }
                for ec in expr_contribs:
                    e = exprs_by_id.get(ec.expression_id)
                    if e:
                        e_key = enqueue_neighbor("expression", e, next_hop)
                        if e_key:
                            add_edge(e_key, contrib_key, "contributed_by", "contributors", ec.role)

            man_contribs = (
                db.session.execute(
                    select(ManifestationContribution)
                    .where(ManifestationContribution.contributor_id == contributor.id)
                    .order_by(ManifestationContribution.sequence.asc(), ManifestationContribution.id.asc())
                    .limit(MAX_GRAPH_NODES)
                )
                .scalars()
                .all()
            )
            if man_contribs:
                man_ids = [mc.manifestation_id for mc in man_contribs]
                mans_by_id = {
                    m.id: m
                    for m in db.session.execute(
                        select(Manifestation)
                        .options(selectinload(Manifestation.expression).selectinload(Expression.work))
                        .where(Manifestation.id.in_(man_ids))
                    )
                    .scalars()
                    .all()
                }
                for mc in man_contribs:
                    m = mans_by_id.get(mc.manifestation_id)
                    if m:
                        m_key = enqueue_neighbor("manifestation", m, next_hop)
                        if m_key:
                            add_edge(m_key, contrib_key, "contributed_by", "contributors", mc.role)

        if "lod" in allowed_categories:
            GraphService._add_semantic_links("contributor", contributor.id, contrib_key, next_hop, try_add_node, add_edge)

    @staticmethod
    def search_root_candidates(
        query: str,
        *,
        types: list[str] | None = None,
        limit: int = 10,
        viewer_user_id: uuid.UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        """Search visibility-safe FRBR & contributor root candidates for the graph picker."""
        q_clean = (query or "").strip()
        if not q_clean:
            return []

        effective_limit = max(1, min(int(limit), 25))
        folded = normalize_diacritics(q_clean)
        pattern = f"%{escape_ilike_term(folded)}%"
        requested = list(dict.fromkeys(types)) if types else list(DEFAULT_GRAPH_SEARCH_TYPES)

        results: list[dict[str, Any]] = []
        seen_contributors: set[int] = set()

        for ent_type in requested:
            if len(results) >= effective_limit:
                break
            remaining = effective_limit - len(results)

            if ent_type in ("person", "contributor"):
                stmt = (
                    select(Contributor)
                    .where(db.func.immutable_unaccent(func.coalesce(Contributor.name, "")).ilike(pattern, escape="\\"))
                    .order_by(Contributor.id.asc())
                    .limit(remaining)
                )
                for c in db.session.execute(stmt).scalars().all():
                    if c.id in seen_contributors:
                        continue
                    seen_contributors.add(c.id)
                    c_type = c.type or "person"
                    results.append(
                        {
                            "entity_type": ent_type,
                            "entity_id": c.id,
                            "label": c.name or f"Contributor #{c.id}",
                            "subtitle": c_type,
                            "contributor_type": c_type,
                            "url": f"/collection?q={quote_plus(c.name)}" if c.name else None,
                        }
                    )

            elif ent_type == "series":
                series_cond = or_(
                    Work.work_kind == "series",
                    exists(select(WorkSeriesMembership.id).where(WorkSeriesMembership.series_work_id == Work.id)),
                    exists(select(WorkPart.container_work_id).where(WorkPart.container_work_id == Work.id)),
                )
                stmt = (
                    select(Work)
                    .where(
                        series_cond,
                        or_(
                            db.func.immutable_unaccent(func.coalesce(Work.title, "")).ilike(pattern, escape="\\"),
                            db.func.immutable_unaccent(func.coalesce(Work.issn, "")).ilike(pattern, escape="\\"),
                        ),
                    )
                    .order_by(Work.id.asc())
                    .limit(remaining)
                )
                for w in db.session.execute(stmt).scalars().all():
                    results.append(
                        {
                            "entity_type": "series",
                            "entity_id": w.id,
                            "label": w.title or f"Series #{w.id}",
                            "subtitle": f"ISSN {w.issn}" if w.issn else (w.work_kind or "series"),
                            "work_kind": w.work_kind,
                            "issn": w.issn,
                            "url": f"/work/{w.id}",
                        }
                    )

            elif ent_type == "work":
                stmt = (
                    select(Work)
                    .where(
                        or_(
                            db.func.immutable_unaccent(func.coalesce(Work.title, "")).ilike(pattern, escape="\\"),
                            db.func.immutable_unaccent(func.coalesce(Work.issn, "")).ilike(pattern, escape="\\"),
                        )
                    )
                    .order_by(Work.id.asc())
                    .limit(remaining)
                )
                for w in db.session.execute(stmt).scalars().all():
                    authors = w.meta.get("authors", []) if isinstance(w.meta, dict) else []
                    sub = ", ".join(str(a) for a in authors[:2] if a) if isinstance(authors, list) and authors else w.work_kind
                    results.append(
                        {
                            "entity_type": "work",
                            "entity_id": w.id,
                            "label": w.title or f"Work #{w.id}",
                            "subtitle": sub,
                            "work_kind": w.work_kind,
                            "issn": w.issn,
                            "url": f"/work/{w.id}",
                        }
                    )

            elif ent_type == "expression":
                stmt = (
                    select(Expression)
                    .options(selectinload(Expression.work))
                    .join(Work, Expression.work_id == Work.id)
                    .where(
                        or_(
                            db.func.immutable_unaccent(func.coalesce(Work.title, "")).ilike(pattern, escape="\\"),
                            db.func.immutable_unaccent(func.coalesce(Expression.language, "")).ilike(pattern, escape="\\"),
                            db.func.immutable_unaccent(func.coalesce(Expression.content_type, "")).ilike(pattern, escape="\\"),
                        )
                    )
                    .order_by(Expression.id.asc())
                    .limit(remaining)
                )
                for e in db.session.execute(stmt).scalars().all():
                    w_title = e.work.title if e.work else f"Work #{e.work_id}"
                    details = [p for p in (e.content_type, e.language, e.kind) if p]
                    results.append(
                        {
                            "entity_type": "expression",
                            "entity_id": e.id,
                            "label": f"{w_title} ({e.language or e.content_type or 'Expression'})",
                            "subtitle": " • ".join(details) if details else "Expression",
                            "url": f"/expression/{e.id}",
                        }
                    )

            elif ent_type == "manifestation":
                stmt = (
                    select(Manifestation)
                    .options(selectinload(Manifestation.expression).selectinload(Expression.work))
                    .join(Expression, Manifestation.expression_id == Expression.id)
                    .join(Work, Expression.work_id == Work.id)
                    .where(
                        or_(
                            db.func.immutable_unaccent(func.coalesce(_meta_text(Manifestation.meta), "")).ilike(pattern, escape="\\"),
                            db.func.immutable_unaccent(func.coalesce(Work.title, "")).ilike(pattern, escape="\\"),
                            func.coalesce(Manifestation.isbn13, "").ilike(pattern, escape="\\"),
                            func.coalesce(Manifestation.barcode, "").ilike(pattern, escape="\\"),
                            func.coalesce(Manifestation.full_barcode, "").ilike(pattern, escape="\\"),
                        )
                    )
                    .order_by(Manifestation.id.asc())
                    .limit(remaining)
                )
                for m in db.session.execute(stmt).scalars().all():
                    details = [p for p in (m.format, m.publisher, str(m.publication_year) if m.publication_year else None) if p]
                    results.append(
                        {
                            "entity_type": "manifestation",
                            "entity_id": m.id,
                            "label": m.title or f"Manifestation #{m.id}",
                            "subtitle": " • ".join(details) if details else None,
                            "url": f"/manifestation/{m.id}",
                        }
                    )

            elif ent_type == "item":
                viewer_uuid: uuid.UUID | None = None
                if viewer_user_id:
                    try:
                        viewer_uuid = uuid.UUID(str(viewer_user_id)) if not isinstance(viewer_user_id, uuid.UUID) else viewer_user_id
                    except (ValueError, TypeError):
                        viewer_uuid = None
                viewer_friend_ids = get_friend_user_ids(viewer_uuid) if viewer_uuid else set()
                opted_out_user_ids = get_federation_opted_out_user_ids()
                vis_where = build_sql_item_visibility_clause(viewer_uuid, viewer_friend_ids, opted_out_user_ids)

                stmt = (
                    select(Item)
                    .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
                    .join(Manifestation, Item.manifestation_id == Manifestation.id)
                    .join(Expression, Manifestation.expression_id == Expression.id)
                    .join(Work, Expression.work_id == Work.id)
                    .where(
                        vis_where,
                        or_(
                            db.func.immutable_unaccent(func.coalesce(_meta_text(Manifestation.meta), "")).ilike(pattern, escape="\\"),
                            db.func.immutable_unaccent(func.coalesce(Work.title, "")).ilike(pattern, escape="\\"),
                        ),
                    )
                    .order_by(Item.id.asc())
                    .limit(remaining)
                )
                for it in db.session.execute(stmt).scalars().all():
                    man_title = it.manifestation.title if it.manifestation and it.manifestation.title else None
                    eff_vis = (it.visibility or ("private" if it.is_hidden else "public")).lower()
                    details = [p for p in (it.collection_status, it.status, eff_vis) if p]
                    results.append(
                        {
                            "entity_type": "item",
                            "entity_id": it.id,
                            "label": f"{man_title} (Copy #{it.id})" if man_title else f"Copy #{it.id}",
                            "subtitle": " • ".join(details) if details else "Item",
                            "url": f"/item/{it.id}",
                        }
                    )

        return results[:effective_limit]
