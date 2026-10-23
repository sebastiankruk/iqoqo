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
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from app.core.frbr_merge import get_entity_tombstone
from app.core.frbr_service import serialize_collection_to_rdf
from app.core.iri import canonical_frbr_iri, get_lod_base_url
from app.core.limiter import limiter
from app.db.federation import FederationFollower, FollowStatus
from app.db.models import (
    Expression,
    Item,
    ItemCustodyEvent,
    Manifestation,
    User,
    UserCollection,
    UserWorkIntent,
    Work,
    db,
)

IQOQO = Namespace("https://iqoqo.org/ontology#")
AS = Namespace("https://www.w3.org/ns/activitystreams#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace("https://schema.org/")
FRBR = Namespace("http://purl.org/vocab/frbr/core#")

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
        and "application/activity+json" not in accept
    ):
        return True
    return False


def _prefers_activitystreams() -> bool:
    """Return True if the request explicitly asks for ActivityStreams/ActivityPub."""
    if request.args.get("format", "").lower() in ("activity", "activitypub", "as", "activity+json"):
        return True
    accept = request.headers.get("Accept", "")
    return "application/activity+json" in accept or 'profile="https://www.w3.org/ns/activitystreams"' in accept


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


def _handle_entity_tombstone(tier: str, entity_id: int, tombstone: Any) -> Response | tuple[Response, int]:
    """Handle dereferencing for an entity consolidated and deleted by a FRBR merge.

    Emits permanent 301 redirection for browsers, ActivityStreams Move/Tombstone
    payloads for federation agents, or owl:sameAs triples for Linked Data crawlers.
    """
    diff = getattr(tombstone, "diff", {}) or {}
    target_id = diff.get("target_id")
    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()

    source_iri = diff.get("source_iri") or canonical_frbr_iri(tier, entity_id, base_url)
    target_iri = diff.get("target_iri") or (canonical_frbr_iri(tier, target_id, base_url) if target_id else base_url)

    # 1. HTML browser request: redirect to surviving entity's frontend page
    if _prefers_html() and target_id:
        return cast(Response, redirect(f"/{tier}/{target_id}", code=301))

    # 2. ActivityStreams / Fediverse request
    if _prefers_activitystreams():
        move_payload = diff.get("activitystreams_move")
        if not move_payload:
            move_payload = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"{source_iri}#move",
                "type": "Move",
                "actor": base_url,
                "object": source_iri,
                "target": target_iri,
            }
        resp = jsonify(move_payload)
        resp.status_code = 410
        resp.mimetype = "application/activity+json"
        resp.headers["Content-Type"] = "application/activity+json; charset=utf-8"
        resp.headers["Location"] = target_iri
        resp.headers["Link"] = f'<{target_iri}>; rel="canonical"'
        resp.headers["Cache-Control"] = "public, max-age=300"
        return resp

    # 3. Explicit redirect query parameter
    if request.args.get("redirect") in ("1", "true"):
        return cast(Response, redirect(target_iri, code=301))

    # 4. Public RDF / Linked Data request (owl:sameAs)
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")
    if rdf_format == "turtle":
        payload = f"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n\n<{source_iri}> owl:sameAs <{target_iri}> .\n"
    elif rdf_format == "nt":
        payload = f"<{source_iri}> <http://www.w3.org/2002/07/owl#sameAs> <{target_iri}> .\n"
    else:
        import json

        payload = json.dumps(
            {
                "@context": {
                    "owl": "http://www.w3.org/2002/07/owl#",
                    "as": "https://www.w3.org/ns/activitystreams#",
                },
                "@id": source_iri,
                "owl:sameAs": {"@id": target_iri},
            },
            indent=2,
        )

    resp = Response(
        payload,
        status=410,
        mimetype=rdf_mimetype,
        headers={
            "Content-Type": f"{rdf_mimetype}; charset=utf-8",
            "Location": target_iri,
            "Link": f'<{target_iri}>; rel="duplicate"',
            "Cache-Control": "public, max-age=300",
        },
    )
    return resp


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
        tombstone = get_entity_tombstone("manifestation", manifestation_id)
        if tombstone:
            return _handle_entity_tombstone("manifestation", manifestation_id, tombstone)
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
        tombstone = get_entity_tombstone("work", work_id)
        if tombstone:
            return _handle_entity_tombstone("work", work_id, tombstone)
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
        tombstone = get_entity_tombstone("expression", expression_id)
        if tombstone:
            return _handle_entity_tombstone("expression", expression_id, tombstone)
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


