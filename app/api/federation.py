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

import os
import uuid
from typing import Any
from urllib.parse import urlparse

from flask import Blueprint, Response, current_app, g, jsonify, redirect, request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.decorators import require_auth
from app.api.federation_guard import federation_required, is_federation_enabled
from app.core import federation_keys
from app.core.federation_client import FederationClient
from app.core.federation_discovery import clean_instance_domain
from app.core.http_signatures import SignatureVerificationError, verify_request
from app.core.iri import canonical_actor_iri, get_federation_base_url, legacy_actor_iri
from app.core.limiter import (
    FEDERATION_FOLLOW_LIMIT,
    FEDERATION_INBOX_LIMIT,
    FEDERATION_LOOKUP_LIMIT,
    FEDERATION_MAX_PAYLOAD_BYTES,
    FEDERATION_OUTBOX_LIMIT,
    limiter,
)
from app.db import db
from app.db.auth import User
from app.db.federation import (
    ActivityStatus,
    FederationActivity,
    FederationActor,
    FederationConsent,
    FederationFollower,
    FederationInstance,
    FollowStatus,
    TrustLevel,
)

federation_bp = Blueprint("federation", __name__, url_prefix="/federation")
wellknown_bp = Blueprint("wellknown", __name__, url_prefix="/.well-known")


def _get_base_url() -> str:
    """Return the configured base URL for federation endpoints."""
    return get_federation_base_url()


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
    """Apply CORS headers to public federation routes."""
    path = request.path
    if "/webfinger" in path or "/nodeinfo" in path or "/actor" in path:
        return _add_federation_headers(response)
    return response


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
    user: User | None = None

    if resource.startswith("acct:"):
        account_part = resource[5:]
        if "@" in account_part:
            username, req_domain = account_part.rsplit("@", 1)
            req_host = request.host.split(":")[0].strip().lower() if request.host else ""
            clean_req_domain = req_domain.strip().lower()
            req_domain_host = clean_req_domain.split(":")[0]
            allowed_domains = {domain.lower(), domain.split(":")[0].lower(), req_host}
            aliases_raw = current_app.config.get("FEDERATION_DOMAIN_ALIASES") or os.environ.get("FEDERATION_DOMAIN_ALIASES", "")
            if aliases_raw:
                allowed_domains |= {a.strip().lower() for a in aliases_raw.split(",") if a.strip()}
            if "iqoqo.kruk.cc" in allowed_domains:
                allowed_domains.add("iqoqo.cc")
            elif "iqoqo.cc" in allowed_domains:
                allowed_domains.add("iqoqo.kruk.cc")
            if clean_req_domain not in allowed_domains and req_domain_host not in allowed_domains:
                return jsonify({"error": f"Resource domain mismatch: {req_domain} != {domain}", "code": 404}), 404
        else:
            username = account_part
        # Look up by public_username, email, or email local-part
        stmt = select(User).where(
            or_(
                User.public_username == username,
                func.lower(User.email) == username.lower(),
                User.email.ilike(f"{username}@%"),
            )
        )
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

    # Require explicit user opt-in consent for federation
    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    is_opted_in = bool(consent and consent.federated_profile)
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
                "href": f"{base_url}/u/{user.public_username}" if user.public_username else base_url,
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

    base_url = _get_base_url()
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
            "instance_actor": f"{base_url}/api/federation/actor",
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

    # Resolve actor cryptographic public key without generating on-the-fly during unauthenticated GET
    public_key_pem = user.federation_public_key or federation_keys.get_actor_public_key(str(user.id))

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
        "url": f"{base_url}/u/{user.public_username}" if user.public_username else base_url,
        "inbox": f"{canonical_uri}/inbox",
        "outbox": f"{canonical_uri}/outbox",
        "followers": f"{canonical_uri}/followers",
        "following": f"{canonical_uri}/following",
        "publicKey": {
            "id": f"{canonical_uri}#main-key",
            "owner": canonical_uri,
            "publicKeyPem": public_key_pem,
        },
        "endpoints": {
            "sharedInbox": f"{base_url}/api/federation/inbox",
        },
    }


