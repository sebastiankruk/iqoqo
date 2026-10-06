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


#: Maximum number of ancestors considered plausible for a collection tree.
#: Collections nest a handful of levels deep in practice, so this only trips
#: on structurally corrupt data (a pre-existing cycle written by a migration
#: or a direct database edit) and serves as a hard stop on traversal cost.
MAX_HIERARCHY_DEPTH = 50


def get_collection_hierarchy_ids(collection_id: int, user_id) -> set[int]:
    """Return ``collection_id`` plus every ancestor of it, in one query.

    Walks the ``parent_id`` chain upward with a single recursive CTE instead
    of one sequential query per hierarchy level, reducing validation from
    ``O(depth)`` round-trips to ``O(1)``.

    The starting collection is included in the result, so callers can tell a
    *missing* collection (empty result) apart from a collection that exists but
    sits at the root of the tree (result of size 1) without a second query.

    The recursion is a ``UNION`` (de-duplicating) over ``(id, parent_id)``
    rather than ``UNION ALL``.  That distinction matters for safety: if the
    stored data already contains a cycle, de-duplication makes the walk
    revisit each ``(id, parent_id)`` pair once and stop, whereas
    ``UNION ALL`` would re-expand the cycle on every iteration and burn CPU
    until the query timed out.

    Parameters
    ----------
    collection_id:
        Id of the collection whose ancestors are requested.
    user_id:
        Owning user.  Scoped so one user can never traverse another's tree.

    Returns:
        The set containing ``collection_id`` itself and all of its ancestors.

    Raises
    ------
    ValueError
        If the stored hierarchy already contains a cycle reachable from
        ``collection_id``, or the chain exceeds :data:`MAX_HIERARCHY_DEPTH`.
        Both indicate corrupt data that callers must not silently accept.
    """
    base = (
        db.select(
            UserCollection.id.label("id"),
            UserCollection.parent_id.label("parent_id"),
        )
        .where(UserCollection.id == collection_id, UserCollection.owner_id == user_id)
        .cte("collection_ancestors", recursive=True)
    )

    # The recursive branch needs its own alias of the CTE so it can reference
    # the previous iteration's ``parent_id``. Walking *up* the tree means
    # selecting the node whose own ``id`` equals the current row's ``parent_id``.
    current = base.alias("c")
    recursive = base.union(
        db.select(
            UserCollection.id.label("id"),
            UserCollection.parent_id.label("parent_id"),
        ).where(
            UserCollection.id == current.c.parent_id,
            UserCollection.owner_id == user_id,
        )
    )

    rows = db.session.execute(db.select(recursive.c.id, recursive.c.parent_id)).all()
    # A set-based UNION does not guarantee row order, and ordering is not
    # meaningful here: cycle detection only depends on membership.
    visited = {row.id for row in rows}

    # If any reachable node names ``collection_id`` as its own parent, the
    # starting node is its own ancestor: the stored data already contains a
    # cycle. Callers must not silently treat that as a valid hierarchy.
    if any(row.parent_id == collection_id for row in rows):
        raise ValueError("Circular reference detected in collection hierarchy")

    if len(visited) - 1 > MAX_HIERARCHY_DEPTH:
        raise ValueError("Collection hierarchy exceeds maximum depth")

    return visited


def _validate_parent_hierarchy(collection_id: int, parent_id: int, user_id) -> str | None:
    """Validate parent collection hierarchy and detect circular references.

    Resolves the full ancestor chain of the proposed parent with a single
    recursive CTE, then rejects the update if the collection being moved
    already appears in it.
    """
    if parent_id == collection_id:
        return "A collection cannot be its own parent"

    # One query resolves both existence and the full ancestor chain. An empty
    # set means the parent does not exist for this user; a parent that exists
    # but sits at the root of the tree yields a set containing only itself.
    hierarchy = get_collection_hierarchy_ids(parent_id, user_id)
    if not hierarchy:
        return "Invalid parent collection"

    if collection_id in hierarchy:
        return "Circular reference detected in collection hierarchy"
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
        try:
            err = _validate_parent_hierarchy(collection.id, data.parent_id, user_id)
        except ValueError:
            # Structurally corrupt hierarchy data: reject the write rather
            # than propagating a 500 to the client.
            logger.error("Collection hierarchy exceeds maximum depth for collection %s", collection_id)
            return jsonify({"success": False, "error": "Invalid parent collection"}), 400
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
