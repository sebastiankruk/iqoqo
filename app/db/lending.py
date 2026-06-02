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
"""
Lending data layer: tracks loan requests between borrowers and item owners.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import UUID

from . import db

load_dotenv()
_USE_PG = os.environ.get("DATABASE_URL", "").strip("'\"").startswith("postgresql")

#: The PostgreSQL schema name for inventory tables, or ``None`` for SQLite.
_INVENTORY: str | None = "inventory" if _USE_PG else None
#: FK prefix — ``"inventory."`` in PostgreSQL, ``""`` in SQLite.
_INVENTORY_PFX: str = f"{_INVENTORY}." if _INVENTORY else ""

#: The PostgreSQL schema name for auth tables, or ``None`` for SQLite.
_AUTH: str | None = "auth" if _USE_PG else None
#: FK prefix — ``"auth."`` in PostgreSQL, ``""`` in SQLite.
_AUTH_PFX: str = f"{_AUTH}." if _AUTH else ""

#: Valid loan request statuses.
LOAN_REQUEST_STATUSES: tuple[str, ...] = ("pending", "approved", "rejected")


class LoanRequest(db.Model):  # type: ignore[name-defined]
    """
    A request from a borrower (requester) to loan an Item from its owner.

    Lifecycle:
    - ``pending``  — request submitted, awaiting owner action
    - ``approved`` — owner approved; item collection_status set to ``lent``
    - ``rejected`` — owner rejected the request
    """

    __tablename__ = "loan_requests"
    __table_args__ = (
        (
            {
                "schema": _INVENTORY,
                "extend_existing": True,
            },
        )
        if _INVENTORY
        else ({"extend_existing": True},)
    )

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(20), default="pending", nullable=False)  # see LOAN_REQUEST_STATUSES
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    item = db.relationship("Item", backref=db.backref("loan_requests", cascade="all, delete-orphan", lazy="dynamic"))
    requester = db.relationship("User", backref=db.backref("loan_requests_sent", lazy="dynamic"))

    def to_dict(self) -> dict[str, Any]:
        """Serialises a LoanRequest record for API responses."""
        item_title: str = "Unknown"
        if self.item and self.item.manifestation:
            item_title = self.item.manifestation.title

        requester_name: str = "Unknown"
        if self.requester:
            requester_name = self.requester.display_name or self.requester.email or "Unknown"

        return {
            "id": self.id,
            "item_id": self.item_id,
            "item_title": item_title,
            "requester_id": str(self.requester_id) if self.requester_id else None,
            "requester_name": requester_name,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
