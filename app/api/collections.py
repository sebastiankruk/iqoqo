"""API routes for UserCollections."""

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

import logging

from flask import Response, g, jsonify, request
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.api.schemas import UserCollectionCreateSchema, UserCollectionUpdateSchema
from app.db.core import UserCollection, db

logger = logging.getLogger(__name__)


@api_bp.route("/collections", methods=["GET"])
@require_auth
def list_collections() -> Response | tuple[Response, int]:
    """List all collections for the authenticated user."""
    user_id = getattr(g, "user_id", None)
    try:
        collections = db.session.query(UserCollection).filter(UserCollection.owner_id == user_id).all()
        data = [
            {
                "id": c.id,
                "name": c.name,
                "parent_id": c.parent_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in collections
        ]
        return jsonify({"success": True, "collections": data})
    except SQLAlchemyError as e:
        logger.error("Error fetching collections: %s", e)
        return jsonify({"success": False, "error": "Database error"}), 500


@api_bp.route("/collections", methods=["POST"])
@require_auth
def create_collection() -> Response | tuple[Response, int]:
    """Create a new user collection."""
    user_id = getattr(g, "user_id", None)
    try:
        data = UserCollectionCreateSchema(**(request.get_json() or {}))
    except ValidationError as e:
        return jsonify({"success": False, "error": e.errors()}), 400

    if data.parent_id is not None:
        parent_collection = (
            db.session.query(UserCollection).filter(UserCollection.id == data.parent_id, UserCollection.owner_id == user_id).first()
        )
        if not parent_collection:
            return jsonify({"success": False, "error": "Invalid parent collection"}), 400

    new_collection = UserCollection(owner_id=user_id, name=data.name, parent_id=data.parent_id)
    try:
        db.session.add(new_collection)
        db.session.commit()
        return (
            jsonify(
                {
                    "success": True,
                    "collection": {
                        "id": new_collection.id,
                        "name": new_collection.name,
                        "parent_id": new_collection.parent_id,
                    },
                }
            ),
            201,
        )
    except SQLAlchemyError as e:
        logger.error("Error creating collection: %s", e)
        db.session.rollback()
        return jsonify({"success": False, "error": "Database error"}), 500


def _validate_parent_hierarchy(collection_id: int, parent_id: int, user_id) -> str | None:
    """Helper to validate parent collection hierarchy and detect circular references."""
    if parent_id == collection_id:
        return "A collection cannot be its own parent"
    parent_collection = db.session.query(UserCollection).filter(UserCollection.id == parent_id, UserCollection.owner_id == user_id).first()
    if not parent_collection:
        return "Invalid parent collection"

    # Walk up parent ancestor chain to prevent circular references
    curr: UserCollection | None = parent_collection
    while curr is not None:
        if curr.id == collection_id:
            return "Circular reference detected in collection hierarchy"
        if curr.parent_id is not None:
            curr = db.session.query(UserCollection).filter(UserCollection.id == curr.parent_id, UserCollection.owner_id == user_id).first()
        else:
            curr = None
    return None


@api_bp.route("/collections/<int:collection_id>", methods=["PUT"])
@require_auth
def update_collection(collection_id: int) -> Response | tuple[Response, int]:
    """Update an existing user collection."""
    user_id = getattr(g, "user_id", None)
    collection = db.session.query(UserCollection).filter(UserCollection.id == collection_id, UserCollection.owner_id == user_id).first()
    if not collection:
        return jsonify({"success": False, "error": "Collection not found"}), 404

    try:
        data = UserCollectionUpdateSchema(**(request.get_json() or {}))
    except ValidationError as e:
        return jsonify({"success": False, "error": e.errors()}), 400

    if data.name is not None:
        collection.name = data.name
    if data.parent_id is not None:
        err = _validate_parent_hierarchy(collection.id, data.parent_id, user_id)
        if err:
            return jsonify({"success": False, "error": err}), 400
        collection.parent_id = data.parent_id

    try:
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "collection": {
                    "id": collection.id,
                    "name": collection.name,
                    "parent_id": collection.parent_id,
                },
            }
        )
    except SQLAlchemyError as e:
        logger.error("Error updating collection: %s", e)
        db.session.rollback()
        return jsonify({"success": False, "error": "Database error"}), 500


@api_bp.route("/collections/<int:collection_id>", methods=["DELETE"])
@require_auth
def delete_collection(collection_id: int) -> Response | tuple[Response, int]:
    """Delete a user collection."""
    user_id = getattr(g, "user_id", None)
    collection = db.session.query(UserCollection).filter(UserCollection.id == collection_id, UserCollection.owner_id == user_id).first()
    if not collection:
        return jsonify({"success": False, "error": "Collection not found"}), 404

    # Prevent deletion if there are nested children
    has_children = (
        db.session.query(UserCollection).filter(UserCollection.parent_id == collection.id, UserCollection.owner_id == user_id).first()
    )
    if has_children:
        return jsonify({"success": False, "error": "Cannot delete a collection that contains sub-collections"}), 400

    try:
        db.session.delete(collection)
        db.session.commit()
        return jsonify({"success": True})
    except SQLAlchemyError as e:
        logger.error("Error deleting collection: %s", e)
        db.session.rollback()
        return jsonify({"success": False, "error": "Database error"}), 500
