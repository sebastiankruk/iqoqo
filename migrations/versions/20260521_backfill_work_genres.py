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
"""backfill_work_genres

Backfill Work.meta["genres"] from genre-like data trapped in Manifestation.meta
(e.g. "Categories" from Google Books / Open Library lookups).

Revision ID: 20260521_backfill_work_genres
Revises: 49dedc457aa3, 1b7b2d612e23
Create Date: 2026-05-21

"""
import json
import logging

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision = "20260521_backfill_work_genres"
down_revision = ("49dedc457aa3", "1b7b2d612e23")
branch_labels = None
depends_on = None


def _extract_genres_from_meta(meta: dict) -> list[str]:
    """Extract genre strings from a Manifestation.meta dict.

    Handles the same keys as the :func:`_extract_genres` helper in
    ``app/core/ingest.py`` so that the backfill is consistent with the
    ingest-time logic.
    """
    genres: list[str] = []
    for key in ("Categories", "genres", "genre", "Genre"):
        raw = meta.get(key)
        if isinstance(raw, list):
            for v in raw:
                if isinstance(v, str) and v.strip():
                    genres.append(v.strip())
        elif isinstance(raw, str) and raw.strip():
            genres.append(raw.strip())
    return genres


def upgrade():
    bind = op.get_bind()
    meta = sa.MetaData()

    works_table = sa.Table(
        "works", meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("meta", sa.JSON),
        schema="catalog",
    )
    expressions_table = sa.Table(
        "expressions", meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("work_id", sa.Integer),
        schema="catalog",
    )
    manifestations_table = sa.Table(
        "manifestations", meta,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("expression_id", sa.Integer),
        sa.Column("meta", sa.JSON),
        schema="catalog",
    )

    # Fetch all manifestations that have a non-null meta.
    rows = bind.execute(
        sa.select(
            manifestations_table.c.id,
            manifestations_table.c.expression_id,
            manifestations_table.c.meta,
        ).where(
            manifestations_table.c.meta.isnot(None)
        )
    ).all()

    updated_count = 0
    skipped_no_expression = 0
    skipped_no_work = 0
    skipped_already_has_genres = 0
    skipped_no_genre_data = 0

    for _manif_id, expression_id, raw_meta in rows:
        if not raw_meta:
            skipped_no_genre_data += 1
            continue

        if isinstance(raw_meta, str):
            try:
                man_meta = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                man_meta = {}
        else:
            man_meta = raw_meta

        if not isinstance(man_meta, dict):
            skipped_no_genre_data += 1
            continue

        genres = _extract_genres_from_meta(man_meta)
        if not genres:
            skipped_no_genre_data += 1
            continue

        # Resolve the Work via Expression.
        if not expression_id:
            skipped_no_expression += 1
            continue

        expr_row = bind.execute(
            sa.select(expressions_table.c.work_id).where(
                expressions_table.c.id == expression_id
            )
        ).first()
        if not expr_row or not expr_row[0]:
            skipped_no_work += 1
            continue

        work_id = expr_row[0]

        # Read current Work.meta
        work_row = bind.execute(
            sa.select(works_table.c.meta).where(
                works_table.c.id == work_id
            )
        ).first()
        if not work_row:
            skipped_no_work += 1
            continue

        raw_work_meta = work_row[0]
        if isinstance(raw_work_meta, str):
            try:
                work_meta = json.loads(raw_work_meta)
            except (json.JSONDecodeError, TypeError):
                work_meta = {}
        else:
            work_meta = raw_work_meta if raw_work_meta else {}

        if not isinstance(work_meta, dict):
            work_meta = {}

        # Skip if Work.meta already has genres (don't overwrite).
        existing = work_meta.get("genres") or work_meta.get("genre")
        if existing:
            skipped_already_has_genres += 1
            continue

        work_meta["genres"] = genres
        new_meta = json.dumps(work_meta) if isinstance(raw_work_meta, str) else work_meta

        bind.execute(
            sa.update(works_table)
            .where(works_table.c.id == work_id)
            .values(meta=new_meta)
        )
        updated_count += 1

    logger.info(
        "backfill_work_genres: updated=%d skipped(no_expression=%d no_work=%d already_has=%d no_genre_data=%d)",
        updated_count,
        skipped_no_expression,
        skipped_no_work,
        skipped_already_has_genres,
        skipped_no_genre_data,
    )


def downgrade():
    # Data migration — not reversible without a full backup.
    pass
