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

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.friend_service import get_friend_user_ids
from app.db.contributions import Contributor, ExpressionContribution, WorkContribution, WorkPart, WorkSeriesMembership
from app.db.core import Expression, Item, Manifestation, SemanticLink, Work, WorkExpansionLink
from app.db.games import ContainerAggregation
from app.db.models import db
from app.db.video import ManifestationContribution

VALID_GRAPH_ENTITY_TYPES: tuple[str, ...] = ("work", "expression", "manifestation", "item")
VALID_EDGE_CATEGORIES: tuple[str, ...] = ("frbr", "series", "parts_expansions", "contributors", "maps", "lod")
MAX_GRAPH_DEPTH = 2
MAX_GRAPH_NODES = 150


def is_item_visible_to_viewer(
    item: Item,
    viewer_user_id: uuid.UUID | str | None,
    viewer_friend_ids: set[uuid.UUID],
) -> bool:
    """Return True if *item* satisfies three-tier visibility rules for *viewer_user_id*."""
    effective_visibility = (item.visibility or ("private" if item.is_hidden else "public")).lower()
    if effective_visibility == "public" and not item.is_hidden:
        return True

    if not viewer_user_id:
        return False

    try:
        viewer_uuid = uuid.UUID(str(viewer_user_id)) if not isinstance(viewer_user_id, uuid.UUID) else viewer_user_id
    except (ValueError, TypeError):
        return False

    if item.owner_id == viewer_uuid:
        return True

    if effective_visibility in ("friends_only", "shared") and item.owner_id in viewer_friend_ids:
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


