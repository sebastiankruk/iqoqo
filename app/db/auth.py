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
"""Authentication and RBAC models (public schema)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import check_password_hash, generate_password_hash

if TYPE_CHECKING:
    from app.core.permissions import PermissionName

from . import db

# ---------------------------------------------------------------------------
# Schema selector
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").strip("'\"").startswith("postgresql")

_AUTH: str | None = "auth" if _USE_PG else None
_AUTH_PFX: str = f"{_AUTH}." if _AUTH else ""

# ---------------------------------------------------------------------------
# RBAC association tables
# ---------------------------------------------------------------------------

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey(f"{_AUTH_PFX}roles.id", ondelete="CASCADE"), primary_key=True),
    schema=_AUTH,
)

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey(f"{_AUTH_PFX}roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey(f"{_AUTH_PFX}permissions.id", ondelete="CASCADE"), primary_key=True),
    schema=_AUTH,
)


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class TokenBlocklist(db.Model):  # type: ignore[name-defined]
    """JWT token revocation blocklist."""

    __tablename__ = "token_blocklist"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class Permission(db.Model):  # type: ignore[name-defined]
    """A granular permission that can be assigned to roles."""

    __tablename__ = "permissions"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))


class Role(db.Model):  # type: ignore[name-defined]
    """A named role that aggregates permissions."""

    __tablename__ = "roles"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="selectin")


class User(db.Model):  # type: ignore[name-defined]
    """
    Application user.  Supports local password auth as well as Google OAuth.
    """

    __tablename__ = "users"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.String(100))
    public_username = db.Column(db.String(50), unique=True, nullable=True, index=True)
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    apple_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    last_login = db.Column(db.DateTime, nullable=True)
    visibility = db.Column(db.String(20), default="private")

    roles = db.relationship("Role", secondary=user_roles, lazy="selectin", backref=db.backref("users", lazy="dynamic"))
    items = db.relationship("Item", foreign_keys="Item.owner_id", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    lent_items = db.relationship("Item", foreign_keys="Item.lent_to_user_id", backref="borrower", lazy="dynamic")
    consents = db.relationship("ConsentRecord", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and store a new password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if *password* matches the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name: PermissionName | str) -> bool:
        """Return True if the user holds *permission_name* through any role."""
        perm_val = permission_name.value if hasattr(permission_name, "value") else permission_name
        for role in self.roles:  # type: ignore[attr-defined]
            for perm in role.permissions:  # type: ignore[attr-defined]
                if perm.name == perm_val:
                    return True
        return False

    def to_dict(self) -> dict:
        """Serialize core user fields for API responses and tests."""
        return {
            "id": str(self.id) if self.id else None,
            "email": self.email,
            "display_name": self.display_name,
            "public_username": self.public_username,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def list_llm_permissions(cls, user: User | None) -> dict[str, bool]:
        """Return a dict of LLM-related permissions for *user*."""
        if not user:
            return {
                "allow_generate_cover": False,
                "allow_cloud_llm": False,
                "allow_generate_metadata": False,
            }

        from app.core.permissions import PermissionName

        return {
            "allow_generate_cover": user.has_permission(PermissionName.LLM_GENERATE_COVER),
            "allow_cloud_llm": user.has_permission(PermissionName.LLM_GENERATE_CLOUD),
            "allow_generate_metadata": user.has_permission(PermissionName.LLM_GENERATE_METADATA),
        }


class ConsentRecord(db.Model):  # type: ignore[name-defined]
    """GDPR consent record for a user."""

    __tablename__ = "user_consents"
    __table_args__ = ({"schema": _AUTH},) if _AUTH else ()

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False)
    consent_type = db.Column(db.String(50), nullable=False, index=True)
    is_granted = db.Column(db.Boolean, nullable=False)
    policy_version = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
