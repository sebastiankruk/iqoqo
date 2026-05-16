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

from flask import Response, g, jsonify
from sqlalchemy.orm import selectinload

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.db.models import Expression, Item, Manifestation, db


@api_bp.route("/works/shelf", methods=["GET"])
@require_auth
def get_user_works() -> Response:
    """
    Returns a specialized view of the user's shelf grouped by Conceptual Work.
    This resolves the F15 Complex Work/Series requirement by allowing the UI
    to display a 'Series' or 'Work' card that contains multiple manifestations.
    """
    user_id = getattr(g, "user_id", None)

    items = db.session.query(Item).options(
        selectinload(Item.manifestation)
        .selectinload(Manifestation.expression)
        .selectinload(Expression.work)
    ).filter(Item.owner_id == user_id).all()

    works_map = {}
    for item in items:
        if not item.manifestation or not item.manifestation.expression or not item.manifestation.expression.work:
            continue

        work = item.manifestation.expression.work
        if work.id not in works_map:
            works_map[work.id] = {
                "work_id": work.id,
                "title": work.title,
                "creators": work.meta.get("creators", []) if work.meta else [],
                "owned_manifestations": [],
                "total_items": 0,
            }

        man_dict = next(
            (m for m in works_map[work.id]["owned_manifestations"] if m["manifestation_id"] == item.manifestation.id),
            None
        )
        if not man_dict:
            works_map[work.id]["owned_manifestations"].append({
                "manifestation_id": item.manifestation.id,
                "format": item.manifestation.meta.get("format", "Unknown") if item.manifestation.meta else "Unknown",
                "cover_url": item.manifestation.cover_url,
            })

        works_map[work.id]["total_items"] += 1

    return jsonify({
        "success": True,
        "data": list(works_map.values()),
        "total": len(works_map),
    })
