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
"""
API endpoints managing the creation, prioritization, and status of items inside a roadmap.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.api.decorators import require_auth
from app.core.limiter import limiter
from app.db.core import Expression, Item, Manifestation, Work, db
from app.db.roadmap import ReadingRoadmap, RoadmapItem

logger = logging.getLogger(__name__)

roadmap_bp = Blueprint("roadmap", __name__, url_prefix="/api/v1/roadmaps")


def _validate_target_payload(data: dict[str, Any], user_id: Any) -> tuple[dict[str, int | None] | None, tuple[Response, int] | None]:
    """Validates exactly one positive integer target reference exists and is authorized.

    Returns (targets_dict, None) on success, or (None, (error_response, status_code)) on error.
    """
    target_keys = ("work_id", "expression_id", "manifestation_id", "item_id")
    provided = {k: data[k] for k in target_keys if data.get(k) is not None}
    if len(provided) != 1:
        return None, (
            jsonify(
                {
                    "error": "Exactly one of work_id, expression_id, manifestation_id, or item_id must be provided",
                    "code": 400,
                }
            ),
            400,
        )

    key, val = next(iter(provided.items()))
    if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
        return None, (
            jsonify({"error": f"Invalid {key}: must be a positive integer", "code": 400}),
            400,
        )

    if key == "work_id":
        work = db.session.get(Work, val)
        if not work:
            return None, (jsonify({"error": "Work not found", "code": 404}), 404)
    elif key == "expression_id":
        expr = db.session.get(Expression, val)
        if not expr:
            return None, (jsonify({"error": "Expression not found", "code": 404}), 404)
    elif key == "manifestation_id":
        man = db.session.get(Manifestation, val)
        if not man:
            return None, (jsonify({"error": "Manifestation not found", "code": 404}), 404)
    elif key == "item_id":
        item = db.session.get(Item, val)
        if not item or str(item.owner_id) != str(user_id):
            return None, (jsonify({"error": "Item not found", "code": 404}), 404)

    targets = {
        "work_id": provided.get("work_id"),
        "expression_id": provided.get("expression_id"),
        "manifestation_id": provided.get("manifestation_id"),
        "item_id": provided.get("item_id"),
    }
    return targets, None


@roadmap_bp.route("", methods=["GET"])
@limiter.limit("60 per minute")
@require_auth
def get_roadmaps() -> Response | tuple[Response, int]:
    """Retrieves all pipelines configured by the currently authenticated user session."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = (
            select(ReadingRoadmap)
            .filter(ReadingRoadmap.user_id == user_id)
            .order_by(ReadingRoadmap.created_at.desc(), ReadingRoadmap.id.desc())
        )
        roadmaps = db.session.scalars(stmt).unique().all()
        return jsonify([r.to_dict() for r in roadmaps]), 200
    except SQLAlchemyError as e:
        logger.error("Error fetching roadmaps: %s", e)
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("", methods=["POST"])
@limiter.limit("30 per minute")
@require_auth
def create_roadmap() -> Response | tuple[Response, int]:
    """Creates a clean roadmap bucket for personal item sequencing tracking execution."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    data = request.get_json() or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "Missing title configuration parameters", "code": 400}), 400

    roadmap = ReadingRoadmap(
        user_id=user_id,
        title=title,
        description=data.get("description"),
        is_public=data.get("is_public", False),
    )
    try:
        db.session.add(roadmap)
        db.session.commit()
        return jsonify(roadmap.to_dict()), 201
    except SQLAlchemyError as e:
        logger.error("Error creating roadmap: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("/<int:roadmap_id>/items", methods=["POST"])
@limiter.limit("30 per minute")
@require_auth
def add_item_to_roadmap(roadmap_id: int) -> Response | tuple[Response, int]:
    """Appends an item at the final tail boundary of the tracking collection order chain."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = select(ReadingRoadmap).filter(ReadingRoadmap.id == roadmap_id, ReadingRoadmap.user_id == user_id)
        roadmap = db.session.scalars(stmt).first()
        if not roadmap:
            return jsonify({"error": "Roadmap not found", "code": 404}), 404

        data = request.get_json() or {}

        target_refs, err = _validate_target_payload(data, user_id)
        if err:
            return err

        # Pylint & SQLAlchemy func.count E1102 warning disable rule:
        count_stmt = select(func.count(RoadmapItem.id)).filter(RoadmapItem.roadmap_id == roadmap.id)  # pylint: disable=not-callable
        current_count = db.session.scalar(count_stmt) or 0

        target_date_str = data.get("target_date")
        target_date = None
        if target_date_str:
            from datetime import datetime

            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Invalid date format, use YYYY-MM-DD", "code": 400}), 400

        item = RoadmapItem(
            roadmap_id=roadmap.id,
            work_id=target_refs["work_id"],
            expression_id=target_refs["expression_id"],
            manifestation_id=target_refs["manifestation_id"],
            item_id=target_refs["item_id"],
            position=current_count + 1,
            notes=data.get("notes"),
            target_date=target_date,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict()), 201
    except SQLAlchemyError as e:
        logger.error("Error adding item to roadmap: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("/items/<int:item_id>/position", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_auth
def reorder_roadmap_item(item_id: int) -> Response | tuple[Response, int]:
    """Handles mutation reposition commands safely minimizing relational row collateral write shifts."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = select(RoadmapItem).join(ReadingRoadmap).filter(RoadmapItem.id == item_id, ReadingRoadmap.user_id == user_id)
        item = db.session.scalars(stmt).first()
        if not item:
            return jsonify({"error": "Roadmap item not found", "code": 404}), 404

        data = request.get_json() or {}
        new_position_val = data.get("position")
        if new_position_val is None:
            return jsonify({"error": "Invalid target execution priority array coordinates", "code": 400}), 400

        try:
            new_position = int(new_position_val)
            if new_position < 1:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"error": "Position must be a valid integer greater than or equal to 1", "code": 400}), 400

        count_stmt = select(func.count()).where(RoadmapItem.roadmap_id == item.roadmap_id)  # pylint: disable=not-callable
        total_items = db.session.scalar(count_stmt) or 1
        target_position = max(1, min(new_position, total_items))

        old_position = item.position
        if old_position != target_position:
            if old_position > target_position:
                # Moving item up (e.g. from 5 to 2): shift items in [target, old - 1] by +1
                db.session.execute(
                    update(RoadmapItem)
                    .where(
                        RoadmapItem.roadmap_id == item.roadmap_id,
                        RoadmapItem.position >= target_position,
                        RoadmapItem.position < old_position,
                    )
                    .values(position=RoadmapItem.position + 1)
                )
            else:
                # Moving item down (e.g. from 2 to 5): shift items in [old + 1, target] by -1
                db.session.execute(
                    update(RoadmapItem)
                    .where(
                        RoadmapItem.roadmap_id == item.roadmap_id,
                        RoadmapItem.position <= target_position,
                        RoadmapItem.position > old_position,
                    )
                    .values(position=RoadmapItem.position - 1)
                )

            item.position = target_position
            db.session.commit()

        return jsonify({"success": True}), 200
    except SQLAlchemyError as e:
        logger.error("Error reordering roadmap item: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("/<int:roadmap_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_auth
def delete_roadmap(roadmap_id: int) -> Response | tuple[Response, int]:
    """Deletes a roadmap pipeline and cascades to its items."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = select(ReadingRoadmap).filter(ReadingRoadmap.id == roadmap_id, ReadingRoadmap.user_id == user_id)
        roadmap = db.session.scalars(stmt).first()
        if not roadmap:
            return jsonify({"error": "Roadmap not found", "code": 404}), 404

        db.session.delete(roadmap)
        db.session.commit()
        return jsonify({"success": True}), 200
    except SQLAlchemyError as e:
        logger.error("Error deleting roadmap: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("/<int:roadmap_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_auth
def get_roadmap(roadmap_id: int) -> Response | tuple[Response, int]:
    """Retrieves a single roadmap pipeline by ID."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = select(ReadingRoadmap).filter(ReadingRoadmap.id == roadmap_id, ReadingRoadmap.user_id == user_id)
        roadmap = db.session.scalars(stmt).first()
        if not roadmap:
            return jsonify({"error": "Roadmap not found", "code": 404}), 404

        return jsonify(roadmap.to_dict()), 200
    except SQLAlchemyError as e:
        logger.error("Error fetching roadmap: %s", e)
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("/items/<int:item_id>", methods=["PATCH"])
@roadmap_bp.route("/items/<int:item_id>/target", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_auth
def update_roadmap_item_target(item_id: int) -> Response | tuple[Response, int]:
    """Replaces the FRBR target of a roadmap item while preserving position, status, notes, and dates."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = select(RoadmapItem).join(ReadingRoadmap).filter(RoadmapItem.id == item_id, ReadingRoadmap.user_id == user_id)
        item = db.session.scalars(stmt).first()
        if not item:
            return jsonify({"error": "Roadmap item not found", "code": 404}), 404

        data = request.get_json() or {}
        target_refs, err = _validate_target_payload(data, user_id)
        if err:
            return err

        item.work_id = target_refs["work_id"]
        item.expression_id = target_refs["expression_id"]
        item.manifestation_id = target_refs["manifestation_id"]
        item.item_id = target_refs["item_id"]

        db.session.commit()
        return jsonify(item.to_dict()), 200
    except SQLAlchemyError as e:
        logger.error("Error updating roadmap item target: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("/items/<int:item_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_auth
def delete_roadmap_item(item_id: int) -> Response | tuple[Response, int]:
    """Deletes an individual roadmap entry and compacts subsequent positions in the roadmap."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = select(RoadmapItem).join(ReadingRoadmap).filter(RoadmapItem.id == item_id, ReadingRoadmap.user_id == user_id)
        item = db.session.scalars(stmt).first()
        if not item:
            return jsonify({"error": "Roadmap item not found", "code": 404}), 404

        old_position = item.position
        roadmap_id = item.roadmap_id

        db.session.delete(item)
        # Compact positions for all items after the deleted one in this roadmap
        db.session.execute(
            update(RoadmapItem)
            .where(
                RoadmapItem.roadmap_id == roadmap_id,
                RoadmapItem.position > old_position,
            )
            .values(position=RoadmapItem.position - 1)
        )
        db.session.commit()
        return jsonify({"success": True}), 200
    except SQLAlchemyError as e:
        logger.error("Error deleting roadmap item: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500
