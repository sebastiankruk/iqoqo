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
"""SPARQL query endpoint — read-only SPARQL Protocol over user collections with resource isolation."""

import logging
import time
from typing import Any

from flask import Blueprint, Response, current_app, g, jsonify, request
from rdflib import Graph
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.api.decorators import require_auth, require_permission
from app.core.iri import get_lod_base_url
from app.core.limiter import limiter
from app.core.permissions import PermissionName
from app.core.sparql_service import (
    MAX_SERIALIZED_BYTES,
    SPARQLChildProcessError,
    SPARQLConcurrencyLimit,
    SPARQLError,
    SPARQLGraphBuildError,
    SPARQLQueryTooLarge,
    SPARQLResourceLimit,
    SPARQLSyntaxError,
    SPARQLTimeout,
    SPARQLWriteRejected,
    build_graph,
    execute_sparql,
    format_graph_results,
    format_select_results,
    validate_query,
)
from app.db.models import Expression, Item, Manifestation, User, db

logger = logging.getLogger(__name__)

sparql_bp = Blueprint("sparql", __name__, url_prefix="/sparql")


def _get_sparql_items(user: User | None) -> list[Item]:
    """Fetch items for SPARQL querying with eager-loaded FRBR entities.

    Strictly filters Item entities to public records and items owned by user,
    preventing disclosure of other users' private collection records.
    """
    from app.core.sparql_service import MAX_GRAPH_ITEMS

    stmt = select(Item).options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
    if user and user.id:
        stmt = stmt.where(or_(Item.is_hidden.is_(False), Item.owner_id == user.id))
    else:
        stmt = stmt.where(Item.is_hidden.is_(False))

    # Apply item count limit
    stmt = stmt.limit(MAX_GRAPH_ITEMS)

    return list(db.session.execute(stmt).scalars().all())


def _format_select_ask(result: Any, accept: str) -> tuple[bytes | str, str]:
    """Format SELECT/ASK result into (payload, mimetype)."""
    if "application/sparql-results+xml" in accept or "application/xml" in accept or "text/xml" in accept:
        return result.serialize(format="xml") or b"", "application/sparql-results+xml"
    if "text/csv" in accept:
        return result.serialize(format="csv") or b"", "text/csv"
    if "text/tab-separated-values" in accept or "text/tsv" in accept:
        return result.serialize(format="tsv") or b"", "text/tab-separated-values"
    data = format_select_results(result)
    return jsonify(data).get_data(as_text=True), "application/sparql-results+json"


def _format_graph(result: Any, accept: str) -> tuple[bytes | str, str]:
    """Format CONSTRUCT/DESCRIBE result into (payload, mimetype)."""
    if "application/ld+json" in accept:
        return format_graph_results(result, output_format="json-ld"), "application/ld+json"
    if "application/rdf+xml" in accept:
        g_res = result.graph if hasattr(result, "graph") and result.graph is not None else Graph()
        return g_res.serialize(format="xml"), "application/rdf+xml"
    return format_graph_results(result, output_format="turtle"), "text/turtle"


_FORMATTERS = {
    "SELECT": _format_select_ask,
    "ASK": _format_select_ask,
    "CONSTRUCT": _format_graph,
    "DESCRIBE": _format_graph,
}


