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
Roadmap data layer handling the sequential tracking of user reading queues.
Tied directly into the custom PostgreSQL schema.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import Any, cast

from sqlalchemy.dialects.postgresql import UUID

from . import db

_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")

#: The PostgreSQL schema name for FRBR catalog tables, or ``None`` for SQLite.
_CATALOG: str | None = "catalog" if _USE_PG else None
#: FK prefix — ``"catalog."`` in PostgreSQL, ``""`` in SQLite.
_CATALOG_PFX: str = f"{_CATALOG}." if _CATALOG else ""

#: The PostgreSQL schema name for auth tables, or ``None`` for SQLite.
_AUTH: str | None = "auth" if _USE_PG else None
#: FK prefix — ``"auth."`` in PostgreSQL, ``""`` in SQLite.
_AUTH_PFX: str = f"{_AUTH}." if _AUTH else ""


class ReadingRoadmap(db.Model):  # type: ignore[name-defined]
    """
    Roadmap tracking model that groups ordered roadmap items.
    """

    __tablename__ = "reading_roadmaps"
    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    items = db.relationship(
        "RoadmapItem",
        backref="roadmap",
        lazy="joined",
        order_by="RoadmapItem.position",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, Any]:
        """Converts roadmap object to serialization-safe dictionary structure."""
        items_list = cast(list[RoadmapItem], self.items) if self.items is not None else []
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": [item.to_dict() for item in sorted(items_list, key=lambda x: x.position)],
        }


class RoadmapItem(db.Model):  # type: ignore[name-defined]
    """
    Individual items sequentially placed on a reading roadmap.
    """

    __tablename__ = "roadmap_items"
    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_CATALOG_PFX}reading_roadmaps.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="SET NULL"),
        nullable=True,
    )
    manifestation_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="SET NULL"),
        nullable=True,
    )
    position = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default="queued", nullable=False)  # queued, in_progress, completed
    target_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships to resolve title/creator in to_dict()
    work = db.relationship("Work", foreign_keys=[work_id], lazy="joined")
    manifestation = db.relationship("Manifestation", foreign_keys=[manifestation_id], lazy="joined")

    def to_dict(self) -> dict[str, Any]:
        """Converts individual roadmap nodes to dynamic dictionary objects.

        Resolves ``title`` and ``creator`` by walking the FRBR hierarchy:
        manifestation → expression → work (title, meta.authors).
        """
        title: str = "Unknown"
        creator: str = "Unknown"

        # Prefer resolution via the linked manifestation (most specific)
        if self.manifestation_id is not None and hasattr(self, "manifestation") and self.manifestation is not None:
            man = self.manifestation
            if man.expression and man.expression.work:
                work = man.expression.work
                title = work.title or "Unknown"
                authors = work.meta.get("authors", []) if work.meta else []
                if authors and isinstance(authors, list) and isinstance(authors[0], str):
                    creator = authors[0]
        # Fall back to direct work link
        elif self.work_id is not None and hasattr(self, "work") and self.work is not None:
            work = self.work
            title = work.title or "Unknown"
            authors = work.meta.get("authors", []) if work.meta else []
            if authors and isinstance(authors, list) and isinstance(authors[0], str):
                creator = authors[0]

        return {
            "id": self.id,
            "work_id": self.work_id,
            "manifestation_id": self.manifestation_id,
            "title": title,
            "creator": creator,
            "position": self.position,
            "status": self.status,
            "target_date": (self.target_date.isoformat() if isinstance(self.target_date, (date, datetime)) else None),
            "notes": self.notes,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
        }
