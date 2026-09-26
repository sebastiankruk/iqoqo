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
"""Public Linked Open Data (LOD) and RDF endpoints for iqoqo v0.7.0.

Handles canonical IRI dereferencing, content negotiation, and RDF serialization
for Work, Expression, Manifestation, and Item entities.
"""

from typing import Any, cast

from flask import Blueprint, Response, current_app, jsonify, redirect, request, url_for
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.core.frbr_service import serialize_collection_to_rdf
from app.core.iri import get_lod_base_url
from app.core.limiter import limiter
from app.db.models import Expression, Item, Manifestation, Work, db

public_bp = Blueprint("public", __name__, url_prefix="/public")
lod_bp = Blueprint("lod", __name__)

# Public RDF request policy constants
MAX_PUBLIC_RDF_LIMIT = 1000  # Maximum items allowed in a single public RDF request
DEFAULT_PUBLIC_RDF_LIMIT = 100  # Default limit when not specified
MIN_PUBLIC_RDF_LIMIT = 1  # Minimum valid limit


@lod_bp.route("/works/<int:work_id>", methods=["GET"])
def canonical_work_iri(work_id: int) -> Response:
    """Dereference a canonical Work IRI through its negotiated public endpoint."""
    return redirect(url_for("api.public.get_public_work", work_id=work_id, **request.args.to_dict(flat=False)), code=308)


@lod_bp.route("/expressions/<int:expression_id>", methods=["GET"])
def canonical_expression_iri(expression_id: int) -> Response:
    """Dereference a canonical Expression IRI through its negotiated public endpoint."""
    return redirect(url_for("api.public.get_public_expression", expression_id=expression_id, **request.args.to_dict(flat=False)), code=308)


@lod_bp.route("/manifestations/<int:manifestation_id>", methods=["GET"])
def canonical_manifestation_iri(manifestation_id: int) -> Response:
    """Dereference a canonical Manifestation IRI through its negotiated public endpoint."""
    return redirect(
        url_for("api.public.get_public_manifestation", manifestation_id=manifestation_id, **request.args.to_dict(flat=False)), code=308
    )


@lod_bp.route("/items/<int:item_id>", methods=["GET"])
def canonical_item_iri(item_id: int) -> Response:
    """Dereference a canonical Item IRI through its visibility-aware public endpoint."""
    return redirect(url_for("api.public.get_public_item", item_id=item_id, **request.args.to_dict(flat=False)), code=308)