def _serialize_graph_output(g: Graph, output_format: str) -> str:
    """Serializes an rdflib Graph to string according to format."""
    if output_format in ("nt", "n-triples", "ntriples"):
        return g.serialize(format="nt")
    if output_format == "json-ld":
        context = {
            "iqoqo": str(IQOQO),
            "as": str(AS),
            "crm": str(CRM),
            "foaf": str(FOAF),
            "schema": str(SCHEMA),
            "frbr": str(FRBR),
            "xsd": str(XSD),
        }
        return g.serialize(format="json-ld", context=context, indent=2)
    return g.serialize(format="turtle")


def serialize_custody_events_to_rdf(
    custody_events: list[Any],
    base_url: str,
    output_format: str = "json-ld",
) -> str:
    """Serializes ItemCustodyEvents to RDF (CIDOC CRM E10 + ActivityStreams)."""
    g = Graph()
    g.bind("iqoqo", IQOQO)
    g.bind("as", AS)
    g.bind("crm", CRM)
    g.bind("xsd", XSD)

    for event in custody_events:
        e_uri = URIRef(f"{base_url}/custody/{event.id}")
        g.add((e_uri, RDF.type, IQOQO.ItemCustodyEvent))
        g.add((e_uri, RDF.type, CRM.E10_Transfer_of_Custody))

        ev_type = str(getattr(event, "event_type", "transfer"))
        if ev_type in ("loan", "loan_accepted", "loan_dispatched", "acquisition", "transfer"):
            g.add((e_uri, RDF.type, AS.Accept))

        item_id = getattr(event, "item_id", None)
        if item_id:
            i_uri = URIRef(f"{base_url}/item/{item_id}")
            g.add((i_uri, RDF.type, IQOQO.Item))
            g.add((e_uri, IQOQO.custodyItem, i_uri))

        g.add((e_uri, IQOQO.eventType, Literal(ev_type, datatype=XSD.string)))

        rec_at = getattr(event, "recorded_at", None)
        if rec_at:
            rec_str = rec_at.isoformat() if hasattr(rec_at, "isoformat") else str(rec_at)
            g.add((e_uri, IQOQO.recordedAt, Literal(rec_str, datatype=XSD.dateTime)))

        notes = getattr(event, "notes", None)
        if notes:
            g.add((e_uri, IQOQO.eventNotes, Literal(str(notes), datatype=XSD.string)))

        actor = getattr(event, "actor", None)
        actor_id = getattr(event, "actor_id", None)
        if actor or actor_id:
            actor_name = actor.public_username if actor and getattr(actor, "public_username", None) else str(actor_id)
            a_uri = URIRef(f"{base_url}/u/{actor_name}")
            g.add((a_uri, RDF.type, IQOQO.User))
            g.add((e_uri, IQOQO.custodyActor, a_uri))

    return _serialize_graph_output(g, output_format)


def serialize_user_collection_to_rdf(
    collection: Any,
    base_url: str,
    output_format: str = "json-ld",
) -> str:
    """Serializes UserCollection to RDF (ActivityStreams OrderedCollection)."""
    g = Graph()
    g.bind("iqoqo", IQOQO)
    g.bind("as", AS)
    g.bind("xsd", XSD)

    c_uri = URIRef(f"{base_url}/collections/{collection.id}")
    g.add((c_uri, RDF.type, IQOQO.UserCollection))
    g.add((c_uri, RDF.type, AS.OrderedCollection))

    owner = getattr(collection, "owner", None)
    owner_id = getattr(collection, "owner_id", None)
    owner_name = owner.public_username if owner and getattr(owner, "public_username", None) else str(owner_id)
    o_uri = URIRef(f"{base_url}/u/{owner_name}")
    g.add((o_uri, RDF.type, IQOQO.User))
    g.add((c_uri, IQOQO.collectionOwner, o_uri))

    name = str(getattr(collection, "name", "Collection"))
    g.add((c_uri, IQOQO.collectionName, Literal(name, datatype=XSD.string)))

    for item_link in getattr(collection, "items", None) or []:
        it = getattr(item_link, "item", None)
        it_id = getattr(item_link, "item_id", None) or getattr(item_link, "id", None)
        if it is not None and getattr(it, "is_hidden", False):
            continue
        if it_id:
            it_uri = URIRef(f"{base_url}/item/{it_id}")
            g.add((it_uri, RDF.type, IQOQO.Item))
            g.add((c_uri, IQOQO.collectionItem, it_uri))
            g.add((c_uri, AS.orderedItems, it_uri))

    return _serialize_graph_output(g, output_format)


