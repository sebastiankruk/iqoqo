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
"""Authenticated sharing management API."""

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from app.api.decorators import require_auth
from app.db.models import SharedCollection, db

sharing_bp = Blueprint("sharing", __name__, url_prefix="/sharing")


@sharing_bp.route("/", methods=["GET"])
@require_auth
def list_shared_collections():
    """List shared collections for the current user."""
    user_id = getattr(g, "user_id", None)
    stmt = select(SharedCollection).where(SharedCollection.user_id == user_id)
    collections = db.session.execute(stmt).scalars().all()
    return jsonify({"success": True, "data": [c.to_dict() for c in collections]})


@sharing_bp.route("/", methods=["POST"])
@require_auth
def create_shared_collection():
    """Create a new shared collection."""
    data = request.get_json() or {}
    user_id = getattr(g, "user_id", None)

    if "name" not in data:
        return jsonify({"error": "Missing name", "code": 400}), 400

    collection = SharedCollection(
        user_id=user_id,
        name=data["name"],
        description=data.get("description"),
        filters=data.get("filters", {}),
    )
    db.session.add(collection)
    db.session.commit()
    return jsonify({"success": True, "data": collection.to_dict()})


@sharing_bp.route("/<int:collection_id>", methods=["DELETE"])
@require_auth
def delete_shared_collection(collection_id: int):
    """Delete a shared collection."""
    user_id = getattr(g, "user_id", None)
    collection = db.session.get(SharedCollection, collection_id)

    if not collection or str(collection.user_id) != str(user_id):
        return jsonify({"error": "Collection not found", "code": 404}), 404

    db.session.delete(collection)
    db.session.commit()
    return jsonify({"success": True, "message": "Collection deleted"})