@federation_bp.route("/actor", methods=["GET"])
@federation_required
@limiter.limit("120 per minute")
def get_instance_actor() -> Response | tuple[Response, int]:
    """Instance Application actor document publishing the server public key."""
    public_key_pem = federation_keys.get_actor_public_key("server")
    if not public_key_pem:
        return jsonify({"error": "Instance actor not configured", "code": 404}), 404

    base_url = _get_base_url()
    actor_uri = f"{base_url}/api/federation/actor"
    domain = _get_domain()

    payload = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
        ],
        "id": actor_uri,
        "type": "Application",
        "preferredUsername": domain,
        "name": f"iqoqo ({domain})",
        "url": base_url,
        "inbox": f"{base_url}/api/federation/inbox",
        "outbox": f"{base_url}/api/federation/outbox",
        "publicKey": {
            "id": f"{actor_uri}#main-key",
            "owner": actor_uri,
            "publicKeyPem": public_key_pem,
        },
        "endpoints": {
            "sharedInbox": f"{base_url}/api/federation/inbox",
        },
    }

    resp = jsonify(payload)
    resp.mimetype = "application/activity+json"
    resp.headers["Content-Type"] = "application/activity+json; charset=utf-8"
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


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
    is_opted_in = bool(consent and consent.federated_profile)
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
    is_opted_in = bool(consent and consent.federated_profile)
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


@federation_bp.route("/inbox", methods=["POST"])
@federation_bp.route("/actor/u/<string:user_uuid>/inbox", methods=["POST"])
@federation_bp.route("/actor/<string:username>/inbox", methods=["POST"])
@federation_required
@limiter.limit(FEDERATION_INBOX_LIMIT)
def receive_inbox(user_uuid: str | None = None, username: str | None = None) -> Response | tuple[Response, int]:
    """ActivityPub inbox endpoint receiving inbound signed activities."""
    # 1. Bounded payload size check (protects against chunked transfer encoding bypass)
    content_length = request.content_length
    if content_length and content_length > FEDERATION_MAX_PAYLOAD_BYTES:
        return jsonify({"error": "Payload exceeds 100KB limit", "code": 413}), 413

    raw_body = request.get_data(cache=True)
    if len(raw_body) > FEDERATION_MAX_PAYLOAD_BYTES:
        return jsonify({"error": "Payload exceeds 100KB limit", "code": 413}), 413

    # 2. Per-actor route validation: ensure targeted local user exists and consented
    if user_uuid or username:
        target_user: User | None = None
        if user_uuid:
            try:
                target_user = db.session.execute(select(User).where(User.id == uuid.UUID(user_uuid))).scalars().first()
            except (ValueError, TypeError):
                target_user = None
        elif username:
            target_user = db.session.execute(select(User).where(User.public_username == username)).scalars().first()
            if not target_user:
                try:
                    target_user = db.session.execute(select(User).where(User.id == uuid.UUID(username))).scalars().first()
                except (ValueError, TypeError):
                    target_user = None

        if not target_user:
            return jsonify({"error": "Actor not found", "code": 404}), 404

        consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == target_user.id)).scalars().first()
        if not consent or not consent.federated_profile:
            return jsonify({"error": "Actor not found", "code": 404}), 404

    verified_actor: str | None = None
    try:
        verified_actor = verify_request(request)
    except SignatureVerificationError as exc:
        current_app.logger.warning("Inbound activity rejected (invalid HTTP signature): %s", exc)
        return jsonify({"error": f"Invalid signature: {exc}", "code": 401}), 401
    except Exception as exc:
        current_app.logger.warning("Signature verification error: %s", exc)
        return jsonify({"error": "Signature verification failed", "code": 401}), 401

    payload = request.get_json(silent=True)
    if not payload or not isinstance(payload, dict):
        return jsonify({"error": "Invalid or missing JSON payload", "code": 400}), 400

    activity_type = str(payload.get("type", "Create"))
    activity_id = str(payload.get("id") or uuid.uuid4())

    # Check if sending instance is blocked
    sender_domain = clean_instance_domain(verified_actor)
    if sender_domain:
        inst_stmt = select(FederationInstance).where(FederationInstance.domain == sender_domain)
        sender_instance = db.session.execute(inst_stmt).scalars().first()
        if sender_instance and sender_instance.trust_level == TrustLevel.BLOCKED:
            current_app.logger.warning("Rejected activity from blocked instance %s", sender_domain)
            return jsonify({"error": f"Instance {sender_domain} is blocked", "code": 403}), 403

    # Actor identity verification: payload actor MUST match verified signature actor
    payload_actor_raw = payload.get("actor")
    payload_actor = payload_actor_raw.get("id") if isinstance(payload_actor_raw, dict) else payload_actor_raw
    if payload_actor and str(payload_actor) != verified_actor:
        current_app.logger.warning("Actor mismatch in inbox: payload=%s, verified=%s", payload_actor, verified_actor)
        return jsonify({"error": "Payload actor does not match verified signature actor", "code": 403}), 403

    actor_uri = verified_actor

    # Record inbound activity log
    activity_rec: FederationActivity | None = None
    try:
        activity_rec = FederationActivity(
            actor_uri=actor_uri,
            activity_type=activity_type,
            object_json=payload,
            target_uri=request.url,
            direction="inbound",
            status=ActivityStatus.QUEUED,
        )
        db.session.add(activity_rec)
        db.session.commit()
    except Exception as exc:
        current_app.logger.error("Failed to record inbound activity: %s", exc)
        db.session.rollback()
        activity_rec = None

    # Dispatch via Celery or inline fallback
    if activity_rec and activity_rec.id:
        from app.core.federation_tasks import process_inbound_activity
        from app.core.tasks import submit_task

        task_id = submit_task(process_inbound_activity, str(activity_rec.id), payload, queue="federation")
        if not task_id:
            process_inbound_activity(str(activity_rec.id), payload)

    resp = jsonify({"status": "accepted", "id": activity_id})
    resp.status_code = 202
    return resp


