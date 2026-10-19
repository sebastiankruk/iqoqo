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
"""Fediverse instance discovery and health monitoring."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select

from app.db import db
from app.db.federation import FederationInstance, TrustLevel
from app.utils.http_client import SSRFError, safe_get

logger = logging.getLogger(__name__)


def clean_instance_domain(domain_or_url: str) -> str:
    """Normalize input domain or URL to lowercase host.

    Args:
        domain_or_url: Raw domain string or full URL.

    Returns:
        Normalized domain hostname (with port if non-standard).
    """
    cleaned = domain_or_url.strip()
    if not cleaned:
        return ""
    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower().strip()
    if parsed.port and parsed.port not in (80, 443):
        return f"{host}:{parsed.port}"
    return host


def discover_instance(domain_or_url: str) -> FederationInstance | None:
    """Discover a remote Fediverse instance via NodeInfo and register or update it.

    Args:
        domain_or_url: Remote instance domain or base URL.

    Returns:
        FederationInstance if registered or found, None if domain is invalid.
    """
    domain = clean_instance_domain(domain_or_url)
    if not domain:
        return None

    stmt = select(FederationInstance).where(FederationInstance.domain == domain)
    instance = db.session.execute(stmt).scalars().first()

    if not instance:
        instance = FederationInstance(
            domain=domain,
            trust_level=TrustLevel.UNTRUSTED,
            created_at=datetime.now(UTC),
        )
        db.session.add(instance)
        db.session.flush()

    probe_instance_health(instance)
    return instance


def probe_instance_health(instance: FederationInstance) -> bool:
    """Perform a health probe against a remote instance via NodeInfo or root URL.

    Respects TrustLevel.BLOCKED: blocked instances are never probed.
    On success, updates `last_seen_at` and software metadata.
    Supports both HTTPS and HTTP for local/staging federation pair environments.

    Args:
        instance: The FederationInstance record to probe.

    Returns:
        True if the remote instance responded positively, False otherwise.
    """
    import os

    if instance.trust_level == TrustLevel.BLOCKED:
        logger.debug("Skipping health probe for blocked instance: %s", instance.domain)
        return False

    schemes = ["https"]
    if os.environ.get("FEDERATION_ALLOW_LOOPBACK") == "true" or ":" in instance.domain or instance.domain in ("localhost", "peer-web"):
        schemes = ["https", "http"]

    timeout = (5, 10)

    for scheme in schemes:
        base_url = f"{scheme}://{instance.domain}"
        nodeinfo_well_known = f"{base_url}/.well-known/nodeinfo"

        try:
            resp = safe_get(nodeinfo_well_known, headers={"Accept": "application/json"}, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                links = data.get("links", []) if isinstance(data, dict) else []
                nodeinfo_href = None
                for link in links:
                    if isinstance(link, dict) and "2." in link.get("rel", ""):
                        nodeinfo_href = link.get("href")
                        break

                if nodeinfo_href:
                    ni_resp = safe_get(nodeinfo_href, headers={"Accept": "application/json"}, timeout=timeout)
                    if ni_resp.status_code == 200:
                        ni_data = ni_resp.json()
                        software = ni_data.get("software", {}) if isinstance(ni_data, dict) else {}
                        if isinstance(software, dict):
                            instance.software_name = str(software.get("name") or instance.software_name or "")[:100] or None
                            instance.software_version = str(software.get("version") or instance.software_version or "")[:50] or None
                        metadata = ni_data.get("metadata", {}) if isinstance(ni_data, dict) else {}
                        if isinstance(metadata, dict) and metadata.get("sharedInbox"):
                            instance.shared_inbox_url = str(metadata["sharedInbox"])[:500]

                instance.last_seen_at = datetime.now(UTC)
                db.session.commit()
                return True

            # Fallback probe to root base_url
            root_resp = safe_get(base_url, timeout=timeout)
            if root_resp.status_code < 500:
                instance.last_seen_at = datetime.now(UTC)
                db.session.commit()
                return True

        except SSRFError as exc:
            logger.warning("SSRF blocked probe for %s: %s", instance.domain, exc)
            return False
        except Exception as exc:
            logger.debug("Health probe attempt via %s failed for %s: %s", scheme, instance.domain, exc)
            continue

    return False


def probe_registered_instances() -> dict[str, bool]:
    """Execute health checks for all non-blocked instances registered in the database.

    Returns:
        Mapping of domain to probe success status.
    """
    stmt = select(FederationInstance).where(FederationInstance.trust_level != TrustLevel.BLOCKED)
    instances = db.session.execute(stmt).scalars().all()

    results: dict[str, bool] = {}
    for inst in instances:
        results[inst.domain] = probe_instance_health(inst)

    return results
