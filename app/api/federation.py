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
"""ActivityPub Federation API endpoints.

Provides:
- WebFinger (/.well-known/webfinger)
- NodeInfo (/.well-known/nodeinfo)
- Actor profiles
- Inbox (per-actor and shared)
- Outbox (per-actor, read-only)
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse

from flask import Blueprint, Response, jsonify, request

from app.api.federation_guard import federation_required
from app.core.config_service import ConfigService
from app.db import db
from app.db.auth import User
from app.db.federation import (
    ActivityStatus,
    FederationActivity,
    FederationConsent,
)

logger = logging.getLogger(__name__)

federation_bp = Blueprint("federation", __name__)

# Maximum accepted inbox payload size (100 KB)
_MAX_INBOX_PAYLOAD = 100 * 1024


def _get_base_url() -> str:
    """Get the federation base URL from configuration."""
    base_url = ConfigService.get("FEDERATION_BASE_URL", "http://localhost:3000")
    return str(base_url).rstrip("/")


def _get_instance_domain() -> str:
    """Extract domain from base URL."""
    base_url = _get_base_url()
    parsed = urlparse(base_url)
    return parsed.hostname or "localhost"


# ---------------------------------------------------------------------------
# WebFinger
# ---------------------------------------------------------------------------


@federation_bp.route("/.well-known/webfinger")
@federation_required
def webfinger():
    """WebFinger endpoint for actor discovery.

    GET /.well-known/webfinger?resource=acct:user@domain
    """
    resource = request.args.get("resource", "")

    if not resource.startswith("acct:"):
        return jsonify({"error": "Invalid resource format. Expected acct:user@domain"}), 400

    # Parse acct:user@domain
    acct = resource[5:]  # Remove "acct:" prefix
    if "@" not in acct:
        return jsonify({"error": "Invalid resource format"}), 400

    username, domain = acct.rsplit("@", 1)
    instance_domain = _get_instance_domain()

    if domain != instance_domain:
        return jsonify({"error": "Unknown domain"}), 404

    # Look up user
    user = User.query.filter_by(public_username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check federation consent
    consent = FederationConsent.query.filter_by(user_id=user.id).first()
    if not consent or not consent.federated_profile:
        return jsonify({"error": "User not found"}), 404

    base_url = _get_base_url()
    actor_url = f"{base_url}/api/federation/actor/{username}"

    jrd = {
        "subject": resource,
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": actor_url,
            }
        ],
    }

    return Response(
        json.dumps(jrd),
        content_type="application/jrd+json; charset=utf-8",
        status=200,
    )


# ---------------------------------------------------------------------------
# NodeInfo
# ---------------------------------------------------------------------------


@federation_bp.route("/.well-known/nodeinfo")
@federation_required
def nodeinfo_wellknown():
    """NodeInfo well-known endpoint — points to the full NodeInfo document."""
    base_url = _get_base_url()

    return jsonify(
        {
            "links": [
                {
                    "rel": "http://nodeinfo.diaspora.software/ns/schema/2.1",
                    "href": f"{base_url}/api/federation/nodeinfo/2.1",
                }
            ]
        }
    )


@federation_bp.route("/api/federation/nodeinfo/2.1")
@federation_required
def nodeinfo():
    """NodeInfo 2.1 document — instance metadata for Fediverse discovery."""
    from app.config import Config

    user_count = User.query.filter_by(is_active=True).count()

    return jsonify(
        {
            "version": "2.1",
            "software": {
                "name": "iqoqo",
                "version": Config.VERSION,
                "repository": "https://github.com/sebastiankruk/iqoqo",
            },
            "protocols": ["activitypub"],
            "services": {
                "inbound": [],
                "outbound": [],
            },
            "openRegistrations": False,
            "usage": {
                "users": {
                    "total": user_count,
                },
                "localPosts": 0,
            },
            "metadata": {
                "nodeName": _get_instance_domain(),
                "federation": {
                    "enabled": True,
                },
            },
        }
    )


# ---------------------------------------------------------------------------
# Actor Profile
# ---------------------------------------------------------------------------


@federation_bp.route("/api/federation/actor/<username>")
@federation_required
def actor_profile(username: str):
    """ActivityPub Actor profile endpoint.

    Returns a JSON-LD Actor document with inbox, outbox, and public key.
    """
    user = User.query.filter_by(public_username=username).first()
    if not user:
        return jsonify({"error": "Actor not found"}), 404

    # Check federation consent
    consent = FederationConsent.query.filter_by(user_id=user.id).first()
    if not consent or not consent.federated_profile:
        return jsonify({"error": "Actor not found"}), 404

    base_url = _get_base_url()
    actor_url = f"{base_url}/api/federation/actor/{username}"

    actor = {
        "@context": [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
        ],
        "type": "Person",
        "id": actor_url,
        "preferredUsername": username,
        "name": user.display_name or username,
        "inbox": f"{actor_url}/inbox",
        "outbox": f"{actor_url}/outbox",
        "followers": f"{actor_url}/followers",
        "following": f"{actor_url}/following",
        "url": f"{base_url}/u/{username}",
    }

    # Add public key if available
    if user.federation_public_key:
        actor["publicKey"] = {
            "id": f"{actor_url}#main-key",
            "owner": actor_url,
            "publicKeyPem": user.federation_public_key,
        }

    return Response(
        json.dumps(actor),
        content_type="application/activity+json; charset=utf-8",
        status=200,
    )


# ---------------------------------------------------------------------------
# Inbox
# ---------------------------------------------------------------------------


@federation_bp.route("/api/federation/actor/<username>/inbox", methods=["POST"])
@federation_required
def actor_inbox(username: str):
    """Per-actor inbox — receives activities from remote servers.

    Verifies HTTP Signature, validates payload, and queues for processing.
    """
    return _process_inbox(username=username)


@federation_bp.route("/api/federation/inbox", methods=["POST"])
@federation_required
def shared_inbox():
    """Shared inbox — receives activities targeting multiple local actors."""
    return _process_inbox(username=None)


def _parse_inbox_body():
    """Parse and verify the inbox request body and HTTP signature.

    Returns (activity, key_id) on success, or (response, status_code) on error.
    The caller distinguishes success by checking ``isinstance(result[1], str)``.
    """
    content_length = request.content_length or 0
    if content_length > _MAX_INBOX_PAYLOAD:
        return jsonify({"error": "Payload too large"}), 413

    body = request.get_data()
    if len(body) > _MAX_INBOX_PAYLOAD:
        return jsonify({"error": "Payload too large"}), 413

    from app.core.http_signatures import SignatureVerificationError, verify_flask_request

    try:
        key_id = verify_flask_request(request)
    except SignatureVerificationError as exc:
        logger.warning("Signature verification failed: %s", exc)
        return jsonify({"error": "Signature verification failed"}), 401

    try:
        activity = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return jsonify({"error": "Invalid JSON"}), 400

    if not activity.get("type") or not activity.get("actor"):
        return jsonify({"error": "Missing required fields"}), 400

    return activity, key_id


def _process_inbox(username: str | None):
    """Common inbox processing logic."""
    result = _parse_inbox_body()
    if isinstance(result[1], int):
        return result

    activity, key_id = result
    actor_uri = activity["actor"]
    activity_type = activity["type"]

    # Verify actor URI domain matches signature keyId domain
    key_domain = urlparse(key_id.split("#")[0]).hostname
    actor_domain = urlparse(actor_uri).hostname
    if key_domain != actor_domain:
        logger.warning("Actor domain mismatch: key=%s actor=%s", key_domain, actor_domain)
        return jsonify({"error": "Actor domain mismatch"}), 403

    # Check if sending instance is blocked
    from app.db.federation import FederationInstance, TrustLevel

    instance = FederationInstance.query.filter_by(domain=actor_domain).first()
    if instance and instance.trust_level == TrustLevel.BLOCKED:
        return jsonify({"error": "Instance blocked"}), 403

    # If targeting a specific user, verify they exist and have federation consent
    if username:
        user = User.query.filter_by(public_username=username).first()
        consent = FederationConsent.query.filter_by(user_id=user.id).first() if user else None
        if not user or not consent or not consent.federated_profile:
            return jsonify({"error": "User not found"}), 404

    # Log the activity
    fed_activity = FederationActivity(
        actor_uri=actor_uri,
        activity_type=activity_type,
        object_json=activity,
        target_uri=username or "shared",
        direction="inbound",
        status=ActivityStatus.QUEUED,
    )
    db.session.add(fed_activity)
    db.session.commit()

    # Queue for async processing via Celery; fall back to inline
    from app.core.federation_tasks import process_inbound_activity
    from app.core.tasks import submit_task

    task_id = submit_task(process_inbound_activity, str(fed_activity.id), activity)
    if not task_id:
        # Celery unavailable — process inline
        process_inbound_activity(str(fed_activity.id), activity)

    return jsonify({"status": "accepted"}), 202


# ---------------------------------------------------------------------------
# Outbox
# ---------------------------------------------------------------------------


@federation_bp.route("/api/federation/actor/<username>/outbox")
@federation_required
def actor_outbox(username: str):
    """Per-actor outbox — read-only OrderedCollection of public activities."""
    user = User.query.filter_by(public_username=username).first()
    if not user:
        return jsonify({"error": "Actor not found"}), 404

    consent = FederationConsent.query.filter_by(user_id=user.id).first()
    if not consent or not consent.federated_profile:
        return jsonify({"error": "Actor not found"}), 404

    base_url = _get_base_url()
    actor_url = f"{base_url}/api/federation/actor/{username}"

    # Fetch recent outbound activities for this user
    page = request.args.get("page", type=int)
    per_page = 20

    if page is None:
        # Return collection metadata only
        total = FederationActivity.query.filter_by(
            actor_uri=actor_url,
            direction="outbound",
            status=ActivityStatus.DELIVERED,
        ).count()

        return Response(
            json.dumps(
                {
                    "@context": "https://www.w3.org/ns/activitystreams",
                    "type": "OrderedCollection",
                    "id": f"{actor_url}/outbox",
                    "totalItems": total,
                    "first": f"{actor_url}/outbox?page=1",
                }
            ),
            content_type="application/activity+json; charset=utf-8",
        )

    # Return paginated items
    activities = (
        FederationActivity.query.filter_by(
            actor_uri=actor_url,
            direction="outbound",
            status=ActivityStatus.DELIVERED,
        )
        .order_by(FederationActivity.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = [a.object_json for a in activities if a.object_json]

    collection_page = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollectionPage",
        "id": f"{actor_url}/outbox?page={page}",
        "partOf": f"{actor_url}/outbox",
        "orderedItems": items,
    }

    if len(items) == per_page:
        collection_page["next"] = f"{actor_url}/outbox?page={page + 1}"

    return Response(
        json.dumps(collection_page),
        content_type="application/activity+json; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Followers / Following (stubs)
# ---------------------------------------------------------------------------


@federation_bp.route("/api/federation/actor/<username>/followers")
@federation_required
def actor_followers(username: str):
    """Followers collection — returns count only (privacy)."""
    from app.db.federation import FederationFollower, FollowStatus

    user = User.query.filter_by(public_username=username).first()
    if not user:
        return jsonify({"error": "Actor not found"}), 404

    consent = FederationConsent.query.filter_by(user_id=user.id).first()
    if not consent or not consent.federated_profile:
        return jsonify({"error": "Actor not found"}), 404

    count = FederationFollower.query.filter_by(
        local_user_id=user.id,
        status=FollowStatus.ACCEPTED,
    ).count()

    base_url = _get_base_url()
    actor_url = f"{base_url}/api/federation/actor/{username}"

    return Response(
        json.dumps(
            {
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "OrderedCollection",
                "id": f"{actor_url}/followers",
                "totalItems": count,
            }
        ),
        content_type="application/activity+json; charset=utf-8",
    )


@federation_bp.route("/api/federation/actor/<username>/following")
@federation_required
def actor_following(username: str):
    """Following collection — currently empty (S2S only)."""
    user = User.query.filter_by(public_username=username).first()
    if not user:
        return jsonify({"error": "Actor not found"}), 404

    base_url = _get_base_url()
    actor_url = f"{base_url}/api/federation/actor/{username}"

    return Response(
        json.dumps(
            {
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "OrderedCollection",
                "id": f"{actor_url}/following",
                "totalItems": 0,
            }
        ),
        content_type="application/activity+json; charset=utf-8",
    )