def _execute_and_respond(query: str) -> tuple[Response, int] | Response:
    """Validate, execute, and format a SPARQL query response."""
    start_time = time.time()
    error_msg = None
    status_code = 400
    rejection_reason = None
    phase = "validate"
    graph_build_duration = 0.0
    execute_duration = 0.0

    try:
        operation = validate_query(query)
        phase = "build_graph"
        user = db.session.get(User, g.user_id) if hasattr(g, "user_id") and g.user_id else None
        items = _get_sparql_items(user)
        base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
        graph_build_start = time.time()
        graph = build_graph(items, base_url, user_id=user.id if user else None)
        graph_build_duration = time.time() - graph_build_start
        phase = "execute"
        execute_start = time.time()
        result = execute_sparql(graph, query)
        execute_duration = time.time() - execute_start
        phase = "format"
    except SPARQLQueryTooLarge as e:
        error_msg = str(e)
        status_code = 413
        rejection_reason = "query_too_large"
    except SPARQLWriteRejected as e:
        error_msg = str(e)
        status_code = 400
        rejection_reason = "write_rejected"
    except SPARQLSyntaxError as e:
        error_msg = str(e)
        status_code = 400
        rejection_reason = "syntax_error"
    except SPARQLTimeout as e:
        error_msg = str(e)
        status_code = 504
        rejection_reason = "timeout"
    except SPARQLResourceLimit as e:
        error_msg = str(e)
        status_code = 413
        rejection_reason = "resource_limit"
    except SPARQLConcurrencyLimit as e:
        error_msg = str(e)
        status_code = 503
        rejection_reason = "concurrency_limit"
    except SPARQLGraphBuildError as e:
        error_msg = str(e)
        status_code = 500
        rejection_reason = "graph_build_error"
    except SPARQLChildProcessError as e:
        error_msg = str(e)
        status_code = 502
        rejection_reason = "child_process_error"
    except SPARQLError as e:
        error_msg = str(e)
        status_code = 500
        rejection_reason = "internal_error"
    except (SQLAlchemyError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, OSError):
        # Catch known execution exceptions: convert into a structured error response
        # so clients never see an uncaught Flask traceback.
        logger.exception("SPARQL endpoint uncaught exception in phase=%s", phase)
        error_msg = "Internal server error during SPARQL execution."
        status_code = 500
        rejection_reason = "uncaught_exception"

    duration = time.time() - start_time

    if error_msg is not None:
        # Log rejection without query content (for security)
        logger.warning(
            "SPARQL query rejected: reason=%s, phase=%s, duration=%.3fs, status=%s",
            rejection_reason,
            phase,
            duration,
            status_code,
        )
        return jsonify({"error": error_msg, "code": status_code}), status_code

    # Log successful query completion without query content
    logger.info(
        "SPARQL query completed: operation=%s, phase=%s, graph_build=%.3fs, execute=%.3fs, total=%.3fs",
        operation,
        phase,
        graph_build_duration,
        execute_duration,
        duration,
    )

    accept = request.headers.get("Accept", "")
    formatter = _FORMATTERS.get(result.type, _format_graph)
    output_payload, mimetype = formatter(result, accept)

    payload_len = len(output_payload.encode("utf-8")) if isinstance(output_payload, str) else len(output_payload)
    if payload_len > MAX_SERIALIZED_BYTES:
        return jsonify({"error": f"Result exceeds maximum size of {MAX_SERIALIZED_BYTES} bytes", "code": 413}), 413

    return Response(response=output_payload, status=200, mimetype=mimetype)


@sparql_bp.route("", methods=["POST"])
@require_auth
@require_permission(PermissionName.READ_METADATA)
@limiter.limit("10 per minute")
def sparql_post():
    """Execute a SPARQL query via POST body."""
    if request.content_type and "application/sparql-query" in request.content_type:
        query = request.get_data(as_text=True)
    elif request.is_json:
        body = request.get_json(silent=True)
        if not body or "query" not in body:
            return jsonify({"error": "Missing 'query' field in JSON body", "code": 400}), 400
        query = body["query"]
    else:
        # Form-encoded fallback (SPARQL Protocol)
        query = request.form.get("query", "")

    if not query or not query.strip():
        return jsonify({"error": "Empty query", "code": 400}), 400

    return _execute_and_respond(query)


@sparql_bp.route("", methods=["GET"])
@require_auth
@require_permission(PermissionName.READ_METADATA)
@limiter.limit("10 per minute")
def sparql_get():
    """Execute a SPARQL query via GET ?query= parameter (SPARQL Protocol compliance)."""
    query = request.args.get("query", "")
    if not query or not query.strip():
        return jsonify({"error": "Missing 'query' parameter", "code": 400}), 400

    return _execute_and_respond(query)
