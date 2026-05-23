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

from app.db import db
from app.db.models import Work


def apply_genre_filter(query, genres_list):
    """Apply genre filter on Work.meta, handling scalar ``genre`` and array ``genres`` case-insensitively."""
    conditions = []
    for gen in genres_list:
        conditions.append(Work.meta["genre"].as_string().ilike(f"%{gen}%"))
        conditions.append(Work.meta["genres"].as_string().ilike(f"%{gen}%"))
    query = query.filter(db.or_(*conditions))
    return query
