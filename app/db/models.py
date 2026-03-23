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
import uuid
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

#: Canonical list of allowed Item statuses.  This is the single source of truth
#: on the Python side; the TypeScript ``ItemStatus`` union in
#: ``frontend/types/frbr.ts`` must stay in sync with these values.
ITEM_STATUSES: tuple[str, ...] = ("available", "lent", "lost", "wish_list", "reading", "read", "unread")

# RBAC Association Tables

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(db.Model):  # type: ignore[name-defined]
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))


class Role(db.Model):  # type: ignore[name-defined]
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="selectin")


class User(db.Model):  # type: ignore[name-defined]
    __tablename__ = "users"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500), nullable=True)  # Increased from 255 to handle long URLs
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    last_login = db.Column(db.DateTime, nullable=True)
    visibility = db.Column(db.String(20), default="private")

    roles = db.relationship("Role", secondary=user_roles, lazy="selectin", backref=db.backref("users", lazy="dynamic"))
    items = db.relationship("Item", backref="owner", lazy="dynamic")
    consents = db.relationship("ConsentRecord", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name: str) -> bool:
        for role in self.roles:  # type: ignore[attr-defined]
            for perm in role.permissions:  # type: ignore[attr-defined]
                if perm.name == permission_name:
                    return True
        return False

    def to_dict(self):
        """Serialize core user fields for API responses and tests."""
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ConsentRecord(db.Model):  # type: ignore[name-defined]
    __tablename__ = "user_consents"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type = db.Column(db.String(50), nullable=False, index=True)
    is_granted = db.Column(db.Boolean, nullable=False)
    policy_version = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))


# ... FRBR models (Work, Expression, Manifestation, LLMTelemetry)


class Work(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Work
    A distinct intellectual or artistic creation.
    e.g., "The Hobbit" (the story itself, regardless of language).
    """

    __tablename__ = "works"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(1000), nullable=False)  # Increased from 255 to handle long titles
    # Flexible metadata (e.g., original_language, first_performance_date)
    meta = db.Column(db.JSON, default={})

    # Relationships
    expressions = db.relationship("Expression", backref="work", lazy=True)


class Expression(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Expression
    The intellectual realization of a work.
    e.g., The English text of The Hobbit, or the German translation.
    """

    __tablename__ = "expressions"
    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, db.ForeignKey("works.id"), nullable=False)
    content_type = db.Column(db.String(50))  # e.g., 'text', 'sound', 'notated_music'
    language = db.Column(db.String(10))  # e.g., 'en', 'pl'
    meta = db.Column(db.JSON, default={})

    # Relationships
    manifestations = db.relationship("Manifestation", backref="expression", lazy=True)


class Manifestation(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Manifestation
    The physical or digital embodiment of an expression.
    e.g., The 1937 Allen & Unwin Hardcover edition.
    """

    __tablename__ = "manifestations"
    id = db.Column(db.Integer, primary_key=True)
    expression_id = db.Column(db.Integer, db.ForeignKey("expressions.id"), nullable=False)

    # Identifiers
    isbn13 = db.Column(db.String(13), index=True, unique=True)
    upc = db.Column(db.String(12), index=True)
    ean = db.Column(db.String(13), index=True)

    publisher = db.Column(db.String(500))  # Increased from 255 for long publisher names
    publication_date = db.Column(db.Date)
    cover_url = db.Column(db.String(255), nullable=True)
    meta = db.Column(db.JSON, default={})  # Stores cover images, page count, dimensions

    def update_meta(self, **kwargs):
        """Safely updates the meta JSON field."""
        meta = dict(self.meta) if self.meta else {}
        meta.update(kwargs)
        self.meta = meta

    # Relationships
    items = db.relationship("Item", backref="manifestation", lazy=True)


class Item(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Item
    A single exemplar of a manifestation.
    e.g., The specific book on your shelf.
    """

    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey("manifestations.id"), nullable=False)

    # User ownership data
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = db.Column(db.String(50), default="available")  # see ITEM_STATUSES for valid values
    condition = db.Column(db.String(50))

    added_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    meta = db.Column(db.JSON, default={})  # Custom tags, notes, location on shelf


class LLMTelemetry(db.Model):  # type: ignore[name-defined]
    __tablename__ = "llm_telemetry"
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.String(100), nullable=False)
    images_generated = db.Column(db.Integer, default=0)
    estimated_cost_usd = db.Column(db.Float, default=0.0)
    total_duration_seconds = db.Column(db.Float, default=0.0)
    __table_args__ = (db.UniqueConstraint("provider", "user_id", name="uq_provider_user"),)


class InstanceSettings(db.Model):  # type: ignore[name-defined]
    """
    Stores global configuration for the iqoqo instance (e.g., federation toggles,
    affiliate links, default language).
    """

    __tablename__ = "instance_settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
