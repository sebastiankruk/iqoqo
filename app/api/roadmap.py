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

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.decorators import require_auth
from app.db.core import db
from app.db.roadmap import ReadingRoadmap, RoadmapItem

logger = logging.getLogger(__name__)

roadmap_bp = Blueprint("roadmap", __name__, url_prefix="/api/v1/roadmaps")


@roadmap_bp.route("", methods=["GET"])
@require_auth
def get_roadmaps() -> Response | tuple[Response, int]:
    """Retrieves all pipelines configured by the currently authenticated user session."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Authentication required", "code": 401}), 401

    try:
        stmt = select(ReadingRoadmap).filter(ReadingRoadmap.user_id == user_id)
        roadmaps = db.session.scalars(stmt).unique().all()
        return jsonify([r.to_dict() for r in roadmaps]), 200
    except SQLAlchemyError as e:
        logger.error("Error fetching roadmaps: %s", e)
        return jsonify({"error": "Database error", "code": 500}), 500


@roadmap_bp.route("", methods=["POST"])
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
            work_id=data.get("work_id"),
            manifestation_id=data.get("manifestation_id"),
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

        items_stmt = select(RoadmapItem).filter(RoadmapItem.roadmap_id == item.roadmap_id).order_by(RoadmapItem.position)
        items = list(db.session.scalars(items_stmt).all())

        if item in items:
            items.remove(item)

        # Insert at the 0-indexed position (new_position - 1)
        target_idx = max(0, min(new_position - 1, len(items)))
        items.insert(target_idx, item)

        for idx, node in enumerate(items):
            node.position = idx + 1

        db.session.commit()
        return jsonify({"success": True}), 200
    except SQLAlchemyError as e:
        logger.error("Error reordering roadmap item: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database error", "code": 500}), 500
