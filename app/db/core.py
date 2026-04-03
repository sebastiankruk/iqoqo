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
"""Core FRBR hierarchy models (catalog schema).

FRBR Group 1 entities:
  Work → Expression → Manifestation → Item

All four tables live in the ``catalog`` PostgreSQL schema, keeping them
logically separated from the auth/settings tables in ``public``.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import TSVECTOR, UUID

from . import db

# ---------------------------------------------------------------------------
# Schema selector
# Use the "catalog" PostgreSQL schema in production.  SQLite (used in tests)
# does not support named schemas, so we fall back to no schema.
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")
# In test environments (pytest), default to non-Postgres (no schemas/FTS) unless
# FTS tests are explicitly enabled. This ensures tests run correctly on SQLite
# even if DATABASE_URL is set in the environment.
if "pytest" in sys.modules and os.environ.get("ENABLE_FTS_TESTS") != "true":
    _USE_PG = False

#: The PostgreSQL schema name for FRBR catalog tables, or ``None`` for SQLite.
_CATALOG: str | None = "catalog" if _USE_PG else None
#: FK prefix — ``"catalog."`` in PostgreSQL, ``""`` in SQLite.
_CATALOG_PFX: str = f"{_CATALOG}." if _CATALOG else ""

#: The PostgreSQL schema name for inventory tables, or ``None`` for SQLite.
_INVENTORY: str | None = "inventory" if _USE_PG else None
#: FK prefix — ``"inventory."`` in PostgreSQL, ``""`` in SQLite.
_INVENTORY_PFX: str = f"{_INVENTORY}." if _INVENTORY else ""

#: The PostgreSQL schema name for auth tables, or ``None`` for SQLite.
_AUTH: str | None = "auth" if _USE_PG else None
#: FK prefix — ``"auth."`` in PostgreSQL, ``""`` in SQLite.
_AUTH_PFX: str = f"{_AUTH}." if _AUTH else ""

#: Canonical list of allowed Item statuses.  This is the single source of truth
#: on the Python side; the TypeScript ``ItemStatus`` union in
#: ``frontend/types/frbr.ts`` must stay in sync with these values.
#:
#: Statuses are grouped by media type for readability:
#:   - generic:       available, lent, lost, wish_list, ordered, damaged
#:   - text media:    reading, read, unread, want_to_read (alias: wish_list)
#:   - audio media:   listening, listened, want_to_listen
ITEM_STATUSES: tuple[str, ...] = (
    "available",
    "lent",
    "lost",
    "wish_list",
    "ordered",
    "damaged",
    "reading",
    "read",
    "unread",
    "want_to_read",
    "listening",
    "listened",
    "want_to_listen",
)


class Work(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Work.

    A distinct intellectual or artistic creation.
    E.g., "The Hobbit" (the story itself, language-agnostic).
    """

    __tablename__ = "works"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(1000), nullable=False)
    meta = db.Column(db.JSON, default=dict)

    # Full-text search column for PostgreSQL (production only; skipped in SQLite tests)
    if os.environ.get("DATABASE_URL", "").startswith("postgresql") and (
        "pytest" not in sys.modules or os.environ.get("ENABLE_FTS_TESTS") == "true"
    ):
        fts_simple = db.Column(
            TSVECTOR(),
            db.Computed(
                "to_tsvector('simple'::regconfig, (((COALESCE(title, ''::character varying))::text"
                " || ' '::text) || COALESCE((meta ->> 'authors'::text), ''::text)))",
                persisted=True,
            ),
            nullable=True,
        )
        __table_args__: tuple = (
            db.Index("ix_works_fts", fts_simple, postgresql_using="gin"),
            {"schema": _CATALOG},
        )
    else:
        fts_simple = db.Column(db.Text, db.FetchedValue(), nullable=True)
        __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()  # type: ignore[assignment]

    # Relationships
    expressions = db.relationship("Expression", backref="work", lazy=True)
    contributions = db.relationship("WorkContribution", backref="work", lazy="selectin", cascade="all, delete-orphan")
    parts = db.relationship(
        "WorkPart",
        foreign_keys="WorkPart.container_work_id",
        backref=db.backref("container", lazy="joined"),
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    member_of = db.relationship(
        "WorkPart",
        foreign_keys="WorkPart.part_work_id",
        backref=db.backref("part", lazy="joined"),
        lazy="selectin",
    )


class Expression(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Expression.

    The intellectual or artistic realization of a Work.
    E.g., the English text of The Hobbit, or the German audiobook recording.
    """

    __tablename__ = "expressions"
    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()

    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id"), nullable=False)
    content_type = db.Column(db.String(50))  # e.g., 'text', 'sound', 'notated_music', 'video'
    language = db.Column(db.String(10))  # BCP-47 language tag, e.g., 'en', 'pl'
    meta = db.Column(db.JSON, default=dict)

    # Relationships
    manifestations = db.relationship("Manifestation", backref="expression", lazy=True)
    contributions = db.relationship("ExpressionContribution", backref="expression", lazy="selectin", cascade="all, delete-orphan")


class Manifestation(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Manifestation.

    The physical or digital embodiment of an Expression.
    E.g., the 1937 Allen & Unwin hardcover; a specific CD pressing.
    """

    __tablename__ = "manifestations"

    id = db.Column(db.Integer, primary_key=True)
    expression_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}expressions.id"), nullable=False)

    # Identifiers — at least one is expected for cover/lookup purposes
    isbn13 = db.Column(db.String(13), index=True, unique=True)
    upc = db.Column(db.String(12), index=True)
    ean = db.Column(db.String(13), index=True)

    publisher = db.Column(db.String(500))
    publication_date = db.Column(db.Date)
    cover_url = db.Column(db.String(255), nullable=True)
    meta = db.Column(db.JSON, default=dict)

    # Full-text search column for PostgreSQL (production only; skipped in SQLite tests)
    if os.environ.get("DATABASE_URL", "").startswith("postgresql") and (
        "pytest" not in sys.modules or os.environ.get("ENABLE_FTS_TESTS") == "true"
    ):
        fts_simple = db.Column(
            TSVECTOR(),
            db.Computed(
                "to_tsvector('simple'::regconfig, (((((COALESCE(isbn13, ''::character varying))::text"
                " || ' '::text) || COALESCE((meta ->> 'publisher'::text), ''::text))"
                " || ' '::text) || COALESCE((meta ->> 'alt_title'::text), ''::text)))",
                persisted=True,
            ),
            nullable=True,
        )
        __table_args__: tuple = (
            db.Index("ix_manifestations_fts", fts_simple, postgresql_using="gin"),
            {"schema": _CATALOG},
        )
    else:
        fts_simple = db.Column(db.Text, db.FetchedValue(), nullable=True)
        __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()  # type: ignore[assignment]

    @property
    def title(self) -> str:
        """Convenience property to get the manifestation title from expression/work."""
        if self.expression and self.expression.work:
            return self.expression.work.title or "Untitled"
        return self.meta.get("title") or self.meta.get("Title") or "Untitled"

    @property
    def author(self) -> str | None:
        """Convenience property to get the primary author/artist name."""
        if self.expression and self.expression.work:
            work = self.expression.work
            authors = work.meta.get("authors", []) if work.meta else []
            if authors and isinstance(authors, list):
                val = authors[0]
                if isinstance(val, str):
                    return val
        if self.meta:
            auth = self.meta.get("author")
            if isinstance(auth, str):
                return auth
            authors_list = self.meta.get("authors", [])
            # In Python, we can't assume what's in the list, so check it's a string
            if isinstance(authors_list, list) and authors_list and isinstance(authors_list[0], str):
                return authors_list[0]
            artist = self.meta.get("Artist")
            if isinstance(artist, str):
                return artist
        return None

    def update_meta(self, **kwargs) -> None:
        """Safely merge keyword arguments into the ``meta`` JSON field."""
        meta = dict(self.meta) if self.meta else {}

        meta.update(kwargs)
        self.meta = meta

    # Relationships
    items = db.relationship("Item", backref="manifestation", lazy=True)


class Item(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Item.

    A single exemplar of a Manifestation owned by a specific user.
    E.g., the dog-eared copy on your bookshelf.
    """

    __tablename__ = "items"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id"), nullable=False)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = db.Column(db.String(50), default="available")  # see ITEM_STATUSES for valid values
    condition = db.Column(db.String(50))

    added_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    meta = db.Column(db.JSON, default=dict)
