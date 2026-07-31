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
"""Video/film-specific constants + backward-compat re-exports.

The FRBRoo Publication Event model
(:class:`app.db.contributions.ManifestationContribution`) is shared across
**all** media strategies and lives in :mod:`app.db.contributions`.  This
module only holds the video-specific ``Manifestation.meta`` key conventions
and role vocabularies, and re-exports the shared model so existing imports
keep working.
"""

from __future__ import annotations

from app.db.contributions import (
    EXPRESSION_VIDEO_ROLES,
    MANIFESTATION_VIDEO_ROLES,
    WORK_VIDEO_ROLES,
    ManifestationContribution,
)

__all__ = [
    "EXPRESSION_VIDEO_ROLES",
    "MANIFESTATION_VIDEO_META_KEYS",
    "MANIFESTATION_VIDEO_ROLES",
    "WORK_VIDEO_ROLES",
    "ManifestationContribution",
]

MANIFESTATION_VIDEO_META_KEYS: tuple[str, ...] = (
    "resolution",
    "aspect_ratio",
    "video_format",
    "audio_formats",
    "region_code",
    "run_time_minutes",
)