@federation_bp.route("/actor/u/<string:user_uuid>/outbox", methods=["GET"])
@federation_bp.route("/actor/<string:username>/outbox", methods=["GET"])
@federation_required
@limiter.limit(FEDERATION_OUTBOX_LIMIT)
def actor_outbox(user_uuid: str | None = None, username: str | None = None) -> Response | tuple[Response, int]:
    """Per-actor outbox — read-only OrderedCollection of public activities."""
    user: User | None = None
    if user_uuid:
        try:
            user = db.session.execute(select(User).where(User.id == uuid.UUID(user_uuid))).scalars().first()
        except (ValueError, TypeError):
            user = None
    elif username:
        user = db.session.execute(select(User).where(User.public_username == username)).scalars().first()
        if not user:
            try:
                user = db.session.execute(select(User).where(User.id == uuid.UUID(username))).scalars().first()
            except (ValueError, TypeError):
                user = None

    if not user:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    if not consent or not consent.federated_profile:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    base_url = _get_base_url()
    canonical_uri = canonical_actor_iri(user.id, base_url)
    actor_uris = [canonical_uri]
    if user.public_username:
        actor_uris.append(f"{base_url}/api/federation/actor/{user.public_username}")

    page = request.args.get("page", type=int)
    per_page = 20

    if page is None:
        count_stmt = select(func.count(FederationActivity.id)).where(  # pylint: disable=not-callable
            FederationActivity.actor_uri.in_(actor_uris),
            FederationActivity.direction == "outbound",
            FederationActivity.status == ActivityStatus.DELIVERED,
        )
        total = db.session.execute(count_stmt).scalar() or 0

        data = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "OrderedCollection",
            "id": f"{canonical_uri}/outbox",
            "totalItems": total,
            "first": f"{canonical_uri}/outbox?page=1",
        }
        resp = jsonify(data)
        resp.mimetype = "application/activity+json"
        resp.headers["Content-Type"] = "application/activity+json; charset=utf-8"
        return resp

    page_num = max(1, page)
    items_stmt = (
        select(FederationActivity)
        .where(
            FederationActivity.actor_uri.in_(actor_uris),
            FederationActivity.direction == "outbound",
            FederationActivity.status == ActivityStatus.DELIVERED,
        )
        .order_by(FederationActivity.created_at.desc())
        .offset((page_num - 1) * per_page)
        .limit(per_page)
    )
    activities = db.session.execute(items_stmt).scalars().all()
    items = [a.object_json for a in activities if a.object_json]

    collection_page: dict[str, Any] = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollectionPage",
        "id": f"{canonical_uri}/outbox?page={page_num}",
        "partOf": f"{canonical_uri}/outbox",
        "orderedItems": items,
    }
    if len(items) == per_page:
        collection_page["next"] = f"{canonical_uri}/outbox?page={page_num + 1}"

    resp = jsonify(collection_page)
    resp.mimetype = "application/activity+json"
    resp.headers["Content-Type"] = "application/activity+json; charset=utf-8"
    return resp


