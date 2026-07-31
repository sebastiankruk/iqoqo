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
"""Shared FRBRoo event-based contribution models (catalog schema).

These entities implement the FRBRoo event layer for **all** media strategies
(text, audio, video, board game, puzzle).  They live in the ``catalog``
PostgreSQL schema alongside the core FRBR hierarchy.  In SQLite test
environments no schema is applied.

- ``Contributor``                — FRBRoo F10 Person / F11 Corporate Body
- ``WorkContribution``           — FRBRoo Composition Event   (creator → Work)
- ``ExpressionContribution``     — FRBRoo Performance Event   (performer → Expression)
- ``ManifestationContribution``  — FRBRoo Publication Event   (publisher → Manifestation)
- ``WorkPart``                   — FRBRoo F15 Complex Work    (box-set / anthology)

Historically these lived in :mod:`app.db.audio` and :mod:`app.db.video` for
convenience; both modules re-export them here for backward compatibility.  New
code should import from this module (or from :mod:`app.db.models`).
"""

from __future__ import annotations

import os

from . import db

# ---------------------------------------------------------------------------
# Schema selector — mirrors the logic in app.db.core
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")

_CATALOG: str | None = "catalog" if _USE_PG else None
_CATALOG_PFX: str = f"{_CATALOG}." if _CATALOG else ""

# ---------------------------------------------------------------------------
# Roles used in contribution tables (informational constants)
# ---------------------------------------------------------------------------

#: Valid ``role`` values for :class:`WorkContribution` (Composition Event).
#: Generic across media; media-specific extensions live in
#: :data:`WORK_VIDEO_ROLES` and the per-media ``*_META_KEYS`` modules.
WORK_CONTRIBUTION_ROLES: tuple[str, ...] = (
    "composer",
    "lyricist",
    "author",
    "playwright",
    "arranger",
)

#: Valid ``role`` values for :class:`ExpressionContribution` (Performance Event).
EXPRESSION_CONTRIBUTION_ROLES: tuple[str, ...] = (
    "performer",
    "conductor",
    "narrator",
    "band",
    "director",
    "ensemble",
)

#: Video-specific Work roles (Composition Event for film/series).
WORK_VIDEO_ROLES: tuple[str, ...] = ("director", "writer", "screenwriter", "creator")

#: Video-specific Expression roles (Performance Event for film/series).
EXPRESSION_VIDEO_ROLES: tuple[str, ...] = ("actor", "cast", "voice_actor", "host")

#: Valid ``role`` values for :class:`ManifestationContribution` (Publication Event).
MANIFESTATION_VIDEO_ROLES: tuple[str, ...] = ("studio", "distributor", "producer", "network")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Contributor(db.Model):  # type: ignore[name-defined]
    """
    FRBRoo F10 Person / F11 Corporate Body.

    A person or organization that contributes to Works and/or Expressions.
    Normalizing contributors into their own table allows cross-work queries
    (e.g., "all recordings by Miles Davis").
    """

    __tablename__ = "contributors"
    __table_args__ = (
        db.UniqueConstraint("name", "type", name="uq_contributor_name_type"),
        *(({"schema": _CATALOG},) if _CATALOG else ()),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False, index=True)
    #: 'person' | 'organization'
    type = db.Column(db.String(20), nullable=False, default="person")
    meta = db.Column(db.JSON, default=dict)

    # Relationships
    work_contributions = db.relationship("WorkContribution", backref="contributor", lazy="dynamic", cascade="all, delete-orphan")
    expression_contributions = db.relationship(
        "ExpressionContribution", backref="contributor", lazy="dynamic", cascade="all, delete-orphan"
    )


class WorkContribution(db.Model):  # type: ignore[name-defined]
    """
    FRBRoo Composition Event.

    Links a :class:`~app.db.core.Work` to a :class:`Contributor` with a
    creative role (e.g., composer, lyricist, author).

    ``sequence`` controls display order when multiple contributors share the
    same role (e.g., co-authors).
    """

    __tablename__ = "work_contributions"
    __table_args__ = (
        db.Index("ix_work_contributions_work_id", "work_id"),
        db.Index("ix_work_contributions_contributor_id", "contributor_id"),
        *(({"schema": _CATALOG},) if _CATALOG else ()),
    )

    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), nullable=False)
    contributor_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}contributors.id", ondelete="CASCADE"), nullable=False)
    #: see WORK_CONTRIBUTION_ROLES for valid values
    role = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.Integer, default=0)


class ExpressionContribution(db.Model):  # type: ignore[name-defined]
    """
    FRBRoo Performance Event.

    Links a :class:`~app.db.core.Expression` to a :class:`Contributor` with a
    performance role (e.g., performer, conductor, narrator).
    """

    __tablename__ = "expression_contributions"
    __table_args__ = (
        db.Index("ix_expression_contributions_expression_id", "expression_id"),
        db.Index("ix_expression_contributions_contributor_id", "contributor_id"),
        *(({"schema": _CATALOG},) if _CATALOG else ()),
    )

    id = db.Column(db.Integer, primary_key=True)
    expression_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}expressions.id", ondelete="CASCADE"), nullable=False)
    contributor_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}contributors.id", ondelete="CASCADE"), nullable=False)
    #: see EXPRESSION_CONTRIBUTION_ROLES for valid values
    role = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.Integer, default=0)


class ManifestationContribution(db.Model):  # type: ignore[name-defined]
    """
    FRBRoo Publication Event.

    Links a Manifestation to a Contributor with a publication role
    (e.g., studio, production company, distributor).
    """

    __tablename__ = "manifestation_contributions"
    __table_args__ = (
        db.Index("ix_manifestation_contributions_manifestation_id", "manifestation_id"),
        db.Index("ix_manifestation_contributions_contributor_id", "contributor_id"),
        *(({"schema": _CATALOG},) if _CATALOG else ()),
    )

    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="CASCADE"), nullable=False)
    contributor_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}contributors.id", ondelete="CASCADE"), nullable=False)

    #: see MANIFESTATION_VIDEO_ROLES for valid values
    role = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.Integer, default=0)

    contributor = db.relationship(
        "Contributor", backref=db.backref("manifestation_contributions", lazy="dynamic", cascade="all, delete-orphan")
    )
    manifestation = db.relationship("Manifestation", backref=db.backref("contributions", lazy="dynamic", cascade="all, delete-orphan"))


class WorkPart(db.Model):  # type: ignore[name-defined]
    """
    FRBRoo F15 Complex Work — Box-set / anthology containment.

    Represents a "has-part" relationship between two Works: a *container*
    Work (e.g., a box set) that aggregates one or more *part* Works (e.g.,
    individual albums/titles).

    ``sequence`` controls the display order of parts within the container.
    """

    __tablename__ = "work_parts"
    __table_args__ = (
        db.Index("ix_work_parts_container_work_id", "container_work_id"),
        db.Index("ix_work_parts_part_work_id", "part_work_id"),
        *(({"schema": _CATALOG},) if _CATALOG else ()),
    )

    container_work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), primary_key=True)
    part_work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), primary_key=True)
    sequence = db.Column(db.Integer, default=0)
