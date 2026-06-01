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
"""Federation models (federation schema)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import JSONB, UUID

from . import db

# ---------------------------------------------------------------------------
# Schema selector
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")
_JSON_TYPE = JSONB if _USE_PG else db.JSON

_FED: str | None = "federation" if _USE_PG else None
_FED_PFX: str = f"{_FED}." if _FED else ""
_AUTH_PFX: str = "auth." if _USE_PG else ""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TrustLevel:
    """Trust level constants for federation instances."""

    UNTRUSTED = "untrusted"
    PENDING = "pending"
    TRUSTED = "trusted"
    BLOCKED = "blocked"

    ALL = (UNTRUSTED, PENDING, TRUSTED, BLOCKED)


class FollowStatus:
    """Follow relationship status constants."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

    ALL = (PENDING, ACCEPTED, REJECTED)


class ActivityStatus:
    """Activity delivery status constants."""

    QUEUED = "queued"
    DELIVERED = "delivered"
    FAILED = "failed"

    ALL = (QUEUED, DELIVERED, FAILED)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FederationInstance(db.Model):  # type: ignore[name-defined]
    """Remote instance registry."""

    __tablename__ = "federation_instances"
    __table_args__ = ({"schema": _FED},) if _FED else ()

    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    shared_inbox_url = db.Column(db.String(500), nullable=True)
    software_name = db.Column(db.String(100), nullable=True)
    software_version = db.Column(db.String(50), nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    trust_level = db.Column(db.String(20), nullable=False, default=TrustLevel.UNTRUSTED)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    actors = db.relationship("FederationActor", backref="instance", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "id": self.id,
            "domain": self.domain,
            "shared_inbox_url": self.shared_inbox_url,
            "software_name": self.software_name,
            "software_version": self.software_version,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "trust_level": self.trust_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FederationActor(db.Model):  # type: ignore[name-defined]
    """Cached remote actor profiles."""

    __tablename__ = "federation_actors"
    __table_args__ = ({"schema": _FED},) if _FED else ()

    id = db.Column(db.Integer, primary_key=True)
    actor_uri = db.Column(db.String(500), unique=True, nullable=False, index=True)
    inbox_url = db.Column(db.String(500), nullable=False)
    outbox_url = db.Column(db.String(500), nullable=True)
    public_key_pem = db.Column(db.Text, nullable=True)
    instance_id = db.Column(db.Integer, db.ForeignKey(f"{_FED_PFX}federation_instances.id", ondelete="CASCADE"), nullable=False)
    display_name = db.Column(db.String(200), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    last_fetched_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    followers = db.relationship("FederationFollower", backref="remote_actor", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "id": self.id,
            "actor_uri": self.actor_uri,
            "inbox_url": self.inbox_url,
            "outbox_url": self.outbox_url,
            "instance_id": self.instance_id,
            "display_name": self.display_name,
            "username": self.username,
            "last_fetched_at": self.last_fetched_at.isoformat() if self.last_fetched_at else None,
        }


class FederationFollower(db.Model):  # type: ignore[name-defined]
    """Follow relationships between remote actors and local users."""

    __tablename__ = "federation_followers"
    __table_args__ = ({"schema": _FED},) if _FED else ()

    id = db.Column(db.Integer, primary_key=True)
    local_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)
    remote_actor_id = db.Column(
        db.Integer, db.ForeignKey(f"{_FED_PFX}federation_actors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status = db.Column(db.String(20), nullable=False, default=FollowStatus.PENDING)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "id": self.id,
            "local_user_id": str(self.local_user_id),
            "remote_actor_id": self.remote_actor_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FederationActivity(db.Model):  # type: ignore[name-defined]
    """Outbox/activity log for tracking sent and received activities."""

    __tablename__ = "federation_activities"
    __table_args__ = ({"schema": _FED},) if _FED else ()

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_uri = db.Column(db.String(500), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    object_json = db.Column(_JSON_TYPE, nullable=True)
    target_uri = db.Column(db.String(500), nullable=True)
    direction = db.Column(db.String(10), nullable=False, default="outbound")  # inbound | outbound
    delivered_at = db.Column(db.DateTime, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default=ActivityStatus.QUEUED)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "id": str(self.id),
            "actor_uri": self.actor_uri,
            "activity_type": self.activity_type,
            "object_json": self.object_json,
            "target_uri": self.target_uri,
            "direction": self.direction,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "retry_count": self.retry_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FederationConsent(db.Model):  # type: ignore[name-defined]
    """Per-user federation opt-in consent."""

    __tablename__ = "federation_consents"
    __table_args__ = ({"schema": _FED},) if _FED else ()

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    federated_profile = db.Column(db.Boolean, nullable=False, default=False)
    federated_collection = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "user_id": str(self.user_id),
            "federated_profile": self.federated_profile,
            "federated_collection": self.federated_collection,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