@federation_bp.route("/actor/u/<string:user_uuid>/followers", methods=["GET"])
@federation_bp.route("/actor/<string:username>/followers", methods=["GET"])
@federation_required
@limiter.limit(FEDERATION_OUTBOX_LIMIT)
def actor_followers(user_uuid: str | None = None, username: str | None = None) -> Response | tuple[Response, int]:
    """Followers collection — returns count and metadata."""
    user: User | None = None
    if user_uuid:
        try:
            user = db.session.execute(select(User).where(User.id == uuid.UUID(user_uuid))).scalars().first()
        except (ValueError, TypeError):
            user = None
    elif username:
        user = db.session.execute(select(User).where(User.public_username == username)).scalars().first()

    if not user:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    if not consent or not consent.federated_profile:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    base_url = _get_base_url()
    canonical_uri = canonical_actor_iri(user.id, base_url)

    count_stmt = select(func.count(FederationFollower.id)).where(  # pylint: disable=not-callable
        FederationFollower.local_user_id == user.id,
        FederationFollower.status == FollowStatus.ACCEPTED,
    )
    count = db.session.execute(count_stmt).scalar() or 0

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "id": f"{canonical_uri}/followers",
        "totalItems": count,
    }
    resp = jsonify(data)
    resp.mimetype = "application/activity+json"
    resp.headers["Content-Type"] = "application/activity+json; charset=utf-8"
    return resp


@federation_bp.route("/actor/u/<string:user_uuid>/following", methods=["GET"])
@federation_bp.route("/actor/<string:username>/following", methods=["GET"])
@federation_required
@limiter.limit(FEDERATION_OUTBOX_LIMIT)
def actor_following(user_uuid: str | None = None, username: str | None = None) -> Response | tuple[Response, int]:
    """Following collection — returns count and metadata."""
    user: User | None = None
    if user_uuid:
        try:
            user = db.session.execute(select(User).where(User.id == uuid.UUID(user_uuid))).scalars().first()
        except (ValueError, TypeError):
            user = None
    elif username:
        user = db.session.execute(select(User).where(User.public_username == username)).scalars().first()

    if not user:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
    if not consent or not consent.federated_profile:
        return jsonify({"error": "Actor not found", "code": 404}), 404

    base_url = _get_base_url()
    canonical_uri = canonical_actor_iri(user.id, base_url)

    data = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "id": f"{canonical_uri}/following",
        "totalItems": 0,
    }
    resp = jsonify(data)
    resp.mimetype = "application/activity+json"
    resp.headers["Content-Type"] = "application/activity+json; charset=utf-8"
    return resp


@federation_bp.route("/lookup", methods=["GET"])
@require_auth
@federation_required
@limiter.limit(FEDERATION_LOOKUP_LIMIT)
def federation_lookup() -> Response | tuple[Response, int]:
    """Resolve remote actor handle via WebFinger and retrieve Actor JSON-LD document."""
    handle = request.args.get("handle", "").strip()
    if not handle:
        return jsonify({"error": "Missing 'handle' query parameter", "code": 400}), 400

    clean_handle = handle.lstrip("@")
    if "@" not in clean_handle:
        return jsonify({"error": "Invalid handle format. Expected username@domain", "code": 400}), 400

    username, domain = clean_handle.split("@", 1)
    scheme = "http" if ("localhost" in domain or "127.0.0.1" in domain or domain.startswith("peer-web")) else "https"
    webfinger_url = f"{scheme}://{domain}/.well-known/webfinger?resource=acct:{username}@{domain}"

    try:
        from app.utils.http_client import safe_get

        headers = {"Accept": "application/jrd+json, application/json"}
        wf_resp = safe_get(webfinger_url, headers=headers, timeout=5.0)
        if wf_resp.status_code != 200:
            return (
                jsonify({"error": f"WebFinger resolution failed with status {wf_resp.status_code}", "code": wf_resp.status_code}),
                wf_resp.status_code,
            )

        wf_data = wf_resp.json()
        actor_uri: str | None = None
        for link in wf_data.get("links", []):
            if link.get("rel") == "self" and "activity" in link.get("type", ""):
                actor_uri = link.get("href")
                break

        if not actor_uri:
            for link in wf_data.get("links", []):
                if link.get("rel") == "self":
                    actor_uri = link.get("href")
                    break

        if not actor_uri:
            return jsonify({"error": "No ActivityPub actor link found in WebFinger response", "code": 404}), 404

        client = FederationClient()
        actor_data = client.fetch_actor(actor_uri)
        if not actor_data:
            return jsonify({"error": "Failed to fetch remote Actor document", "code": 502}), 502

        return jsonify(
            {
                "success": True,
                "handle": f"@{username}@{domain}",
                "actor_uri": actor_uri,
                "actor": actor_data,
            }
        )
    except Exception as exc:
        current_app.logger.warning("Remote federation lookup error for %s: %s", handle, exc)
        return jsonify({"error": "Remote federation lookup failed", "code": 500}), 500


