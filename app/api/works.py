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
from app.api.decorators import require_auth, require_permission
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

    items = (
        db.session.query(Item)
        .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
        .filter(Item.owner_id == user_id)
        .all()
    )

    works_map: dict[int, dict] = {}
    for item in items:
        if not item.manifestation or not item.manifestation.expression or not item.manifestation.expression.work:
            continue

        expr = item.manifestation.expression
        work = expr.work

        # Apply category filter at the expression level
        if category and (expr.content_type or "").lower() != category:
            continue

        creators: list[str] = []
        if work.meta:
            creators = work.meta.get("creators") or work.meta.get("authors") or []

        # Apply search filter against title and creator names
        if search_q:
            haystack = (work.title or "").lower() + " " + " ".join(creators).lower()
            if search_q not in haystack:
                continue

        if work.id not in works_map:
            works_map[work.id] = {
                "work_id": work.id,
                "title": work.title,
                "creators": creators,
                "owned_manifestations": [],
                "total_items": 0,
            }

        man_dict = next((m for m in works_map[work.id]["owned_manifestations"] if m["manifestation_id"] == item.manifestation.id), None)
        if not man_dict:
            works_map[work.id]["owned_manifestations"].append(
                {
                    "manifestation_id": item.manifestation.id,
                    "format": item.manifestation.meta.get("format", "Unknown") if item.manifestation.meta else "Unknown",
                    "cover_url": item.manifestation.cover_url,
                }
            )

        works_map[work.id]["total_items"] += 1

    return jsonify(
        {
            "success": True,
            "data": list(works_map.values()),
            "total": len(works_map),
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

    items = (
        db.session.query(Item)
        .options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
        .filter(Item.owner_id == user_id)
        .all()
    )

    expr_map: dict[int, dict] = {}
    for item in items:
        if not item.manifestation or not item.manifestation.expression:
            continue

        expr = item.manifestation.expression
        work = expr.work

        # Apply category filter at the expression level
        if category and (expr.content_type or "").lower() != category:
            continue

        creators: list[str] = []
        if work and work.meta:
            creators = work.meta.get("creators") or work.meta.get("authors") or []

        work_title = work.title if work else "Unknown"

        # Apply search filter against work title and creator names
        if search_q:
            haystack = work_title.lower() + " " + " ".join(creators).lower()
            if search_q not in haystack:
                continue

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
            expr_map[expr.id]["owned_manifestations"].append(
                {
                    "manifestation_id": item.manifestation.id,
                    "format": item.manifestation.meta.get("format", "Unknown") if item.manifestation.meta else "Unknown",
                    "cover_url": item.manifestation.cover_url,
                }
            )

        expr_map[expr.id]["total_items"] += 1

    return jsonify(
        {
            "success": True,
            "data": list(expr_map.values()),
            "total": len(expr_map),
        }
    )


@api_bp.route("/works/<int:work_id>/parts", methods=["GET"])
def get_work_parts(work_id: int) -> Response | tuple[Response, int]:
    """Get the series/parts associated with a given complex work."""
    work = db.session.get(Work, work_id)
    if not work:
        return jsonify({"error": "Work not found", "code": 404}), 404

    parts = []
    for wp in work.parts:  # type: ignore[attr-defined]
        part_work = wp.part
        parts.append(
            {
                "part_work_id": part_work.id,
                "title": part_work.title,
                "sequence": wp.sequence,
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