@public_bp.after_request
def add_cors_headers(response: Response) -> Response:
    """Ensure all public endpoints provide open CORS for AI agents and Linked Data crawlers."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization"
    return response


def _parse_safe_rdf_limit(default: int = DEFAULT_PUBLIC_RDF_LIMIT) -> int:
    """Parse and validate the 'limit' query parameter with safe bounds.

    Returns a clamped limit value between MIN_PUBLIC_RDF_LIMIT and MAX_PUBLIC_RDF_LIMIT.
    Non-positive or malformed values are replaced with the default.
    """
    try:
        limit = request.args.get("limit", default, type=int)
    except (ValueError, TypeError):
        limit = default

    # Clamp to safe bounds
    if limit < MIN_PUBLIC_RDF_LIMIT:
        limit = default
    elif limit > MAX_PUBLIC_RDF_LIMIT:
        limit = MAX_PUBLIC_RDF_LIMIT

    return limit


def _prefers_html() -> bool:
    """Return True if the request explicitly asks for HTML over RDF formats."""
    if request.args.get("format"):
        return False
    accept = request.headers.get("Accept", "")
    if (
        "text/html" in accept
        and "application/ld+json" not in accept
        and "text/turtle" not in accept
        and "application/n-triples" not in accept
    ):
        return True
    return False


def _negotiate_rdf_format(default_format: str = "json-ld") -> tuple[str, str]:
    """Negotiate RDF format and mimetype from Accept header and format query param.

    Returns:
        tuple[str, str]: (rdf_format, rdf_mimetype)
    """
    accept_header = request.headers.get("Accept", "")
    format_arg = request.args.get("format", "").lower()

    if "application/n-triples" in accept_header or format_arg in ("nt", "n-triples") or accept_header == "text/plain":
        return "nt", "application/n-triples"
    if "text/turtle" in accept_header or "application/x-turtle" in accept_header or format_arg == "turtle":
        return "turtle", "text/turtle"
    if "application/ld+json" in accept_header or format_arg in ("json-ld", "jsonld"):
        return "json-ld", "application/ld+json"

    if default_format == "json-ld":
        return "json-ld", "application/ld+json"
    return "turtle", "text/turtle"


@public_bp.route("/manifestations/<int:manifestation_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_manifestation(manifestation_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for a Manifestation entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples.
    """
    stmt = (
        select(Manifestation)
        .options(
            joinedload(Manifestation.expression).joinedload(Expression.work),
        )
        .where(Manifestation.id == manifestation_id)
    )
    manifestation = db.session.execute(stmt).scalars().first()
    if not manifestation:
        return jsonify({"error": "Manifestation not found"}), 404

    if _prefers_html():
        return cast(Response, redirect(f"/manifestation/{manifestation.id}", code=303))

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/manifestation/{manifestation.id}"
    rdf_payload = serialize_collection_to_rdf(
        [manifestation],
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/works/<int:work_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_work(work_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for a Work entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples,
    linking expressions and manifestations embodied by the work.
    """
    stmt = (
        select(Work)
        .options(
            selectinload(cast(Any, Work.expressions)).selectinload(cast(Any, Expression.manifestations)),
        )
        .where(Work.id == work_id)
    )
    work = db.session.execute(stmt).scalars().first()
    if not work:
        return jsonify({"error": "Work not found"}), 404

    if _prefers_html():
        return cast(Response, redirect(f"/work/{work.id}", code=303))

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/work/{work.id}"
    expressions_list: list[Any] = getattr(work, "expressions", [])
    manifestations = [m for expr in expressions_list for m in getattr(expr, "manifestations", [])]
    items_to_serialize: list[Any] = manifestations if manifestations else [work]

    rdf_payload = serialize_collection_to_rdf(
        items_to_serialize,
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/expressions/<int:expression_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_expression(expression_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for an Expression entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples.
    """
    stmt = (
        select(Expression)
        .options(
            joinedload(Expression.work),
            selectinload(cast(Any, Expression.manifestations)),
        )
        .where(Expression.id == expression_id)
    )
    expression = db.session.execute(stmt).scalars().first()
    if not expression:
        return jsonify({"error": "Expression not found"}), 404

    if _prefers_html():
        return cast(Response, redirect(f"/expression/{expression.id}", code=303))

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/expression/{expression.id}"
    expr_manifestations: list[Any] = list(getattr(expression, "manifestations", []))
    items_to_serialize: list[Any] = expr_manifestations if expr_manifestations else [expression]

    rdf_payload = serialize_collection_to_rdf(
        items_to_serialize,
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/items/<int:item_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_item(item_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for an Item entity.

    Serves FRBR/Schema.org semantic metadata in JSON-LD, Turtle, or N-Triples.
    Only non-hidden items are accessible publicly.
    """
    stmt = (
        select(Item)
        .options(
            joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work),
        )
        .where(Item.id == item_id, Item.is_hidden.is_(False))
    )
    item = db.session.execute(stmt).scalars().first()
    if not item:
        return jsonify({"error": "Item not found"}), 404

    if _prefers_html():
        return cast(Response, redirect(f"/item/{item.id}", code=303))

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")

    collection_uri = f"{base_url}/item/{item.id}"
    rdf_payload = serialize_collection_to_rdf(
        [item],
        base_url,
        output_format=rdf_format,
        collection_uri=collection_uri,
    )
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp
