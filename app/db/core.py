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
"""This module contains the core bibliographic models based on the FRBR ontology:
- :class:`Work` (catalog schema)
- :class:`Expression` (catalog schema)
- :class:`Manifestation` (catalog schema)
- :class:`Item` (inventory schema)

The hierarchy follows the Work -> Expression -> Manifestation -> Item structure.
Note that while most bibliographic data resides in the ``catalog`` schema,
individual ``Item`` records reside in the ``inventory`` schema and reference
user ownership in the ``auth`` schema.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import UUID

from app.core.taxonomy import (  # noqa: F401
    CATEGORY_PROGRESS_STATUSES,
    COLLECTION_STATUSES,
    PROGRESS_STATUSES,
    MediaCategory,
    MediaFormat,
)
from app.db.search_types import SearchVector

from . import db

_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")

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


#: Unified list of all possible item statuses.
ITEM_STATUSES: tuple[str, ...] = COLLECTION_STATUSES + PROGRESS_STATUSES

#: Controlled vocabulary for :attr:`Expression.kind`.
#:
#: ``live_performance`` — a concert / gig / live-recorded realization of a Work,
#: linked to a Performance Event via :class:`ExpressionContribution` rows that
#: capture performers, venue, and date.  Concerts must be typed here, never as
#: genre tags or item-level flags.
#:
#: ``None`` (NULL) is the default and means a studio / ordinary realization.
#: Additional kinds (``remix``, ``directors_cut``, …) may be added in future
#: releases without a schema migration — the vocabulary is enforced at the
#: service layer, not by a database CHECK constraint.
EXPRESSION_KINDS: tuple[str, ...] = ("live_performance",)
EXPRESSION_KIND_LIVE_PERFORMANCE: str = "live_performance"

#: Controlled vocabulary for :attr:`WorkExpansionLink.link_type`.
WORK_LINK_TYPES: tuple[str, ...] = ("is_expansion_of",)
WORK_LINK_TYPE_IS_EXPANSION_OF: str = "is_expansion_of"


class Work(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Work.

    A distinct intellectual or artistic creation.
    E.g., "The Hobbit" (the story itself, language-agnostic).
    """

    __tablename__ = "works"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(1000), nullable=False)
    #: Sort key derived from ``title`` with leading articles stripped
    #: ("The", "A", "An", and Polish "Ten"/"Ta"/"To").  Populated by the
    #: service layer; used for alphabetical ordering in catalog views.
    sort_title = db.Column(db.String(1000), nullable=True, index=True)
    meta = db.Column(db.JSON, default=dict)
    #: Verbatim external-provider payload (BGG/Discogs/TMDB/MusicBrainz/Allegro)
    #: captured at ingestion time.  Read-only audit trail for provenance and
    #: future re-scraping — never edited by the service layer.
    raw_payload = db.Column(db.JSON, nullable=True)

    # Dialect-aware full-text search columns using SearchVector type.
    # Computed columns are only generated on dialects that support them (PostgreSQL).
    fts_simple = db.Column(
        SearchVector(),
        (
            db.Computed(
                "to_tsvector('simple'::regconfig, (((COALESCE(title, ''::character varying))::text"
                " || ' '::text) || COALESCE((meta ->> 'authors'::text), ''::text)))",
                persisted=True,
            )
            if _USE_PG
            else db.FetchedValue()
        ),
        nullable=True,
    )
    search_vector = db.Column(
        SearchVector(),
        db.FetchedValue(),
        nullable=True,
    )

    __table_args__: tuple = (
        db.Index("ix_works_fts", fts_simple, postgresql_using="gin"),
        db.Index("ix_works_search_vector", search_vector, postgresql_using="gin"),
        {"schema": _CATALOG},
    )

    # Relationships
    expressions = db.relationship("Expression", backref="work", lazy=True, cascade="all, delete-orphan")
    contributions = db.relationship("WorkContribution", backref="work", lazy="selectin", cascade="all, delete-orphan")
    feedbacks = db.relationship(
        "SocialFeedback", foreign_keys="SocialFeedback.work_id", backref="work", lazy="dynamic", cascade="all, delete-orphan"
    )
    notes = db.relationship("SocialNote", foreign_keys="SocialNote.work_id", backref="work", lazy="dynamic", cascade="all, delete-orphan")
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
    expansions = db.relationship(
        "WorkExpansionLink",
        foreign_keys="WorkExpansionLink.base_work_id",
        back_populates="base_work",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    base_game = db.relationship(
        "WorkExpansionLink",
        foreign_keys="WorkExpansionLink.expansion_work_id",
        back_populates="expansion_work",
        uselist=False,
    )


class WorkExpansionLink(db.Model):  # type: ignore[name-defined]
    """
    Reified association linking a base board game Work to an expansion Work.

    Mirrors the iqoqo ontology: ``iqoqo:is_expansion_of`` /
    ``iqoqo:has_expansion``.
    """

    __tablename__ = "work_expansion_links"
    __table_args__ = (
        db.Index("ix_work_expansion_links_base_work_id", "base_work_id"),
        db.Index("ix_work_expansion_links_expansion_work_id", "expansion_work_id"),
        {"schema": _CATALOG},
    )

    id = db.Column(db.Integer, primary_key=True)
    base_work_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"),
        nullable=False,
    )
    expansion_work_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    link_type = db.Column(
        db.String(50),
        nullable=False,
        default=WORK_LINK_TYPE_IS_EXPANSION_OF,
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    base_work = db.relationship(
        "Work",
        foreign_keys=[base_work_id],
        back_populates="expansions",
    )
    expansion_work = db.relationship(
        "Work",
        foreign_keys=[expansion_work_id],
        back_populates="base_game",
    )


class BoardgameMechanic(db.Model):  # type: ignore[name-defined]
    """
    Controlled vocabulary for board game mechanics sourced from BoardGameGeek.
    """

    __tablename__ = "boardgame_mechanics"
    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()

    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    bgg_id = db.Column(db.String(50), nullable=True, index=True)
    last_updated = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
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
    work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), nullable=False)
    content_type = db.Column(db.String(50))  # e.g., 'text', 'sound', 'notated_music', 'video'
    language = db.Column(db.String(10))  # BCP-47 language tag, e.g., 'en', 'pl'
    #: FRBRoo expression kind (controlled vocabulary, see
    #: :data:`app.db.core.EXPRESSION_KINDS`).  Initial value: ``live_performance``
    #: for concert recordings.  ``None`` = studio/default realization.
    kind = db.Column(db.String(50), nullable=True, index=True)
    meta = db.Column(db.JSON, default=dict)
    #: Verbatim external-provider payload captured at ingestion time.
    raw_payload = db.Column(db.JSON, nullable=True)

    # Relationships
    manifestations = db.relationship("Manifestation", backref="expression", lazy=True, cascade="all, delete-orphan")
    contributions = db.relationship("ExpressionContribution", backref="expression", lazy="selectin", cascade="all, delete-orphan")
    feedbacks = db.relationship(
        "SocialFeedback", foreign_keys="SocialFeedback.expression_id", backref="expression", lazy="dynamic", cascade="all, delete-orphan"
    )
    notes = db.relationship(
        "SocialNote", foreign_keys="SocialNote.expression_id", backref="expression", lazy="dynamic", cascade="all, delete-orphan"
    )


class Manifestation(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Manifestation.

    The physical or digital embodiment of an Expression.
    E.g., the 1937 Allen & Unwin hardcover; a specific CD pressing.
    """

    __tablename__ = "manifestations"

    id = db.Column(db.Integer, primary_key=True)
    expression_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}expressions.id", ondelete="CASCADE"), nullable=False)

    # Identifiers — at least one is expected for cover/lookup purposes
    isbn13 = db.Column(db.String(13), index=True, unique=True)
    upc = db.Column(db.String(12), index=True)
    ean = db.Column(db.String(13), index=True)

    # Promoted core relational columns
    publisher = db.Column(db.String(500))
    publication_date = db.Column(db.Date)
    cover_url = db.Column(db.String(255), nullable=True)
    format = db.Column(db.String(50), nullable=True, index=True)
    label = db.Column(db.String(500), nullable=True)
    barcode = db.Column(db.String(100), nullable=True, index=True)
    catalog_number = db.Column(db.String(100), nullable=True)
    meta = db.Column(db.JSON, default=dict)
    #: Verbatim external-provider payload captured at ingestion time.
    raw_payload = db.Column(db.JSON, nullable=True)

    # Dialect-aware full-text search column.
    fts_simple = db.Column(
        SearchVector(),
        (
            db.Computed(
                "to_tsvector('simple'::regconfig, (((((COALESCE(isbn13, ''::character varying))::text"
                " || ' '::text) || COALESCE((meta ->> 'publisher'::text), ''::text))"
                " || ' '::text) || COALESCE((meta ->> 'alt_title'::text), ''::text)))",
                persisted=True,
            )
            if _USE_PG
            else db.FetchedValue()
        ),
        nullable=True,
    )

    __table_args__: tuple = (
        db.Index("ix_manifestations_fts", fts_simple, postgresql_using="gin"),
        {"schema": _CATALOG},
    )

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

    @property
    def resolved_identifier(self) -> str:
        """Get the primary/fallback identifier for cover and lookup operations."""
        meta = self.meta or {}
        return (
            self.isbn13
            or self.ean
            or self.upc
            or meta.get("barcode")
            or meta.get("isbn")
            or meta.get("identifier")
            or meta.get("discogs_id")
            or str(self.id)
        )

    def update_meta(self, **kwargs) -> None:
        """Safely merge keyword arguments into the ``meta`` JSON field."""
        meta = dict(self.meta) if self.meta else {}

        if "cover_status" in kwargs and "cover_status_updated_at" not in kwargs:
            kwargs["cover_status_updated_at"] = datetime.now(UTC).isoformat()

        meta.update(kwargs)
        self.meta = meta

    # Relationships
    items = db.relationship("Item", backref="manifestation", lazy=True, cascade="all, delete-orphan")
    feedbacks = db.relationship(
        "SocialFeedback",
        foreign_keys="SocialFeedback.manifestation_id",
        backref="manifestation",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    notes = db.relationship(
        "SocialNote",
        foreign_keys="SocialNote.manifestation_id",
        backref="manifestation",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class Item(db.Model):  # type: ignore[name-defined]
    """
    FRBR Group 1: Item.

    A single exemplar of a Manifestation owned by a specific user.
    E.g., the dog-eared copy on your bookshelf.
    """

    __tablename__ = "items"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="CASCADE"), nullable=False)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = db.Column(db.String(50), default="want_to_read")  # see PROGRESS_STATUSES for valid values
    collection_status = db.Column(db.String(50), default="available")  # see COLLECTION_STATUSES
    condition = db.Column(db.String(50))

    lent_to_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lent_to_name = db.Column(db.String(255), nullable=True)

    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    meta = db.Column(db.JSON, default=dict)
    #: Verbatim external-provider payload captured at ingestion time.
    raw_payload = db.Column(db.JSON, nullable=True)
    feedbacks = db.relationship(
        "SocialFeedback", foreign_keys="SocialFeedback.item_id", backref="item", lazy="dynamic", cascade="all, delete-orphan"
    )
    notes = db.relationship("SocialNote", foreign_keys="SocialNote.item_id", backref="item", lazy="dynamic", cascade="all, delete-orphan")


class UserWorkIntent(db.Model):  # type: ignore[name-defined]
    """
    User intent toward a Conceptual Work (F1).
    E.g., "want_to_read" or other progress intent.
    """

    __tablename__ = "user_work_intents"
    __table_args__: tuple = (
        (
            db.UniqueConstraint("user_id", "work_id", name="uq_user_work_intent"),
            {"schema": _INVENTORY},
        )
        if _INVENTORY
        else (db.UniqueConstraint("user_id", "work_id", name="uq_user_work_intent"),)
    )

    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = db.Column(db.String(50), default="want_to_read", nullable=False)
    # Mirrors Item.is_hidden: lets a user share their wishlist (e.g. as gift ideas
    # for friends/family) with other authenticated users by default, while still
    # allowing individual entries to be opted out of that sharing.
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    work = db.relationship("Work", backref=db.backref("intents", cascade="all, delete-orphan", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("work_intents", cascade="all, delete-orphan", lazy="dynamic"))


class ItemStatusLog(db.Model):  # type: ignore[name-defined]
    """Timeline of status changes for a specific item."""

    __tablename__ = "item_status_logs"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False)
    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50), nullable=False)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    item = db.relationship("Item", backref=db.backref("status_logs", cascade="all, delete", lazy="dynamic"))
    user = db.relationship("User", backref="status_logs")


class ImageScan(db.Model):  # type: ignore[name-defined]
    """Multiple gallery images per manifestation."""

    __tablename__ = "image_scans"
    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()

    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="CASCADE"), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    scan_type = db.Column(db.String(50), default="front")  # front, back, inlay, disc, other
    source = db.Column(db.String(100))  # e.g., user_upload, tmdb, gemini_llm

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    manifestation = db.relationship("Manifestation", backref=db.backref("image_scans", cascade="all, delete", lazy="selectin"))


class UserCollection(db.Model):  # type: ignore[name-defined]
    """
    A user-defined hierarchical collection of items or other collections.
    """

    __tablename__ = "user_collections"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}user_collections.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    owner = db.relationship("User", backref=db.backref("collections", cascade="all, delete-orphan", lazy="dynamic"))
    children = db.relationship(
        "UserCollection", backref=db.backref("parent", remote_side=[id]), cascade="all, delete-orphan", lazy="selectin"
    )
    items = db.relationship("UserCollectionItem", backref="collection", cascade="all, delete-orphan", lazy="dynamic")


class UserCollectionItem(db.Model):  # type: ignore[name-defined]
    """
    Association table linking Items to UserCollections.
    """

    __tablename__ = "user_collection_items"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(
        db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}user_collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    item = db.relationship("Item", backref=db.backref("collection_links", cascade="all, delete-orphan", lazy="selectin"))


class Tag(db.Model):  # type: ignore[name-defined]
    """
    Global folksonomy tags.
    """

    __tablename__ = "tags"
    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    item_links = db.relationship("ItemTag", backref="tag", cascade="all, delete-orphan", lazy="dynamic")


class ItemTag(db.Model):  # type: ignore[name-defined]
    """
    Association table linking Items to Tags, including the user who added it.
    """

    __tablename__ = "item_tags"
    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}tags.id", ondelete="CASCADE"), nullable=False, index=True)
    added_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="SET NULL"), nullable=True)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    item = db.relationship("Item", backref=db.backref("tag_links", cascade="all, delete-orphan", lazy="selectin"))
    added_by = db.relationship("User")


class ItemCustodyEvent(db.Model):  # type: ignore[name-defined]
    """
    CIDOC CRM-compliant immutable event log for item custody changes.

    Records every custody transfer or acquisition event for a physical or
    digital FRBR Item. This log is append-only — events must never be
    modified or deleted, in order to preserve a tamper-proof provenance
    chain suitable for future ActivityPub federation trust.

    Custody applies exclusively at the FRBR Item tier.  Do not use this
    table to record edits to Work, Expression, or Manifestation records;
    use :class:`EntityAuditLog` for those tiers instead.
    """

    __tablename__ = "item_custody_events"
    __table_args__ = (
        (
            db.Index("ix_item_custody_events_item_id", "item_id"),
            db.Index("ix_item_custody_events_recorded_at", "recorded_at"),
            {"schema": _INVENTORY},
        )
        if _INVENTORY
        else (
            db.Index("ix_item_custody_events_item_id", "item_id"),
            db.Index("ix_item_custody_events_recorded_at", "recorded_at"),
        )
    )

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type = db.Column(db.String(100), nullable=False)
    """
    CIDOC CRM event type label, e.g. ``"acquisition"``, ``"transfer"``,
    ``"loss"``, ``"found"``, ``"condition_update"``.
    """
    notes = db.Column(db.Text, nullable=True)
    """Optional free-text provenance notes for this custody event."""
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    item = db.relationship(
        "Item",
        backref=db.backref("custody_events", cascade="all, delete", lazy="dynamic"),
    )
    actor = db.relationship("User", backref="custody_events_as_actor")


class EntityAuditLog(db.Model):  # type: ignore[name-defined]
    """
    Curation and edit history log for Work, Expression, and Manifestation tiers.

    Records metadata edits, duplicate resolutions, and record merges performed
    by administrators or custodians at the three abstract FRBR tiers.  This is
    separate from :class:`ItemCustodyEvent` because curation and possession are
    fundamentally different concepts in the FRBR / CIDOC CRM ontology.

    :attr entity_type: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
    :attr entity_id: The primary key of the affected entity.
    :attr change_type: A label such as ``"metadata_edit"``, ``"merge"``,
        ``"duplicate_resolved"``, or ``"field_update"``.
    :attr diff: Optional JSON snapshot of the before/after field values.
    """

    __tablename__ = "entity_audit_logs"
    __table_args__ = (
        (
            db.Index("ix_entity_audit_logs_entity", "entity_type", "entity_id"),
            db.Index("ix_entity_audit_logs_logged_at", "logged_at"),
            {"schema": _INVENTORY},
        )
        if _INVENTORY
        else (
            db.Index("ix_entity_audit_logs_entity", "entity_type", "entity_id"),
            db.Index("ix_entity_audit_logs_logged_at", "logged_at"),
        )
    )

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    actor_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(f"{_AUTH_PFX}users.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_type = db.Column(db.String(100), nullable=False)
    diff = db.Column(db.JSON, nullable=True)
    """Optional JSON capturing before/after field values for the edit."""
    logged_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    actor = db.relationship("User", backref="entity_audit_logs_as_actor")


class MetadataRefetchLog(db.Model):  # type: ignore[name-defined]
    """
    Log of metadata refetch attempts by strategy.
    Prevents redundant API calls for entities that have already been checked.
    """

    __tablename__ = "metadata_refetch_log"
    __table_args__: tuple = (
        (
            db.UniqueConstraint("entity_type", "entity_id", "strategy", name="uq_metadata_refetch_log"),
            {"schema": _INVENTORY},
        )
        if _INVENTORY
        else (db.UniqueConstraint("entity_type", "entity_id", "strategy", name="uq_metadata_refetch_log"),)
    )

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    strategy = db.Column(db.String(100), nullable=False)
    checked_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    iqoqo_version = db.Column(db.String(50), nullable=False)
    found_fields = db.Column(db.JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