@federation_bp.route("/follow", methods=["POST"])
@require_auth
@federation_required
@limiter.limit(FEDERATION_FOLLOW_LIMIT)
def federation_follow_remote() -> Response | tuple[Response, int]:
    """Initiate an outbound Follow activity to a remote Actor."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401
    current_user = db.session.get(User, user_id)
    if not current_user:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    payload = request.get_json(silent=True) or {}
    target_handle = payload.get("handle")
    target_actor_uri = payload.get("actor_uri")
    target_inbox_url = payload.get("inbox_url")

    client = FederationClient()

    if target_handle and not target_actor_uri:
        clean_handle = str(target_handle).lstrip("@")
        if "@" in clean_handle:
            username, domain = clean_handle.split("@", 1)
            scheme = "http" if ("localhost" in domain or "127.0.0.1" in domain) else "https"
            wf_url = f"{scheme}://{domain}/.well-known/webfinger?resource=acct:{username}@{domain}"
            try:
                from app.utils.http_client import safe_get

                wf_resp = safe_get(wf_url, headers={"Accept": "application/jrd+json, application/json"}, timeout=5.0)
                if wf_resp.status_code == 200:
                    for link in wf_resp.json().get("links", []):
                        if link.get("rel") == "self":
                            target_actor_uri = link.get("href")
                            break
            except Exception as exc:
                current_app.logger.warning("WebFinger lookup error: %s", exc)

    if not target_actor_uri:
        return jsonify({"error": "Missing target_actor_uri or unresolvable handle", "code": 400}), 400

    actor_data = client.fetch_actor(str(target_actor_uri))
    if not actor_data:
        return jsonify({"error": f"Failed to retrieve remote actor at {target_actor_uri}", "code": 502}), 502

    inbox_url = target_inbox_url or actor_data.get("inbox")
    if not inbox_url:
        return jsonify({"error": "Remote actor document lacks an inbox endpoint", "code": 400}), 400

    base_url = _get_base_url()
    alpha_actor_uri = canonical_actor_iri(current_user.id, base_url)

    follow_activity: dict[str, Any] = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "id": f"{base_url}/activities/{uuid.uuid4()}",
        "type": "Follow",
        "actor": alpha_actor_uri,
        "object": target_actor_uri,
    }

    try:
        resp = client.post_to_inbox(inbox_url, follow_activity, sender_user_id=str(current_user.id))
        if resp.status_code in (200, 201, 202):
            # Ensure FederationActor exists in DB
            actor_stmt = select(FederationActor).where(FederationActor.actor_uri == target_actor_uri)
            remote_actor_rec = db.session.execute(actor_stmt).scalars().first()
            if not remote_actor_rec:
                from app.core.federation_handlers import _get_or_create_actor

                remote_actor_rec = _get_or_create_actor(target_actor_uri)

            if remote_actor_rec:
                follower_stmt = select(FederationFollower).where(
                    FederationFollower.local_user_id == current_user.id,
                    FederationFollower.remote_actor_id == remote_actor_rec.id,
                )
                follower = db.session.execute(follower_stmt).scalars().first()
                if not follower:
                    follower = FederationFollower(
                        local_user_id=current_user.id,
                        remote_actor_id=remote_actor_rec.id,
                        status=FollowStatus.PENDING,
                    )
                    db.session.add(follower)
                    try:
                        db.session.commit()
                    except IntegrityError:
                        db.session.rollback()

            return (
                jsonify(
                    {
                        "success": True,
                        "status": "delivered",
                        "activity": follow_activity,
                        "remote_actor": actor_data,
                    }
                ),
                200,
            )
        return (
            jsonify(
                {
                    "error": f"Remote inbox returned HTTP {resp.status_code}",
                    "code": resp.status_code,
                }
            ),
            resp.status_code,
        )
    except Exception as exc:
        current_app.logger.error("Outbound federation follow error: %s", exc)
        return jsonify({"error": "Outbound delivery failed", "code": 500}), 500


@federation_bp.route("/friends", methods=["GET"])
@require_auth
@federation_required
@limiter.limit("60 per minute")
def get_federated_friends() -> Response | tuple[Response, int]:
    """Retrieve accepted federated friends for current user."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401
    current_user = db.session.get(User, user_id)
    if not current_user:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    stmt = (
        select(FederationFollower, FederationActor)
        .join(FederationActor, FederationFollower.remote_actor_id == FederationActor.id)
        .where(
            FederationFollower.local_user_id == current_user.id,
            FederationFollower.status == FollowStatus.ACCEPTED,
        )
    )
    rows = db.session.execute(stmt).all()
    friends = []
    for follower, actor in rows:
        instance_domain = actor.instance.domain if actor.instance else None
        handle = f"@{actor.username}@{instance_domain}" if (actor.username and instance_domain) else actor.actor_uri
        friends.append(
            {
                "follower_id": follower.id,
                "actor_id": actor.id,
                "actor_uri": actor.actor_uri,
                "username": actor.username,
                "display_name": actor.display_name,
                "instance_domain": instance_domain,
                "handle": handle,
                "created_at": follower.created_at.isoformat() if follower.created_at else None,
            }
        )
    return jsonify({"success": True, "data": friends}), 200


