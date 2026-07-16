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