def serialize_user_intents_to_rdf(
    intents: list[Any],
    base_url: str,
    username: str,
    output_format: str = "json-ld",
) -> str:
    """Serializes UserWorkIntents wishlist to RDF (Schema.org WantAction + AS Collection)."""
    g = Graph()
    g.bind("iqoqo", IQOQO)
    g.bind("as", AS)
    g.bind("schema", SCHEMA)
    g.bind("xsd", XSD)

    coll_uri = URIRef(f"{base_url}/u/{username}/wishlist")
    g.add((coll_uri, RDF.type, AS.Collection))

    u_uri = URIRef(f"{base_url}/u/{username}")
    g.add((u_uri, RDF.type, IQOQO.User))

    for intent in intents:
        i_uri = URIRef(f"{base_url}/intent/{intent.id}")
        g.add((i_uri, RDF.type, IQOQO.UserWorkIntent))
        g.add((i_uri, RDF.type, SCHEMA.WantAction))
        g.add((coll_uri, AS.items, i_uri))
        g.add((i_uri, IQOQO.intentUser, u_uri))

        w_id = getattr(intent, "work_id", None)
        if w_id:
            w_uri = URIRef(f"{base_url}/work/{w_id}")
            g.add((w_uri, RDF.type, IQOQO.Work))
            g.add((i_uri, IQOQO.intentWork, w_uri))

        status = str(getattr(intent, "status", "want_to_read"))
        g.add((i_uri, IQOQO.intentStatus, Literal(status, datatype=XSD.string)))

    return _serialize_graph_output(g, output_format)


def serialize_user_followers_to_rdf(
    user: Any,
    followers: list[Any],
    friends: list[Any],
    base_url: str,
    output_format: str = "json-ld",
) -> str:
    """Serializes User followers and friends to RDF (ActivityStreams Follow + FOAF knows)."""
    g = Graph()
    g.bind("iqoqo", IQOQO)
    g.bind("as", AS)
    g.bind("foaf", FOAF)
    g.bind("xsd", XSD)

    username = getattr(user, "public_username", None) or str(getattr(user, "id", "unknown"))
    u_uri = URIRef(f"{base_url}/u/{username}")
    g.add((u_uri, RDF.type, IQOQO.User))
    g.add((u_uri, RDF.type, FOAF.Person))

    for f in followers:
        f_uri = URIRef(f"{base_url}/followers/{f.id}")
        g.add((f_uri, RDF.type, IQOQO.FederationFollower))
        g.add((f_uri, RDF.type, AS.Follow))
        g.add((f_uri, IQOQO.followerLocalUser, u_uri))
        status = str(getattr(f, "status", "accepted"))
        g.add((f_uri, IQOQO.followerStatus, Literal(status, datatype=XSD.string)))
        g.add((f_uri, AS.object, u_uri))

        remote_actor = getattr(f, "remote_actor", None)
        actor_uri = getattr(remote_actor, "actor_uri", None) if remote_actor else None
        if actor_uri:
            g.add((f_uri, AS.actor, URIRef(str(actor_uri))))

    for friend in friends:
        fr_name = getattr(friend, "public_username", None) or str(getattr(friend, "id", "friend"))
        fr_uri = URIRef(f"{base_url}/u/{fr_name}")
        g.add((fr_uri, RDF.type, IQOQO.User))
        g.add((fr_uri, RDF.type, FOAF.Person))
        g.add((u_uri, FOAF.knows, fr_uri))
        g.add((u_uri, IQOQO.knowsFriend, fr_uri))

    return _serialize_graph_output(g, output_format)


def serialize_loan_request_to_rdf(
    loan_request: Any,
    base_url: str,
    output_format: str = "json-ld",
) -> str:
    """Serializes LoanRequest to RDF (ActivityStreams Offer)."""
    g = Graph()
    g.bind("iqoqo", IQOQO)
    g.bind("as", AS)
    g.bind("xsd", XSD)

    req_uri = URIRef(f"{base_url}/loans/{loan_request.id}")
    g.add((req_uri, RDF.type, IQOQO.LoanRequest))
    g.add((req_uri, RDF.type, AS.Offer))

    item_id = getattr(loan_request, "item_id", None)
    if item_id:
        i_uri = URIRef(f"{base_url}/item/{item_id}")
        g.add((i_uri, RDF.type, IQOQO.Item))
        g.add((req_uri, IQOQO.loanItem, i_uri))

    requester = getattr(loan_request, "requester", None)
    requester_id = getattr(loan_request, "requester_id", None)
    req_name = requester.public_username if requester and getattr(requester, "public_username", None) else str(requester_id)
    r_uri = URIRef(f"{base_url}/u/{req_name}")
    g.add((r_uri, RDF.type, IQOQO.User))
    g.add((req_uri, IQOQO.loanRequester, r_uri))

    status = str(getattr(loan_request, "status", "pending"))
    g.add((req_uri, IQOQO.loanStatus, Literal(status, datatype=XSD.string)))

    return _serialize_graph_output(g, output_format)


