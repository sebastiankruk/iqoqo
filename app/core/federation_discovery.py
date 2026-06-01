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
"""Federation instance discovery and health checking."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.config_service import ConfigService
from app.core.federation_client import SSRFError, federation_client
from app.db import db
from app.db.federation import FederationInstance, TrustLevel

logger = logging.getLogger(__name__)


def discover_instance(domain: str) -> FederationInstance | None:
    """Discover and register a remote iqoqo/federation-compatible instance.

    Fetches NodeInfo from the domain to verify it supports ActivityPub.

    Args:
        domain: The domain to discover (e.g., "books.example.com").

    Returns:
        FederationInstance record or None if discovery failed.
    """
    # Check if already known
    existing = FederationInstance.query.filter_by(domain=domain).first()
    if existing:
        return existing  # type: ignore[no-any-return]

    # Fetch NodeInfo
    try:
        nodeinfo = federation_client.fetch_nodeinfo(domain)
    except SSRFError:
        logger.warning("SSRF blocked during discovery of %s", domain)
        return None

    if not nodeinfo:
        logger.info("No NodeInfo found for %s", domain)
        return None

    # Verify it supports ActivityPub
    protocols = nodeinfo.get("protocols", [])
    if "activitypub" not in protocols:
        logger.info("Instance %s does not support ActivityPub", domain)
        return None

    software = nodeinfo.get("software", {})
    software_name = software.get("name", "unknown")
    software_version = software.get("version", "")

    # Determine shared inbox URL
    shared_inbox_url = f"https://{domain}/api/federation/inbox"

    default_trust = ConfigService.get("FEDERATION_DEFAULT_TRUST", TrustLevel.UNTRUSTED)

    instance = FederationInstance(
        domain=domain,
        shared_inbox_url=shared_inbox_url,
        software_name=software_name,
        software_version=software_version,
        last_seen_at=datetime.now(UTC),
        trust_level=str(default_trust),
    )
    db.session.add(instance)
    db.session.commit()

    logger.info("Discovered instance %s (software: %s %s)", domain, software_name, software_version)
    return instance


def verify_instance_health(instance_id: int) -> bool:
    """Verify a remote instance is still reachable and update last_seen_at.

    Args:
        instance_id: ID of the FederationInstance to check.

    Returns:
        True if instance is healthy.
    """
    instance = db.session.get(FederationInstance, instance_id)
    if not instance:
        return False

    try:
        nodeinfo = federation_client.fetch_nodeinfo(instance.domain)
    except SSRFError:
        return False

    if nodeinfo:
        instance.last_seen_at = datetime.now(UTC)
        # Update software info if changed
        software = nodeinfo.get("software", {})
        if software.get("name"):
            instance.software_name = software["name"]
        if software.get("version"):
            instance.software_version = software["version"]
        db.session.commit()
        return True

    return False


def check_all_instances_health() -> dict[str, int]:
    """Run health checks on all non-blocked instances.

    Intended to be called by the scheduler periodically.

    Returns:
        Dict with counts of healthy and unreachable instances.
    """
    instances = FederationInstance.query.filter(FederationInstance.trust_level != TrustLevel.BLOCKED).all()

    healthy = 0
    unreachable = 0

    for instance in instances:
        if verify_instance_health(instance.id):
            healthy += 1
        else:
            unreachable += 1

    logger.info("Federation health check: %d healthy, %d unreachable", healthy, unreachable)
    return {"healthy": healthy, "unreachable": unreachable}