def _contributor_node_dict(contributor: Contributor, *, hop: int) -> dict[str, Any]:
    return {
        "id": _node_key("contributor", contributor.id),
        "entity_type": "contributor",
        "entity_id": contributor.id,
        "label": contributor.name or f"Contributor #{contributor.id}",
        "subtitle": contributor.type or "person",
        "hop": hop,
        "is_anchor": False,
        "url": f"/collection?q={contributor.name}" if contributor.name else None,
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
        allowed_categories = edge_categories & set(VALID_EDGE_CATEGORIES) if edge_categories is not None else set(VALID_EDGE_CATEGORIES)

        viewer_friend_ids = get_friend_user_ids(viewer_user_id) if viewer_user_id else set()

        anchor_orm = GraphService._load_anchor(norm_type, entity_id, viewer_user_id, viewer_friend_ids)
        if anchor_orm is None:
            return None

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        truncated = False
        queue: deque[tuple[str, Any, int]] = deque()

        root_key = _node_key(norm_type, entity_id)
        nodes[root_key] = GraphService._serialize_node(norm_type, anchor_orm, hop=0, is_anchor=True)
        queue.append((norm_type, anchor_orm, 0))

        def try_add_node(node_key: str, node_payload: dict[str, Any]) -> bool:
            nonlocal truncated
            if node_key in nodes:
                return True
            if len(nodes) >= effective_max_nodes:
                truncated = True
                return False
            nodes[node_key] = node_payload
            return True

        def add_edge(source: str, target: str, relation: str, category: str, label: str | None = None) -> None:
            if source not in nodes or target not in nodes:
                return
            edge_sig = (source, target, relation)
            if edge_sig in seen_edges:
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

        while queue:
            cur_type, cur_orm, cur_hop = queue.popleft()
            if cur_hop >= effective_depth:
                continue
            next_hop = cur_hop + 1
            cur_key = _node_key(cur_type, cur_orm.id)

            if cur_type == "work":
                GraphService._expand_work(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    viewer_user_id,
                    viewer_friend_ids,
                    enqueue_neighbor,
                    try_add_node,
                    add_edge,
                )
            elif cur_type == "expression":
                GraphService._expand_expression(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    enqueue_neighbor,
                    try_add_node,
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
                    enqueue_neighbor,
                    try_add_node,
                    add_edge,
                )
            elif cur_type == "item":
                GraphService._expand_item(
                    cur_orm,
                    cur_key,
                    next_hop,
                    allowed_categories,
                    enqueue_neighbor,
                    add_edge,
                )

        return {
            "anchor": {"entity_type": norm_type, "entity_id": entity_id, "node_id": root_key},
            "nodes": list(nodes.values()),
            "edges": edges,
            "meta": {
                "depth": effective_depth,
                "requested_depth": requested_depth,
                "max_nodes": effective_max_nodes,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "truncated": truncated,
            },
        }

    @staticmethod
    def _load_anchor(
        entity_type: str,
        entity_id: int,
        viewer_user_id: uuid.UUID | str | None,
        viewer_friend_ids: set[uuid.UUID],
    ) -> Any:
        if entity_type == "work":
            return db.session.get(Work, entity_id)
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
            if item is None or not is_item_visible_to_viewer(item, viewer_user_id, viewer_friend_ids):
                return None
            return item
        return None

    @staticmethod
    def _serialize_node(entity_type: str, orm_obj: Any, *, hop: int, is_anchor: bool) -> dict[str, Any]:
        if entity_type == "work":
            return _work_node_dict(orm_obj, hop=hop, is_anchor=is_anchor)
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
            for wp in parts:
                part_work = db.session.get(Work, wp.part_work_id)
                if part_work:
                    p_key = enqueue_neighbor("work", part_work, next_hop)
                    if p_key:
                        add_edge(work_key, p_key, "has_part", "parts_expansions", f"has part (#{wp.sequence or 0})")

            containers = (
                db.session.execute(select(WorkPart).where(WorkPart.part_work_id == work.id).order_by(WorkPart.container_work_id.asc()))
                .scalars()
                .all()
            )
            for wp in containers:
                container_work = db.session.get(Work, wp.container_work_id)
                if container_work:
                    c_key = enqueue_neighbor("work", container_work, next_hop)
                    if c_key:
                        add_edge(c_key, work_key, "has_part", "parts_expansions", f"has part (#{wp.sequence or 0})")

            base_link = (
                db.session.execute(select(WorkExpansionLink).where(WorkExpansionLink.expansion_work_id == work.id)).scalars().first()
            )
            if base_link and base_link.base_work:
                b_key = enqueue_neighbor("work", base_link.base_work, next_hop)
                if b_key:
                    add_edge(work_key, b_key, "is_expansion_of", "parts_expansions", "is expansion of")

            expansion_links = (
                db.session.execute(
                    select(WorkExpansionLink).where(WorkExpansionLink.base_work_id == work.id).order_by(WorkExpansionLink.id.asc())
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
            for wc in contributions:
                contrib = db.session.get(Contributor, wc.contributor_id)
                if contrib:
                    contrib_payload = _contributor_node_dict(contrib, hop=next_hop)
                    if try_add_node(contrib_payload["id"], contrib_payload):
                        add_edge(work_key, contrib_payload["id"], "contributed_by", "contributors", wc.role)

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
            for ec in contributions:
                contrib = db.session.get(Contributor, ec.contributor_id)
                if contrib:
                    contrib_payload = _contributor_node_dict(contrib, hop=next_hop)
                    if try_add_node(contrib_payload["id"], contrib_payload):
                        add_edge(expr_key, contrib_payload["id"], "contributed_by", "contributors", ec.role)

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

            items = (
                db.session.execute(select(Item).where(Item.manifestation_id == manifestation.id).order_by(Item.id.asc())).scalars().all()
            )
            for item in items:
                if is_item_visible_to_viewer(item, viewer_user_id, viewer_friend_ids):
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
            for mc in contributions:
                contrib = db.session.get(Contributor, mc.contributor_id)
                if contrib:
                    contrib_payload = _contributor_node_dict(contrib, hop=next_hop)
                    if try_add_node(contrib_payload["id"], contrib_payload):
                        add_edge(man_key, contrib_payload["id"], "contributed_by", "contributors", mc.role)

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
            for agg in reverse_aggs:
                container = db.session.get(Work, agg.container_work_id)
                if container:
                    c_key = enqueue_neighbor("work", container, next_hop)
                    if c_key:
                        add_edge(c_key, item_key, "has_part", "parts_expansions", agg.component_name)
