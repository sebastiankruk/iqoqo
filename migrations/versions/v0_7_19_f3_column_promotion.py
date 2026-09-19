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
"""Promote FRBR F3 Manifestation physical attributes to typed columns.

Revision ID: v0_7_19_f3_column_promotion
Revises: v0_7_18_fixes
Create Date: 2026-09-17
"""

import json
from typing import Any
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_7_19_f3_column_promotion"
down_revision = "v0_7_18_fixes"
branch_labels = None
depends_on = None

BATCH_SIZE = 500


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    s_cat = "catalog" if is_pg else None

    # 1. Add format_type column if not exists
    manif_cols = {c["name"]: c for c in inspector.get_columns("manifestations", schema=s_cat)}

    with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
        if "format_type" not in manif_cols:
            batch_op.add_column(sa.Column("format_type", sa.String(length=50), nullable=True))
        if "publisher" in manif_cols:
            batch_op.alter_column(
                "publisher",
                type_=sa.String(length=255),
                existing_type=sa.String(length=500),
                existing_nullable=True,
            )

    # 2. Add index on format_type if not exists
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=s_cat)}
    idx_format_name = "ix_catalog_manifestations_format_type" if is_pg else "ix_manifestations_format_type"
    if idx_format_name not in existing_indexes:
        with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
            batch_op.create_index(idx_format_name, ["format_type"], unique=False)

    # 3. Batch backfill from meta and prune promoted keys
    manifestations_tbl = sa.Table(
        "manifestations",
        sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("isbn13", sa.String(length=13), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("format_type", sa.String(length=50), nullable=True),
        sa.Column("format", sa.String(length=50), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        schema=s_cat,
    )

    last_id = 0
    promoted_keys = ("isbn13", "isbn", "publisher", "Publisher", "format_type")

    while True:
        select_stmt = (
            sa.select(
                manifestations_tbl.c.id,
                manifestations_tbl.c.isbn13,
                manifestations_tbl.c.publisher,
                manifestations_tbl.c.format_type,
                manifestations_tbl.c.format,
                manifestations_tbl.c.meta,
            )
            .where(manifestations_tbl.c.id > last_id)
            .order_by(manifestations_tbl.c.id.asc())
            .limit(BATCH_SIZE)
        )

        results = bind.execute(select_stmt).fetchall()
        if not results:
            break

        for row in results:
            m_id = row[0]
            curr_isbn = row[1]
            curr_pub = row[2]
            curr_fmt_type = row[3]
            curr_fmt = row[4]
            raw_meta = row[5]

            last_id = m_id

            if raw_meta is None:
                continue

            if isinstance(raw_meta, str):
                try:
                    meta_dict: dict[str, Any] = json.loads(raw_meta)
                except (json.JSONDecodeError, TypeError):
                    continue
            elif isinstance(raw_meta, dict):
                meta_dict = dict(raw_meta)
            else:
                continue

            meta_changed = False
            new_isbn = curr_isbn
            new_pub = curr_pub
            new_fmt_type = curr_fmt_type

            # Backfill isbn13 if missing
            if not new_isbn:
                cand_isbn = meta_dict.get("isbn13") or meta_dict.get("isbn")
                if cand_isbn and isinstance(cand_isbn, str):
                    clean_isbn = cand_isbn.replace("-", "").replace(" ", "").strip()
                    if len(clean_isbn) == 13:
                        new_isbn = clean_isbn

            # Backfill publisher if missing
            if not new_pub:
                cand_pub = meta_dict.get("publisher") or meta_dict.get("Publisher")
                if cand_pub and isinstance(cand_pub, str):
                    clean_pub = cand_pub.strip()[:255]
                    if clean_pub:
                        new_pub = clean_pub

            # Backfill format_type if missing
            if not new_fmt_type:
                cand_fmt = meta_dict.get("format_type") or curr_fmt or meta_dict.get("format") or meta_dict.get("video_format")
                if cand_fmt and isinstance(cand_fmt, str):
                    clean_fmt = cand_fmt.strip().lower()[:50]
                    if clean_fmt:
                        new_fmt_type = clean_fmt

            # Prune promoted keys from meta
            for k in promoted_keys:
                if k in meta_dict:
                    del meta_dict[k]
                    meta_changed = True

            cols_to_update: dict[str, Any] = {}
            if new_isbn != curr_isbn:
                cols_to_update["isbn13"] = new_isbn
            if new_pub != curr_pub:
                cols_to_update["publisher"] = new_pub
            if new_fmt_type != curr_fmt_type:
                cols_to_update["format_type"] = new_fmt_type
            if meta_changed:
                cols_to_update["meta"] = meta_dict

            if cols_to_update:
                update_stmt = (
                    manifestations_tbl.update()
                    .where(manifestations_tbl.c.id == m_id)
                    .values(**cols_to_update)
                )
                bind.execute(update_stmt)


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    s_cat = "catalog" if is_pg else None

    # 1. Backfill format_type back to meta before dropping column
    manifestations_tbl = sa.Table(
        "manifestations",
        sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("format_type", sa.String(length=50), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        schema=s_cat,
    )

    last_id = 0
    while True:
        select_stmt = (
            sa.select(
                manifestations_tbl.c.id,
                manifestations_tbl.c.format_type,
                manifestations_tbl.c.meta,
            )
            .where(manifestations_tbl.c.id > last_id)
            .where(manifestations_tbl.c.format_type.is_not(None))
            .order_by(manifestations_tbl.c.id.asc())
            .limit(BATCH_SIZE)
        )
        results = bind.execute(select_stmt).fetchall()
        if not results:
            break

        for row in results:
            m_id = row[0]
            fmt_type = row[1]
            raw_meta = row[2]
            last_id = m_id

            if isinstance(raw_meta, str):
                try:
                    meta_dict = json.loads(raw_meta)
                except (json.JSONDecodeError, TypeError):
                    meta_dict = {}
            elif isinstance(raw_meta, dict):
                meta_dict = dict(raw_meta)
            else:
                meta_dict = {}

            if fmt_type:
                meta_dict["format_type"] = fmt_type
                update_stmt = (
                    manifestations_tbl.update()
                    .where(manifestations_tbl.c.id == m_id)
                    .values(meta=meta_dict)
                )
                bind.execute(update_stmt)

    # 2. Drop index on format_type
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=s_cat)}
    idx_format_name = "ix_catalog_manifestations_format_type" if is_pg else "ix_manifestations_format_type"
    if idx_format_name in existing_indexes:
        with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
            batch_op.drop_index(idx_format_name)

    # 3. Drop column format_type and restore publisher length
    manif_cols = {c["name"]: c for c in inspector.get_columns("manifestations", schema=s_cat)}
    with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
        if "format_type" in manif_cols:
            batch_op.drop_column("format_type")
        if "publisher" in manif_cols:
            batch_op.alter_column(
                "publisher",
                type_=sa.String(length=500),
                existing_type=sa.String(length=255),
                existing_nullable=True,
            )
