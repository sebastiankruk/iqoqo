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
"""Shared service helpers for managing FRBR wishlist intents (UserWorkIntent)."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.taxonomy import CATEGORY_PROGRESS_STATUSES, FORMAT_ALIAS_TO_CATEGORY, MediaCategory
from app.db.models import Manifestation, UserWorkIntent, db


def upsert_wishlist_intent_for_manifestation(
    user_id: uuid.UUID,
    manifestation: Manifestation,
    *,
    status: str | None = None,
    is_hidden: bool = False,
) -> UserWorkIntent | None:
    """Create or update a UserWorkIntent bound to a manifestation and its FRBR ancestors."""
    work = manifestation.expression.work if manifestation.expression and manifestation.expression.work else None
    work_id = getattr(work, "id", None) if work is not None else None
    if not isinstance(work_id, int):
        return None

    expr_id_raw = getattr(manifestation, "expression_id", None)
    expr_id = expr_id_raw if isinstance(expr_id_raw, int) else None
    manif_id_raw = getattr(manifestation, "id", None)
    manif_id = manif_id_raw if isinstance(manif_id_raw, int) else None

    raw_content_type = manifestation.expression.content_type if manifestation.expression else "text"
    fmt_lower = raw_content_type.lower() if isinstance(raw_content_type, str) else "text"
    category = fmt_lower if fmt_lower in MediaCategory.ALL else FORMAT_ALIAS_TO_CATEGORY.get(fmt_lower, MediaCategory.TEXT)
    statuses = CATEGORY_PROGRESS_STATUSES.get(category, ("want_to_read",))
    default_progress = status or next((s for s in statuses if s.startswith("want_to_")), statuses[0])

    intent = (
        db.session.execute(
            select(UserWorkIntent).where(
                UserWorkIntent.user_id == user_id,
                UserWorkIntent.work_id == work_id,
            )
        )
        .scalars()
        .first()
    )
    if not intent:
        intent = UserWorkIntent(
            user_id=user_id,
            work_id=work_id,
            expression_id=expr_id,
            manifestation_id=manif_id,
            status=default_progress,
            is_hidden=is_hidden,
        )
        db.session.add(intent)
        db.session.flush()
    else:
        if intent.expression_id is None and expr_id is not None:
            intent.expression_id = expr_id
        if intent.manifestation_id is None and manif_id is not None:
            intent.manifestation_id = manif_id

    return intent


def fulfill_wishlist_intent_for_manifestation(
    user_id: uuid.UUID | None,
    manifestation: Manifestation | None,
) -> int:
    """Delete any matching UserWorkIntent when a user acquires a physical item for its Work."""
    if not user_id or not manifestation:
        return 0
    expr = manifestation.expression
    work = expr.work if expr else None
    work_id = getattr(work, "id", None) if work is not None else None
    if not isinstance(work_id, int):
        return 0

    intents = (
        db.session.execute(
            select(UserWorkIntent).where(
                UserWorkIntent.user_id == user_id,
                UserWorkIntent.work_id == work_id,
            )
        )
        .scalars()
        .all()
    )
    for intent in intents:
        db.session.delete(intent)
    return len(intents)
