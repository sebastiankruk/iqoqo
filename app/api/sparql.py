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
"""SPARQL query endpoint — read-only SPARQL Protocol over user collections."""

from flask import Blueprint, Response, g, jsonify, request

from app.api.decorators import require_auth
from app.core.limiter import limiter
from app.core.sparql_service import (
    SPARQLError,
    SPARQLQueryTooLarge,
    SPARQLSyntaxError,
    SPARQLTimeout,
    SPARQLWriteRejected,
    build_graph,
    execute_sparql,
    format_graph_results,
    format_select_results,
    validate_query,
)
from app.db.models import Item, db

sparql_bp = Blueprint("sparql", __name__, url_prefix="/sparql")


def _get_user_items():
    """Fetch all items belonging to the authenticated user."""
    return (
        db.session.query(Item)
        .filter(Item.owner_id == g.user_id)
        .all()
    )


def _execute_and_respond(query: str) -> tuple[Response, int] | Response:  # pylint: disable=too-many-return-statements
    """Validate, execute, and format a SPARQL query response."""
    try:
        validate_query(query)
    except SPARQLQueryTooLarge as e:
        return jsonify({"error": str(e)}), 400
    except SPARQLWriteRejected as e:
        return jsonify({"error": str(e)}), 400

    items = _get_user_items()
    base_url = request.url_root.rstrip("/")
    graph = build_graph(items, base_url)

    try:
        result = execute_sparql(graph, query)
    except SPARQLSyntaxError as e:
        return jsonify({"error": str(e)}), 400
    except SPARQLTimeout as e:
        return jsonify({"error": str(e)}), 408
    except SPARQLError as e:
        return jsonify({"error": str(e)}), 500

    # Determine result type and format accordingly
    if result.type in ("SELECT", "ASK"):
        data = format_select_results(result)
        return Response(
            response=jsonify(data).get_data(as_text=True),
            status=200,
            mimetype="application/sparql-results+json",
        )

    # CONSTRUCT or DESCRIBE — return RDF
    accept = request.headers.get("Accept", "text/turtle")
    if "application/ld+json" in accept:
        output = format_graph_results(result, output_format="json-ld")
        return Response(response=output, status=200, mimetype="application/ld+json")
    output = format_graph_results(result, output_format="turtle")
    return Response(response=output, status=200, mimetype="text/turtle")


@sparql_bp.route("", methods=["POST"])
@require_auth
@limiter.limit("10 per minute")
def sparql_post():
    """Execute a SPARQL query via POST body."""
    if request.is_json:
        body = request.get_json(silent=True)
        if not body or "query" not in body:
            return jsonify({"error": "Missing 'query' field in JSON body"}), 400
        query = body["query"]
    elif request.content_type and "application/sparql-query" in request.content_type:
        query = request.get_data(as_text=True)
    else:
        # Form-encoded fallback (SPARQL Protocol)
        query = request.form.get("query", "")

    if not query or not query.strip():
        return jsonify({"error": "Empty query"}), 400

    return _execute_and_respond(query)


@sparql_bp.route("", methods=["GET"])
@require_auth
@limiter.limit("10 per minute")
def sparql_get():
    """Execute a SPARQL query via GET ?query= parameter (SPARQL Protocol compliance)."""
    query = request.args.get("query", "")
    if not query or not query.strip():
        return jsonify({"error": "Missing 'query' parameter"}), 400

    return _execute_and_respond(query)
