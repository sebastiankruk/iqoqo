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
"""Dialect-aware genre filter helper for faceted navigation."""

from sqlalchemy.dialects.postgresql import JSONB

from app.db import db
from app.db.models import Work


def parse_csv_param(value: str | None) -> list[str] | None:
    """Parse comma-separated string parameter into a list of non-empty stripped strings.

    Parameters
    ----------
    value:
        Optional comma-separated string parameter.

    Returns
    -------
    list[str] | None
        List of non-empty stripped string tokens, or None if input is empty/None/whitespace only.
    """
    if not value:
        return None
    tokens = [t.strip() for t in value.split(",") if t.strip()]
    return tokens if tokens else None


def apply_genre_filter(query, genres_list):
    """Apply genre filter on Work.meta, handling scalar ``genre`` and array ``genres`` case-insensitively.

    The ``Work.meta`` column is typed as PostgreSQL ``json`` (not ``jsonb``).
    We explicitly cast to ``jsonb`` so that SQLAlchemy's ``.contains()``
    emits the ``@>`` containment operator instead of a broken ``LIKE`` on
    raw JSON.  This also allows the GIN index
    ``idx_work_meta_genres_gin`` (on ``meta::jsonb->'genres'``) to be
    used for ``@>`` queries.
    """
    is_postgres = db.engine.dialect.name == "postgresql"

    conditions = []
    for gen in genres_list:
        g_clean = gen.strip()
        if is_postgres:
            # Cast meta to jsonb so .contains() emits the @> containment operator
            meta_jsonb = Work.meta.cast(JSONB)
            conditions.append(meta_jsonb.contains({"genre": g_clean}))
            conditions.append(meta_jsonb["genres"].contains([g_clean]))
        else:
            # SQLite fallback path
            conditions.append(Work.meta["genre"].as_string().ilike(f"%{g_clean}%"))
            conditions.append(Work.meta["genres"].as_string().ilike(f"%{g_clean}%"))
    query = query.filter(db.or_(*conditions))
    return query


def apply_statuses_filter(query, statuses_list, user_id=None, borrowed_only=False):
    """
    Apply statuses filter handling both Process (Item.status) and Collection (Item.collection_status) filters.
    When both types are provided, applies them conjunctively (AND).
    """
    if not statuses_list:
        return query

    from app.core.taxonomy import COLLECTION_STATUSES, PROGRESS_STATUSES
    from app.db.models import Item

    process_statuses = [s for s in statuses_list if s in PROGRESS_STATUSES]
    collection_statuses = [s for s in statuses_list if s in COLLECTION_STATUSES]
    unknown_statuses = [s for s in statuses_list if s not in PROGRESS_STATUSES and s not in COLLECTION_STATUSES]

    if unknown_statuses:
        process_statuses.extend(unknown_statuses)

    conditions = []
    if process_statuses:
        conditions.append(Item.status.in_(process_statuses))

    if collection_statuses:
        if "lent" in collection_statuses and not borrowed_only and user_id is not None:
            other_statuses = [s for s in collection_statuses if s != "lent"]
            if other_statuses:
                conditions.append(
                    db.or_(
                        db.and_(Item.collection_status == "lent", Item.owner_id == user_id),
                        Item.collection_status.in_(other_statuses),
                    )
                )
            else:
                conditions.append(db.and_(Item.collection_status == "lent", Item.owner_id == user_id))
        else:
            conditions.append(Item.collection_status.in_(collection_statuses))

    if conditions:
        return query.filter(db.and_(*conditions))
    return query
