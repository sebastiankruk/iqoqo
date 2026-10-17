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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""ActivityPub Federation, NodeInfo 2.1, and WebFinger endpoints for iqoqo v0.9.0."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

from flask import Blueprint, Response, current_app, jsonify, redirect, request
from sqlalchemy import func, select

from app.api.decorators import require_auth
from app.api.federation_guard import federation_required, is_federation_enabled
from app.core import federation_keys
from app.core.iri import canonical_actor_iri, get_lod_base_url, legacy_actor_iri
from app.core.limiter import limiter
from app.db import db
from app.db.auth import User
from app.db.federation import FederationConsent

federation_bp = Blueprint("federation", __name__, url_prefix="/federation")
wellknown_bp = Blueprint("wellknown", __name__, url_prefix="/.well-known")


def _get_base_url() -> str:
    """Return the configured base URL for federation endpoints."""
    return str(current_app.config.get("BASE_URL") or get_lod_base_url()).rstrip("/")


def _get_domain() -> str:
    """Extract domain from base URL."""
    base_url = _get_base_url()
    parsed = urlparse(base_url)
    return parsed.netloc or "iqoqo.cc"


def _add_federation_headers(response: Response) -> Response:
    """Add standard CORS and caching headers for federation responses."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization"
    return response


@federation_bp.after_request
def federation_after_request(response: Response) -> Response:
    """Apply CORS headers to all federation routes."""
    return _add_federation_headers(response)


@wellknown_bp.after_request
def wellknown_after_request(response: Response) -> Response:
    """Apply CORS headers to all .well-known routes."""
    return _add_federation_headers(response)


def _handle_webfinger_lookup() -> Response | tuple[Response, int]:
    """Execute WebFinger RFC 7033 resolution for user identity queries."""
    resource = request.args.get("resource", "").strip()
    if not resource:
        return jsonify({"error": "Missing 'resource' parameter", "code": 400}), 400

    base_url = _get_base_url()
    domain = _get_domain()
    db.session.expire_all()
    user: User | None = None

    if resource.startswith("acct:"):
        account_part = resource[5:]
        username = account_part.split("@")[0]
        # Look up by public_username or UUID string
        stmt = select(User).where(User.public_username == username)
        user = db.session.execute(stmt).scalars().first()
        if not user:
            try:
                parsed_uuid = uuid.UUID(username)
                user = db.session.execute(select(User).where(User.id == parsed_uuid)).scalars().first()
            except (ValueError, TypeError):
                user = None
    elif "/actor/u/" in resource:
        uuid_str = resource.split("/actor/u/")[-1].strip("/")
        try:
            parsed_uuid = uuid.UUID(uuid_str)
            user = db.session.execute(select(User).where(User.id == parsed_uuid)).scalars().first()
        except (ValueError, TypeError):
            user = None
    elif "/actor/" in resource:
        username = resource.split("/actor/")[-1].strip("/")
        stmt = select(User).where(User.public_username == username)
        user = db.session.execute(stmt).scalars().first()
    else:
        # Fallback query by exact username
        stmt = select(User).where(User.public_username == resource)
        user = db.session.execute(stmt).scalars().first()

    if not user:
        return jsonify({"error": f"Resource not found: {resource}", "code": 404}), 404

    # Require explicit user opt-in consent or public visibility
    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    is_opted_in = (consent and consent.federated_profile) or (consent is None and getattr(user, "visibility", None) == "public")
    if not is_opted_in:
        return jsonify({"error": f"Resource not found: {resource}", "code": 404}), 404

    canonical_actor_uri = canonical_actor_iri(user.id, base_url)
    aliases: list[str] = [canonical_actor_uri]
    if user.public_username:
        aliases.append(legacy_actor_iri(user.public_username, base_url))

    subject = f"acct:{user.public_username}@{domain}" if user.public_username else f"acct:{user.id}@{domain}"

    jrd_payload: dict[str, Any] = {
        "subject": subject,
        "aliases": aliases,
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": canonical_actor_uri,
            },
            {
                "rel": "http://webfinger.net/rel/profile-page",
                "type": "text/html",
                "href": f"{base_url}/user/{user.public_username}" if user.public_username else base_url,
            },
        ],
    }

    resp = jsonify(jrd_payload)
    resp.mimetype = "application/jrd+json"
    resp.headers["Content-Type"] = "application/jrd+json; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@wellknown_bp.route("/webfinger", methods=["GET"])
@federation_required
@limiter.limit("120 per minute")
def wellknown_webfinger() -> Response | tuple[Response, int]:
    """RFC 7033 WebFinger endpoint at /.well-known/webfinger."""
    return _handle_webfinger_lookup()


@federation_bp.route("/webfinger", methods=["GET"])
@federation_required
@limiter.limit("120 per minute")
def federation_webfinger() -> Response | tuple[Response, int]:
    """WebFinger discovery endpoint under /api/federation/webfinger."""
    return _handle_webfinger_lookup()


@wellknown_bp.route("/nodeinfo", methods=["GET"])
@federation_required
@limiter.limit("120 per minute")
def wellknown_nodeinfo() -> Response:
    """RFC/NodeInfo discovery document pointing to NodeInfo 2.1 schema."""
    base_url = _get_base_url()
    data: dict[str, Any] = {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.1",
                "href": f"{base_url}/api/federation/nodeinfo/2.1",
            }
        ]
    }
    resp = jsonify(data)
    resp.mimetype = "application/json"
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@federation_bp.route("/nodeinfo/2.1", methods=["GET"])
@federation_required
@limiter.limit("120 per minute")
def federation_nodeinfo_2_1() -> Response:
    """NodeInfo 2.1 document advertising instance software, protocols, and usage."""
    from app.config import Config

    total_users = db.session.execute(select(func.count(User.id))).scalar() or 0  # pylint: disable=not-callable
    active_users = (
        db.session.execute(select(func.count(User.id)).where(User.is_active.is_(True))).scalar() or 0  # pylint: disable=not-callable
    )

    data: dict[str, Any] = {
        "version": "2.1",
        "software": {
            "name": "iqoqo",
            "version": Config.VERSION,
        },
        "protocols": ["activitypub"],
        "services": {
            "inbound": [],
            "outbound": [],
        },
        "openRegistrations": False,
        "usage": {
            "users": {
                "total": total_users,
                "activeHalfyear": active_users,
                "activeMonth": active_users,
            },
            "localPosts": 0,
        },
        "metadata": {
            "nodeName": "iqoqo",
            "federation": {
                "enabled": is_federation_enabled(),
            },
        },
    }
    resp = jsonify(data)
    resp.mimetype = "application/json"
    resp.headers["Content-Type"] = 'application/json; profile="http://nodeinfo.diaspora.software/ns/schema/2.1#"; charset=utf-8'
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


def _build_actor_payload(user: User, base_url: str) -> dict[str, Any]:
    """Construct ActivityPub Person actor JSON-LD representation."""
    canonical_uri = canonical_actor_iri(user.id, base_url)

    # Resolve or create actor cryptographic keypair
    public_key_pem = federation_keys.get_actor_public_key(str(user.id))
    if not public_key_pem:
        _, public_key_pem = federation_keys.generate_actor_keypair(str(user.id))
        user.federation_public_key = public_key_pem
        user.federation_key_id = f"{canonical_uri}#main-key"
        db.session.commit()

    return {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
        ],
        "id": canonical_uri,
        "type": "Person",
        "preferredUsername": user.public_username or str(user.id),
        "name": user.display_name or user.public_username or "iqoqo User",
        "summary": user.bio or "",
        "url": f"{base_url}/user/{user.public_username}" if user.public_username else base_url,
        "inbox": f"{canonical_uri}/inbox",
        "outbox": f"{canonical_uri}/outbox",
        "publicKey": {
            "id": f"{canonical_uri}#main-key",
            "owner": canonical_uri,
            "publicKeyPem": public_key_pem,
        },
        "endpoints": {
            "sharedInbox": f"{base_url}/api/federation/inbox",
        },
    }


@federation_bp.route("/actor/u/<string:user_uuid>", methods=["GET"])
@federation_required
@limiter.limit("120 per minute")
def get_actor_by_uuid(user_uuid: str) -> Response | tuple[Response, int]:
    """Canonical ActivityPub Actor representation keyed by immutable user UUID."""
    try:
        parsed_uuid = uuid.UUID(user_uuid)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user UUID format", "code": 400}), 400

    user = db.session.execute(select(User).where(User.id == parsed_uuid)).scalars().first()
    if not user:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    is_opted_in = (consent and consent.federated_profile) or (consent is None and getattr(user, "visibility", None) == "public")
    if not is_opted_in:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    base_url = _get_base_url()
    actor_payload = _build_actor_payload(user, base_url)

    resp = jsonify(actor_payload)
    resp.mimetype = "application/activity+json"
    resp.headers["Content-Type"] = "application/activity+json; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@federation_bp.route("/actor/<string:username>", methods=["GET"])
@federation_required
@limiter.limit("120 per minute")
def get_actor_by_username(username: str) -> Response | tuple[Response, int]:
    """Legacy/vanity username actor lookup, permanently redirecting (301) to canonical UUID Actor IRI."""
    stmt = select(User).where(User.public_username == username)
    user = db.session.execute(stmt).scalars().first()
    if not user:
        try:
            parsed_uuid = uuid.UUID(username)
            user = db.session.execute(select(User).where(User.id == parsed_uuid)).scalars().first()
        except (ValueError, TypeError):
            user = None

    if not user:
        return jsonify({"error": f"Actor not found for username: {username}", "code": 404}), 404

    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    is_opted_in = (consent and consent.federated_profile) or (consent is None and getattr(user, "visibility", None) == "public")
    if not is_opted_in:
        return jsonify({"error": f"Actor not found for username: {username}", "code": 404}), 404

    base_url = _get_base_url()
    canonical_uri = canonical_actor_iri(user.id, base_url)
    return redirect(canonical_uri, code=301)


@federation_bp.route("/consent", methods=["GET"])
@require_auth
def federation_consent_get() -> Response | tuple[Response, int]:
    """Retrieve federation consent settings for the current user."""
    from app.api.profile import _handle_get_federation_consent

    return _handle_get_federation_consent()


@federation_bp.route("/consent", methods=["PUT", "PATCH"])
@require_auth
def federation_consent_update() -> Response | tuple[Response, int]:
    """Update federation consent settings for the current user."""
    from app.api.profile import _handle_update_federation_consent

    return _handle_update_federation_consent()