@federation_bp.route("/friends/<int:actor_id>/collections", methods=["GET"])
@require_auth
@federation_required
@limiter.limit("30 per minute")
def get_friend_collections(actor_id: int) -> Response | tuple[Response, int]:
    """Browse federated friend's collection and wishlist with local caching."""
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Unauthorized", "code": 401}), 401
    current_user = db.session.get(User, user_id)
    if not current_user:
        return jsonify({"error": "Unauthorized", "code": 401}), 401

    # Verify friend relationship
    stmt = (
        select(FederationFollower, FederationActor)
        .join(FederationActor, FederationFollower.remote_actor_id == FederationActor.id)
        .where(
            FederationFollower.local_user_id == current_user.id,
            FederationFollower.remote_actor_id == actor_id,
            FederationFollower.status == FollowStatus.ACCEPTED,
        )
    )
    res = db.session.execute(stmt).first()
    if not res:
        return jsonify({"error": "Friend not found or not accepted", "code": 404}), 404

    _, actor = res
    force_refresh = request.args.get("refresh", "").lower() in {"true", "1", "yes"}

    client = FederationClient()
    try:
        collections = client.fetch_actor_collections(actor.actor_uri, force_refresh=force_refresh)
        return jsonify({"success": True, "data": collections or {}}), 200
    except Exception as exc:
        current_app.logger.warning("Error fetching collections for friend %s: %s", actor.actor_uri, exc)
        return jsonify({"error": "Failed to fetch friend collections", "code": 502}), 502


@federation_bp.route("/directory", methods=["GET"])
@federation_bp.route("/instance-info", methods=["GET"])
@limiter.limit("60 per minute")
def get_federation_directory() -> Response:
    """Return public directory listing of connected, verified peer libraries and instance overview."""
    from app.api.federation_guard import is_federation_enabled
    from app.config import Config
    from app.core.iri import get_federation_base_url
    from app.db.core import Item

    fed_enabled = is_federation_enabled()
    if fed_enabled:
        from app.core.federation_discovery import is_publicly_routable_peer_domain

        # 1. Fetch public peer libraries from Trust Graph (trusted or untrusted)
        stmt = (
            select(FederationInstance)
            .where(FederationInstance.trust_level.in_([TrustLevel.TRUSTED, TrustLevel.UNTRUSTED]))
            .order_by(FederationInstance.last_seen_at.desc().nullslast())
        )
        all_peers = db.session.execute(stmt).scalars().all()
        peers = [p for p in all_peers if is_publicly_routable_peer_domain(p.domain)]
    else:
        peers = []

    # 2. Local public items stats
    public_items_count = (
        db.session.execute(select(func.count(Item.id)).where(Item.is_hidden.is_(False))).scalar() or 0  # pylint: disable=not-callable
    )

    base_url = get_federation_base_url()
    local_domain = urlparse(base_url).netloc if base_url else "localhost"

    directory_data = {
        "local_instance": {
            "domain": local_domain,
            "software_name": "iqoqo",
            "software_version": Config.VERSION,
            "public_items_count": public_items_count,
            "federation_enabled": fed_enabled,
        },
        "peers": [peer.to_dict() for peer in peers],
        "total_peers": len(peers),
        "federation_enabled": fed_enabled,
    }

    return jsonify({"success": True, "data": directory_data}), 200
