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
"""API routes for extracting and exposing generic taxonomies."""

from flask import Response, g, jsonify
from sqlalchemy.exc import SQLAlchemyError

from app.api.core import api_bp
from app.api.decorators import require_auth
from app.core.taxonomy import ALL_GENRES
from app.db.core import Manifestation, Tag, UserCollection, db


@api_bp.route("/taxonomies", methods=["GET"])
@require_auth
def get_taxonomies() -> Response | tuple[Response, int]:
    """
    Extract distinct tags, collections, genres, and publishers.
    - Tags: All tags in the global folksonomy.
    - Collections: All collection names for the current user.
    - Publishers: Distinct publisher strings from manifestations.
    - Genres: Static ontology from app.core.taxonomy.
    """
    user_id = getattr(g, "user_id", None)

    try:
        # Global folksonomy tags
        tags_query = db.session.query(Tag.name).distinct().all()
        tags = sorted([t[0] for t in tags_query if t[0]])

        # User's collection names
        collections_query = db.session.query(UserCollection.name).filter(UserCollection.owner_id == user_id).distinct().all()
        collections = sorted([c[0] for c in collections_query if c[0]])

        # Global distinct publishers
        publishers_query = (
            db.session.query(Manifestation.publisher)
            .filter(Manifestation.publisher.isnot(None), Manifestation.publisher != "")
            .distinct()
            .all()
        )
        publishers = sorted([p[0].strip() for p in publishers_query if p[0] and p[0].strip()])

        # Static genres
        genres = sorted(ALL_GENRES)

        return jsonify(
            {
                "success": True,
                "data": {
                    "tags": tags,
                    "genres": genres,
                    "collections": collections,
                    "publishers": publishers,
                },
            }
        )
    except SQLAlchemyError as e:
        import logging

        logging.getLogger(__name__).error(f"Error fetching taxonomies: {e}")
        return jsonify({"success": False, "error": "Failed to load taxonomies"}), 500