@public_bp.route("/items/<int:item_id>/custody", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_item_custody(item_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for an Item's custody provenance history.

    Serves CIDOC CRM (E10_Transfer_of_Custody) and ActivityStreams semantic RDF.
    Only non-hidden items are accessible publicly.
    """
    stmt = select(Item).where(Item.id == item_id, Item.is_hidden.is_(False))
    item = db.session.execute(stmt).scalars().first()
    if not item:
        return jsonify({"error": "Item not found"}), 404

    events_stmt = (
        select(ItemCustodyEvent)
        .options(selectinload(ItemCustodyEvent.actor))
        .where(ItemCustodyEvent.item_id == item_id)
        .order_by(ItemCustodyEvent.recorded_at.asc())
    )
    events = list(db.session.execute(events_stmt).scalars().all())

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")
    rdf_payload = serialize_custody_events_to_rdf(events, base_url, output_format=rdf_format)
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/collections/<int:collection_id>", methods=["GET"])
@limiter.limit("120 per minute")
def get_public_collection(collection_id: int) -> Response | tuple[Response, int]:
    """Public semantic endpoint for a UserCollection entity.

    Serves ActivityStreams OrderedCollection semantic RDF.
    Only collections belonging to public users are accessible publicly.
    """
    stmt = (
        select(UserCollection)
        .options(
            selectinload(UserCollection.owner),
        )
        .where(UserCollection.id == collection_id)
    )
    collection = db.session.execute(stmt).scalars().first()
    if not collection or not collection.owner or collection.owner.visibility != "public":
        return jsonify({"error": "Collection not found"}), 404

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")
    rdf_payload = serialize_user_collection_to_rdf(collection, base_url, output_format=rdf_format)
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/u/<string:username>/wishlist", methods=["GET"])
@limiter.limit("60 per minute")
def get_public_user_wishlist(username: str) -> Response | tuple[Response, int]:
    """Public semantic endpoint for a User's wishlist intents.

    Serves Schema.org WantAction and ActivityStreams Collection RDF.
    """
    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalars().first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    intents_stmt = (
        select(UserWorkIntent)
        .options(selectinload(UserWorkIntent.work))
        .where(UserWorkIntent.user_id == user.id, UserWorkIntent.is_hidden.is_(False))
        .order_by(UserWorkIntent.created_at.desc())
    )
    intents = list(db.session.execute(intents_stmt).scalars().all())

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")
    rdf_payload = serialize_user_intents_to_rdf(intents, base_url, username=user.public_username or username, output_format=rdf_format)
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/u/<string:username>/followers", methods=["GET"])
@limiter.limit("60 per minute")
def get_public_user_followers(username: str) -> Response | tuple[Response, int]:
    """Public semantic endpoint for a User's followers and friends.

    Serves ActivityStreams Follow and FOAF knows RDF.
    """
    user_stmt = select(User).where(func.lower(User.public_username) == username.lower(), User.visibility == "public")
    user = db.session.execute(user_stmt).scalars().first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    followers_stmt = (
        select(FederationFollower)
        .options(selectinload(FederationFollower.remote_actor))
        .where(FederationFollower.local_user_id == user.id, FederationFollower.status == FollowStatus.ACCEPTED)
    )
    followers = list(db.session.execute(followers_stmt).scalars().all())

    from app.core.friend_service import get_friend_user_ids

    local_friend_ids = get_friend_user_ids(user.id)
    friends: list[User] = []
    if local_friend_ids:
        friends_stmt = select(User).where(User.id.in_(local_friend_ids))
        friends = list(db.session.execute(friends_stmt).scalars().all())

    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    rdf_format, rdf_mimetype = _negotiate_rdf_format(default_format="json-ld")
    rdf_payload = serialize_user_followers_to_rdf(user, followers, friends, base_url, output_format=rdf_format)
    resp = Response(
        rdf_payload,
        mimetype=rdf_mimetype,
        headers={"Content-Type": f"{rdf_mimetype}; charset=utf-8"},
    )
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@public_bp.route("/federation/instance-info", methods=["GET"])
@limiter.limit("60 per minute")
def get_public_federation_instance_info() -> Response:
    """Public endpoint returning local instance info and federation status."""
    from urllib.parse import urlparse

    from app.api.federation_guard import is_federation_enabled
    from app.config import Config

    fed_enabled = is_federation_enabled()
    public_items_count = (
        db.session.execute(select(func.count(Item.id)).where(Item.is_hidden.is_(False))).scalar() or 0  # pylint: disable=not-callable
    )
    base_url = current_app.config.get("BASE_URL") or get_lod_base_url()
    local_domain = urlparse(base_url).netloc if base_url else "localhost"

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "domain": local_domain,
                    "software_name": "iqoqo",
                    "software_version": Config.VERSION,
                    "public_items_count": public_items_count,
                    "federation_enabled": fed_enabled,
                },
            }
        ),
        200,
    )
