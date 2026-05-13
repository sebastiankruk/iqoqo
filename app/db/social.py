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
import uuid
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import JSONB, UUID

from . import db

_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")

_INVENTORY: str | None = "inventory" if _USE_PG else None
_INVENTORY_PFX: str = f"{_INVENTORY}." if _INVENTORY else ""

_AUTH: str | None = "auth" if _USE_PG else None
_AUTH_PFX: str = f"{_AUTH}." if _AUTH else ""


class SharedCollection(db.Model):  # type: ignore[name-defined]
    """
    Represents a customized, shareable view of a user's collection.
    Allows users to share specific subsets (e.g., Wishlist) via a secure token.
    """

    __tablename__ = "shared_collections"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False)
    share_token = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    filters = db.Column(JSONB if _USE_PG else db.JSON, server_default="{}", nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    user = db.relationship("User", backref=db.backref("shared_collections", lazy="dynamic"))

    def to_dict(self) -> dict:
        """Serialize the shared collection."""
        return {
            "id": self.id,
            "share_token": self.share_token,
            "name": self.name,
            "description": self.description,
            "filters": self.filters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
