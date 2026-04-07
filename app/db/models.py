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
"""Re-export shim for backward compatibility.

All model definitions have been split into domain-specific modules:

- :mod:`app.db.auth`     — User, Role, Permission, TokenBlocklist, ConsentRecord
- :mod:`app.db.core`     — Work, Expression, Manifestation, Item, ITEM_STATUSES
- :mod:`app.db.audio`    — Contributor, WorkContribution, ExpressionContribution,
                            WorkPart, MANIFESTATION_AUDIO_META_KEYS
- :mod:`app.db.video`    — ManifestationContribution, MANIFESTATION_VIDEO_META_KEYS
- :mod:`app.db.games`    — ContainerAggregation, MANIFESTATION_GAME_META_KEYS
- :mod:`app.db.settings` — LLMTelemetry, InstanceSettings

Existing imports of the form ``from app.db.models import Work`` continue to
work unchanged thanks to this shim.
"""

from app.db.audio import (  # noqa: F401
    EXPRESSION_CONTRIBUTION_ROLES,
    MANIFESTATION_AUDIO_META_KEYS,
    WORK_CONTRIBUTION_ROLES,
    Contributor,
    ExpressionContribution,
    WorkContribution,
    WorkPart,
)
from app.db.auth import ConsentRecord, Permission, Role, TokenBlocklist, User, role_permissions, user_roles  # noqa: F401
from app.db.core import ITEM_STATUSES, Expression, Item, Manifestation, MediaCategory, MediaFormat, Work  # noqa: F401
from app.db.games import MANIFESTATION_GAME_META_KEYS, ContainerAggregation  # noqa: F401
from app.db.puzzle import MANIFESTATION_PUZZLE_META_KEYS  # noqa: F401
from app.db.settings import InstanceSettings, LLMTelemetry  # noqa: F401

# --- New Video, Games & Puzzle Expansions ---
from app.db.video import (  # noqa: F401
    EXPRESSION_VIDEO_ROLES,
    MANIFESTATION_VIDEO_META_KEYS,
    MANIFESTATION_VIDEO_ROLES,
    WORK_VIDEO_ROLES,
    ManifestationContribution,
)

# db is imported here so that ``from app.db.models import db`` also continues to work.
from . import db  # noqa: F401
