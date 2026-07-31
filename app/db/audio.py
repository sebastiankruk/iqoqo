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
"""Audio/music-specific constants + backward-compat re-exports.

The FRBRoo event-based contribution models
(:class:`Contributor`, :class:`WorkContribution`,
:class:`ExpressionContribution`, :class:`WorkPart`) are shared across **all**
media strategies and live in :mod:`app.db.contributions`.  This module only
holds the audio-specific ``Manifestation.meta`` key conventions and
re-exports the shared entities so existing imports keep working.
"""

from __future__ import annotations

from app.db.contributions import (
    EXPRESSION_CONTRIBUTION_ROLES,
    WORK_CONTRIBUTION_ROLES,
    Contributor,
    ExpressionContribution,
    WorkContribution,
    WorkPart,
)

__all__ = [
    "EXPRESSION_CONTRIBUTION_ROLES",
    "MANIFESTATION_AUDIO_META_KEYS",
    "WORK_CONTRIBUTION_ROLES",
    "Contributor",
    "ExpressionContribution",
    "WorkContribution",
    "WorkPart",
]

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
