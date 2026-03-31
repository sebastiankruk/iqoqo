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
"""Audio/music event-based models (catalog schema).

Implements FRBRoo event-based modeling for audio media:

- ``Contributor``          — FRBRoo F10 Person / F11 Corporate Body
- ``WorkContribution``     — FRBRoo Composition Event (who created the Work)
- ``ExpressionContribution`` — FRBRoo Performance Event (who performed the Expression)
- ``WorkPart``             — FRBRoo F15 Complex Work (box-set / anthology containment)

All tables live in the ``catalog`` PostgreSQL schema alongside the core FRBR
hierarchy tables.  In SQLite test environments, no schema is applied.

Audio-specific ``Manifestation.meta`` keys are documented in
:data:`MANIFESTATION_AUDIO_META_KEYS`.
"""

from __future__ import annotations

import os
import sys

from . import db

# ---------------------------------------------------------------------------
# Schema selector — mirrors the logic in app.db.core
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql") and (
    "pytest" not in sys.modules or os.environ.get("ENABLE_FTS_TESTS") == "true"
)
_CATALOG: str | None = "catalog" if _USE_PG else None
_CATALOG_PFX: str = f"{_CATALOG}." if _CATALOG else ""

# ---------------------------------------------------------------------------
# Documented JSONB keys for audio manifestations
# ---------------------------------------------------------------------------

#: Keys that MAY be stored inside ``Manifestation.meta`` for audio releases.
#: These are *not* enforced by the database schema — they are conventions that
#: must be respected by any code reading or writing audio manifestation metadata.
#:
#: ``catalog_number``  — Record-label catalog number (e.g. "ECM 1064").
#: ``pressing_number`` — Specific pressing identifier.
#: ``matrix_number``   — Vinyl run-out groove inscription / lacquer ID.
#: ``label``           — Record label name (e.g. "Blue Note", "ECM").
#: ``format``          — Physical format: 'LP', '45', 'EP', 'CD', 'CD-EP', etc.
#: ``disc_count``      — Number of discs in a multi-disc release (int).
#: ``track_list``      — Ordered list of track dicts: ``[{"position": "A1",
#:                        "title": "...", "duration_seconds": 210}, ...]``.
MANIFESTATION_AUDIO_META_KEYS: tuple[str, ...] = (
    "catalog_number",
    "pressing_number",
    "matrix_number",
    "label",
    "format",
    "disc_count",
    "track_list",
)

# ---------------------------------------------------------------------------
# Roles used in contribution tables (informational constants)
# ---------------------------------------------------------------------------

#: Valid ``role`` values for :class:`WorkContribution` (Composition Event).
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
    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()  # type: ignore[assignment]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False, index=True)
    #: 'person' | 'organization'
    type = db.Column(db.String(20), nullable=False, default="person")
    meta = db.Column(db.JSON, default={})

    # Relationships
    work_contributions = db.relationship("WorkContribution", backref="contributor", lazy="dynamic")
    expression_contributions = db.relationship("ExpressionContribution", backref="contributor", lazy="dynamic")


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
