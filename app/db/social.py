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
"""Shared collections model for library exposure."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import JSONB, UUID

from . import db

_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")

_INVENTORY: str | None = "inventory" if _USE_PG else None
_INVENTORY_PFX: str = f"{_INVENTORY}." if _INVENTORY else ""

_AUTH: str | None = "auth" if _USE_PG else None
_AUTH_PFX: str = f"{_AUTH}." if _AUTH else ""

_CATALOG: str | None = "catalog" if _USE_PG else None
_CATALOG_PFX: str = f"{_CATALOG}." if _CATALOG else ""


class SharedCollection(db.Model):  # type: ignore[name-defined]
    """
    Represents a customized, shareable view of a user's collection.
    Allows users to share specific subsets (e.g., Wishlist) via a secure token.
    """

    __tablename__ = "shared_collections"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False)
    # secrets.token_urlsafe(32) => 256 bits of entropy (vs. uuid4's 122 bits).
    share_token = db.Column(db.String(64), default=lambda: secrets.token_urlsafe(32), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filters = db.Column(JSONB if _USE_PG else db.JSON, server_default="{}", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    # Optional TTL: NULL means the link never expires.
    expires_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("shared_collections", lazy="dynamic", cascade="all, delete-orphan"))

    @property
    def is_expired(self) -> bool:
        """Whether this share link's TTL (if any) has elapsed."""
        if self.expires_at is None:
            return False
        dt: datetime = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=UTC)
        return datetime.now(UTC) > dt

    def to_dict(self) -> dict:
        """Serialize the shared collection."""
        return {
            "id": self.id,
            "share_token": self.share_token,
            "name": self.name,
            "description": self.description,
            "filters": self.filters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class SocialFeedback(db.Model):  # type: ignore[name-defined]
    """
    User rating and comment on any level of the FRBR hierarchy.
    Exactly one of work_id, expression_id, manifestation_id, or item_id must be set.
    """

    __tablename__ = "social_feedbacks"
    __table_args__: tuple = (
        (
            db.CheckConstraint(
                "(case when work_id is not null then 1 else 0 end + "
                "case when expression_id is not null then 1 else 0 end + "
                "case when manifestation_id is not null then 1 else 0 end + "
                "case when item_id is not null then 1 else 0 end) = 1",
                name="chk_feedback_target_exactly_one",
            ),
            db.CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="chk_feedback_rating_range"),
            db.UniqueConstraint("user_id", "work_id", name="uq_user_work_feedback"),
            db.UniqueConstraint("user_id", "expression_id", name="uq_user_expression_feedback"),
            db.UniqueConstraint("user_id", "manifestation_id", name="uq_user_manifestation_feedback"),
            db.UniqueConstraint("user_id", "item_id", name="uq_user_item_feedback"),
            {"schema": _INVENTORY},
        )
        if _INVENTORY
        else (
            db.CheckConstraint(
                "(case when work_id is not null then 1 else 0 end + "
                "case when expression_id is not null then 1 else 0 end + "
                "case when manifestation_id is not null then 1 else 0 end + "
                "case when item_id is not null then 1 else 0 end) = 1",
                name="chk_feedback_target_exactly_one",
            ),
            db.CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="chk_feedback_rating_range"),
            db.UniqueConstraint("user_id", "work_id", name="uq_user_work_feedback"),
            db.UniqueConstraint("user_id", "expression_id", name="uq_user_expression_feedback"),
            db.UniqueConstraint("user_id", "manifestation_id", name="uq_user_manifestation_feedback"),
            db.UniqueConstraint("user_id", "item_id", name="uq_user_item_feedback"),
        )
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)

    # FRBR hierarchy relations
    work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), nullable=True, index=True)
    expression_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}expressions.id", ondelete="CASCADE"), nullable=True, index=True)
    manifestation_id = db.Column(
        db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    item_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"), nullable=True, index=True)

    rating = db.Column(db.Integer, nullable=True)  # rating 1 to 5
    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    user = db.relationship("User", backref=db.backref("feedbacks", cascade="all, delete-orphan", lazy="dynamic"))

    def to_dict(self) -> dict:
        """Serialize the feedback details."""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "user_display_name": self.user.display_name if self.user else "Anonymous",
            "user_username": self.user.public_username if self.user else None,
            "user_avatar_url": self.user.avatar_url if self.user else None,
            "work_id": self.work_id,
            "expression_id": self.expression_id,
            "manifestation_id": self.manifestation_id,
            "item_id": self.item_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SocialNote(db.Model):  # type: ignore[name-defined]
    """
    User personal note or comment on any level of the FRBR hierarchy.
    A user can create multiple notes on the same resource without rating.
    Exactly one of work_id, expression_id, manifestation_id, or item_id must be set.
    """

    __tablename__ = "social_notes"
    __table_args__: tuple = (
        (
            db.CheckConstraint(
                "(case when work_id is not null then 1 else 0 end + "
                "case when expression_id is not null then 1 else 0 end + "
                "case when manifestation_id is not null then 1 else 0 end + "
                "case when item_id is not null then 1 else 0 end) = 1",
                name="chk_note_target_exactly_one",
            ),
            {"schema": _INVENTORY},
        )
        if _INVENTORY
        else (
            db.CheckConstraint(
                "(case when work_id is not null then 1 else 0 end + "
                "case when expression_id is not null then 1 else 0 end + "
                "case when manifestation_id is not null then 1 else 0 end + "
                "case when item_id is not null then 1 else 0 end) = 1",
                name="chk_note_target_exactly_one",
            ),
        )
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)

    # FRBR hierarchy relations
    work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), nullable=True, index=True)
    expression_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}expressions.id", ondelete="CASCADE"), nullable=True, index=True)
    manifestation_id = db.Column(
        db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    item_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"), nullable=True, index=True)

    note = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    user = db.relationship("User", backref=db.backref("notes", cascade="all, delete-orphan", lazy="dynamic"))

    def to_dict(self) -> dict:
        """Serialize the note details."""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "user_display_name": self.user.display_name if self.user else "Anonymous",
            "user_username": self.user.public_username if self.user else None,
            "user_avatar_url": self.user.avatar_url if self.user else None,
            "work_id": self.work_id,
            "expression_id": self.expression_id,
            "manifestation_id": self.manifestation_id,
            "item_id": self.item_id,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EscalationRequest(db.Model):  # type: ignore[name-defined]
    """
    User escalation request targeting a field on any level of the FRBR hierarchy for custodian review.
    At most one of work_id, expression_id, manifestation_id, or item_id is set (may become null if entity deleted).
    """

    __tablename__ = "escalation_requests"
    __table_args__: tuple = (
        (
            db.CheckConstraint(
                "(case when work_id is not null then 1 else 0 end + "
                "case when expression_id is not null then 1 else 0 end + "
                "case when manifestation_id is not null then 1 else 0 end + "
                "case when item_id is not null then 1 else 0 end) <= 1",
                name="chk_escalation_target_exactly_one",
            ),
            db.CheckConstraint(
                "status IN ('pending', 'accepted', 'rejected', 'duplicate')",
                name="chk_escalation_status_valid",
            ),
            {"schema": _INVENTORY},
        )
        if _INVENTORY
        else (
            db.CheckConstraint(
                "(case when work_id is not null then 1 else 0 end + "
                "case when expression_id is not null then 1 else 0 end + "
                "case when manifestation_id is not null then 1 else 0 end + "
                "case when item_id is not null then 1 else 0 end) <= 1",
                name="chk_escalation_target_exactly_one",
            ),
            db.CheckConstraint(
                "status IN ('pending', 'accepted', 'rejected', 'duplicate')",
                name="chk_escalation_status_valid",
            ),
        )
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)

    # FRBR hierarchy relations
    work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="SET NULL"), nullable=True, index=True)
    expression_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}expressions.id", ondelete="SET NULL"), nullable=True, index=True)
    manifestation_id = db.Column(
        db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="SET NULL"), nullable=True, index=True)

    target_type = db.Column(db.String(20), nullable=True)
    field_name = db.Column(db.String(100), nullable=False)
    current_value = db.Column(db.Text, nullable=True)
    suggested_value = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text, nullable=True)
    request_type = db.Column(db.String(20), default="correction", nullable=False)

    status = db.Column(db.String(20), default="pending", nullable=False, index=True)

    resolved_by = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_note = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    user = db.relationship(
        "User", foreign_keys=[user_id], backref=db.backref("escalation_requests", cascade="all, delete-orphan", lazy="dynamic")
    )
    resolver = db.relationship("User", foreign_keys=[resolved_by])

    work = db.relationship("Work", backref=db.backref("escalation_requests", lazy="dynamic"))
    expression = db.relationship("Expression", backref=db.backref("escalation_requests", lazy="dynamic"))
    manifestation = db.relationship("Manifestation", backref=db.backref("escalation_requests", lazy="dynamic"))
    item = db.relationship("Item", backref=db.backref("escalation_requests", lazy="dynamic"))

    def to_dict(self) -> dict:
        """Serialize the escalation request details."""
        return {
            "id": self.id,
            "user_id": str(self.user_id),
            "user_display_name": self.user.display_name if self.user else "Anonymous",
            "user_username": self.user.public_username if self.user else None,
            "user_avatar_url": self.user.avatar_url if self.user else None,
            "work_id": self.work_id,
            "expression_id": self.expression_id,
            "manifestation_id": self.manifestation_id,
            "item_id": self.item_id,
            "target_type": self.target_type
            or (
                "manifestation"
                if self.manifestation_id
                else "item" if self.item_id else "work" if self.work_id else "expression" if self.expression_id else None
            ),
            "field_name": self.field_name,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "note": self.note,
            "request_type": self.request_type,
            "status": self.status,
            "resolved_by": str(self.resolved_by) if self.resolved_by else None,
            "resolver_display_name": (self.resolver.display_name or self.resolver.public_username) if self.resolver else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
