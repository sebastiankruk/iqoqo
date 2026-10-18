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
"""SSRF-safe ActivityPub Federation Client wrapping safe_get and safe_post."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import requests

from app.core import federation_keys
from app.core.http_signatures import sign_request
from app.core.iri import canonical_actor_iri, get_lod_base_url
from app.core.telemetry import record_outbound_telemetry
from app.utils.http_client import SSRFError, safe_get, safe_post

logger = logging.getLogger(__name__)


class FederationClient:
    """Outbound ActivityPub client with socket-level SSRF defense and HTTP Signatures."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    @staticmethod
    def _record_delivery_failure(target_url: str, reason: str) -> None:
        """Record outbound federation delivery failure metric."""
        try:
            from app.core.telemetry import federation_delivery_failures_total

            domain = urlparse(target_url).netloc.lower() or "unknown"
            federation_delivery_failures_total.add(1, {"domain": domain, "reason": reason})
        except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, ImportError):
            pass

    def fetch_actor(self, actor_uri: str) -> dict[str, Any] | None:
        """Fetch remote ActivityPub Actor document with SSRF protection and local cache.

        Args:
            actor_uri: Fully qualified URI of remote actor.

        Returns:
            Parsed JSON actor document or None if retrieval fails.

        Raises:
            SSRFError: If target URL points to a restricted private or loopback IP.
        """
        headers = {
            "Accept": 'application/activity+json, application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            "User-Agent": "iqoqo-federation/0.9.0",
        }
        record_outbound_telemetry("Federation", headers, url=actor_uri)

        try:
            resp = safe_get(actor_uri, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                self._record_delivery_failure(actor_uri, f"http_{resp.status_code}")
                logger.warning("Failed to fetch actor %s: HTTP %d", actor_uri, resp.status_code)
                return None
            data = resp.json()
        except SSRFError:
            self._record_delivery_failure(actor_uri, "ssrf_blocked")
            raise
        except Exception as exc:
            self._record_delivery_failure(actor_uri, "network_error")
            logger.error("Error fetching actor %s: %s", actor_uri, exc)
            return None

        # Attempt to cache actor and instance in database if within application context
        try:
            self._cache_actor_in_db(actor_uri, data)
        except Exception as exc:
            logger.debug("Could not cache actor %s in DB: %s", actor_uri, exc)

        return data

    def _cache_actor_in_db(self, actor_uri: str, data: dict[str, Any]) -> None:
        """Store or update actor details in FederationActor and FederationInstance models."""
        from app.db import db
        from app.db.federation import FederationActor, FederationInstance, TrustLevel

        domain = urlparse(actor_uri).netloc.lower()
        if not domain:
            return

        stmt = db.select(FederationInstance).where(FederationInstance.domain == domain)
        instance = db.session.execute(stmt).scalars().first()
        if not instance:
            endpoints = data.get("endpoints") or {}
            shared_inbox = endpoints.get("sharedInbox") if isinstance(endpoints, dict) else None
            instance = FederationInstance(
                domain=domain,
                shared_inbox_url=shared_inbox,
                trust_level=TrustLevel.UNTRUSTED,
            )
            db.session.add(instance)
            db.session.flush()

        actor_stmt = db.select(FederationActor).where(FederationActor.actor_uri == actor_uri)
        actor = db.session.execute(actor_stmt).scalars().first()

        pk_pem = None
        pk_info = data.get("publicKey")
        if isinstance(pk_info, dict):
            pk_pem = pk_info.get("publicKeyPem")

        if not actor:
            actor = FederationActor(
                actor_uri=actor_uri,
                inbox_url=data.get("inbox") or f"{actor_uri}/inbox",
                outbox_url=data.get("outbox"),
                public_key_pem=pk_pem,
                instance_id=instance.id,
                display_name=data.get("name"),
                username=data.get("preferredUsername"),
                last_fetched_at=datetime.now(UTC),
            )
            db.session.add(actor)
        else:
            actor.inbox_url = data.get("inbox") or actor.inbox_url
            actor.outbox_url = data.get("outbox") or actor.outbox_url
            if pk_pem:
                actor.public_key_pem = pk_pem
            actor.display_name = data.get("name") or actor.display_name
            actor.username = data.get("preferredUsername") or actor.username
            actor.last_fetched_at = datetime.now(UTC)

        db.session.commit()

    def post_to_inbox(
        self,
        target_inbox_url: str,
        activity: dict[str, Any],
        sender_user_id: str | None = None,
    ) -> requests.Response:
        """Deliver signed ActivityPub activity payload to target inbox.

        Args:
            target_inbox_url: Recipient inbox endpoint.
            activity: ActivityStreams JSON dictionary.
            sender_user_id: Local UUID string of the sending user actor.

        Returns:
            requests.Response from the remote instance.

        Raises:
            SSRFError: If target inbox points to a restricted IP.
            requests.RequestException: On transmission failures.
        """
        body_bytes = json.dumps(activity).encode("utf-8")
        headers = {
            "Content-Type": "application/activity+json",
            "User-Agent": "iqoqo-federation/0.9.0",
        }

        # If sender_user_id specified, sign request with actor key
        if sender_user_id:
            priv_key = federation_keys.get_actor_private_key(sender_user_id)
            if not priv_key:
                try:
                    federation_keys.generate_actor_keypair(sender_user_id)
                    priv_key = federation_keys.get_actor_private_key(sender_user_id)
                except Exception as exc:
                    logger.warning("Could not auto-generate keypair for %s: %s", sender_user_id, exc)
            if priv_key:
                from flask import current_app, has_app_context

                base_url = (current_app.config.get("BASE_URL") or get_lod_base_url()) if has_app_context() else get_lod_base_url()
                key_id = f"{canonical_actor_iri(sender_user_id, base_url)}#main-key"
                headers = sign_request(
                    method="POST",
                    url=target_inbox_url,
                    body=body_bytes,
                    key_id=key_id,
                    private_key=priv_key,
                    headers=headers,
                )

        record_outbound_telemetry("Federation", headers, url=target_inbox_url)

        try:
            resp = safe_post(
                target_inbox_url,
                data=body_bytes,
                headers=headers,
                timeout=self.timeout,
            )
            if resp.status_code >= 400:
                self._record_delivery_failure(target_inbox_url, f"http_{resp.status_code}")
            return resp
        except SSRFError:
            self._record_delivery_failure(target_inbox_url, "ssrf_blocked")
            raise
        except Exception:
            self._record_delivery_failure(target_inbox_url, "network_error")
            raise
