"""Add relational FRBR columns, raw_payload, and ETL backfill

Revision ID: e3f891ab45c2
Revises: cdd1a0a92bfa
Create Date: 2026-07-26 06:00:00.000000

Normalizes core bibliographic properties into typed relational columns:
- catalog.works: sort_title, raw_payload
- catalog.expressions: raw_payload
- catalog.manifestations: format, label, barcode, catalog_number, raw_payload
- inventory.items: raw_payload

Includes server-side batched backfill from ``meta`` JSON into the new columns.
Reversible downgrade drops columns and indexes without modifying ``meta``.
"""

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

import re

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e3f891ab45c2"
down_revision = "cdd1a0a92bfa"
branch_labels = None
depends_on = None

_CATALOG_SCHEMA = "catalog"
_INVENTORY_SCHEMA = "inventory"


def _is_pg(bind) -> bool:
    return bind.dialect.name == "postgresql"


def upgrade():
    bind = op.get_bind()
    is_pg = _is_pg(bind)
    cat_schema = _CATALOG_SCHEMA if is_pg else None
    inv_schema = _INVENTORY_SCHEMA if is_pg else None
    inspector = sa.inspect(bind)

    # 1. catalog.works
    existing_work_cols = {col["name"] for col in inspector.get_columns("works", schema=cat_schema)}
    with op.batch_alter_table("works", schema=cat_schema) as batch_op:
        if "sort_title" not in existing_work_cols:
            batch_op.add_column(sa.Column("sort_title", sa.String(length=1000), nullable=True))
        if "raw_payload" not in existing_work_cols:
            batch_op.add_column(sa.Column("raw_payload", sa.JSON(), nullable=True))

    work_indexes = {idx["name"] for idx in inspector.get_indexes("works", schema=cat_schema)}
    if "ix_works_sort_title" not in work_indexes:
        op.create_index("ix_works_sort_title", "works", ["sort_title"], schema=cat_schema)

    # 2. catalog.expressions
    existing_expr_cols = {col["name"] for col in inspector.get_columns("expressions", schema=cat_schema)}
    with op.batch_alter_table("expressions", schema=cat_schema) as batch_op:
        if "raw_payload" not in existing_expr_cols:
            batch_op.add_column(sa.Column("raw_payload", sa.JSON(), nullable=True))

    # 3. catalog.manifestations
    existing_manif_cols = {col["name"] for col in inspector.get_columns("manifestations", schema=cat_schema)}
    with op.batch_alter_table("manifestations", schema=cat_schema) as batch_op:
        if "format" not in existing_manif_cols:
            batch_op.add_column(sa.Column("format", sa.String(length=50), nullable=True))
        if "label" not in existing_manif_cols:
            batch_op.add_column(sa.Column("label", sa.String(length=500), nullable=True))
        if "barcode" not in existing_manif_cols:
            batch_op.add_column(sa.Column("barcode", sa.String(length=100), nullable=True))
        if "catalog_number" not in existing_manif_cols:
            batch_op.add_column(sa.Column("catalog_number", sa.String(length=100), nullable=True))
        if "raw_payload" not in existing_manif_cols:
            batch_op.add_column(sa.Column("raw_payload", sa.JSON(), nullable=True))

    manif_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=cat_schema)}
    if "ix_manifestations_format" not in manif_indexes:
        op.create_index("ix_manifestations_format", "manifestations", ["format"], schema=cat_schema)
    if "ix_manifestations_barcode" not in manif_indexes:
        op.create_index("ix_manifestations_barcode", "manifestations", ["barcode"], schema=cat_schema)

    # 4. inventory.items
    existing_item_cols = {col["name"] for col in inspector.get_columns("items", schema=inv_schema)}
    with op.batch_alter_table("items", schema=inv_schema) as batch_op:
        if "raw_payload" not in existing_item_cols:
            batch_op.add_column(sa.Column("raw_payload", sa.JSON(), nullable=True))

    # -----------------------------------------------------------------------
    # Backfill logic
    # -----------------------------------------------------------------------
    import time
    works_table = f"{cat_schema}.works" if cat_schema else "works"
    manif_table = f"{cat_schema}.manifestations" if cat_schema else "manifestations"

    if is_pg:
        # PostgreSQL native JSONB backfill
        chunk_size = 1000
        last_id = 0
        while True:
            result = bind.execute(
                sa.text(f"""
                    UPDATE {works_table}
                    SET sort_title = CASE
                        WHEN title ~* '^(the|a|an|ten|ta|to)\\s+' THEN regexp_replace(title, '^(the|a|an|ten|ta|to)\\s+', '', 'i')
                        ELSE title
                    END
                    WHERE id IN (
                        SELECT id FROM {works_table}
                        WHERE id > :last_id AND sort_title IS NULL AND title IS NOT NULL
                        ORDER BY id
                        LIMIT :chunk_size
                    )
                    RETURNING id
                """),
                {"chunk_size": chunk_size, "last_id": last_id}
            )
            rows = result.fetchall()
            if not rows:
                break
            last_id = max(row[0] for row in rows)
            time.sleep(0.1)

        last_id = 0
        while True:
            result = bind.execute(
                sa.text(f"""
                    UPDATE {manif_table}
                    SET format = COALESCE(meta->>'format', meta->>'video_format', meta->>'format_name'),
                        label = COALESCE(meta->>'label', meta->>'studio', meta->>'imprint', meta->>'publisher'),
                        barcode = COALESCE(meta->>'barcode', meta->>'identifier'),
                        catalog_number = COALESCE(meta->>'catalog_number', meta->>'catno', meta->>'sku')
                    WHERE id IN (
                        SELECT id FROM {manif_table}
                        WHERE id > :last_id AND meta IS NOT NULL
                        ORDER BY id
                        LIMIT :chunk_size
                    )
                    RETURNING id
                """),
                {"chunk_size": chunk_size, "last_id": last_id}
            )
            rows = result.fetchall()
            if not rows:
                break
            last_id = max(row[0] for row in rows)
            time.sleep(0.1)
    else:
        # SQLite dialect backfill
        chunk_size = 1000
        last_id = 0
        while True:
            result = bind.execute(
                sa.text(f"""
                    UPDATE {works_table}
                    SET sort_title = title
                    WHERE id IN (
                        SELECT id FROM {works_table}
                        WHERE id > :last_id AND sort_title IS NULL AND title IS NOT NULL
                        ORDER BY id
                        LIMIT :chunk_size
                    )
                    RETURNING id
                """),
                {"chunk_size": chunk_size, "last_id": last_id}
            )
            rows = result.fetchall()
            if not rows:
                break
            last_id = max(row[0] for row in rows)
            time.sleep(0.1)

        last_id = 0
        while True:
            result = bind.execute(
                sa.text(f"""
                    UPDATE {manif_table}
                    SET format = COALESCE(
                            json_extract(meta, '$.format'),
                            json_extract(meta, '$.video_format'),
                            json_extract(meta, '$.format_name')
                        ),
                        label = COALESCE(
                            json_extract(meta, '$.label'),
                            json_extract(meta, '$.studio'),
                            json_extract(meta, '$.imprint'),
                            json_extract(meta, '$.publisher')
                        ),
                        barcode = COALESCE(
                            json_extract(meta, '$.barcode'),
                            json_extract(meta, '$.identifier')
                        ),
                        catalog_number = COALESCE(
                            json_extract(meta, '$.catalog_number'),
                            json_extract(meta, '$.catno'),
                            json_extract(meta, '$.sku')
                        )
                    WHERE id IN (
                        SELECT id FROM {manif_table}
                        WHERE id > :last_id AND meta IS NOT NULL
                        ORDER BY id
                        LIMIT :chunk_size
                    )
                    RETURNING id
                """),
                {"chunk_size": chunk_size, "last_id": last_id}
            )
            rows = result.fetchall()
            if not rows:
                break
            last_id = max(row[0] for row in rows)
            time.sleep(0.1)


def downgrade():
    bind = op.get_bind()
    is_pg = _is_pg(bind)
    cat_schema = _CATALOG_SCHEMA if is_pg else None
    inv_schema = _INVENTORY_SCHEMA if is_pg else None
    inspector = sa.inspect(bind)

    # 1. Drop items.raw_payload
    existing_item_cols = {col["name"] for col in inspector.get_columns("items", schema=inv_schema)}
    if "raw_payload" in existing_item_cols:
        with op.batch_alter_table("items", schema=inv_schema) as batch_op:
            batch_op.drop_column("raw_payload")

    # 2. Drop manifestations columns & indexes
    manif_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=cat_schema)}
    if "ix_manifestations_barcode" in manif_indexes:
        op.drop_index("ix_manifestations_barcode", table_name="manifestations", schema=cat_schema)
    if "ix_manifestations_format" in manif_indexes:
        op.drop_index("ix_manifestations_format", table_name="manifestations", schema=cat_schema)

    existing_manif_cols = {col["name"] for col in inspector.get_columns("manifestations", schema=cat_schema)}
    cols_to_drop = [c for c in ("format", "label", "barcode", "catalog_number", "raw_payload") if c in existing_manif_cols]
    if cols_to_drop:
        with op.batch_alter_table("manifestations", schema=cat_schema) as batch_op:
            for c in cols_to_drop:
                batch_op.drop_column(c)

    # 3. Drop expressions.raw_payload
    existing_expr_cols = {col["name"] for col in inspector.get_columns("expressions", schema=cat_schema)}
    if "raw_payload" in existing_expr_cols:
        with op.batch_alter_table("expressions", schema=cat_schema) as batch_op:
            batch_op.drop_column("raw_payload")

    # 4. Drop works columns & indexes
    work_indexes = {idx["name"] for idx in inspector.get_indexes("works", schema=cat_schema)}
    if "ix_works_sort_title" in work_indexes:
        op.drop_index("ix_works_sort_title", table_name="works", schema=cat_schema)

    existing_work_cols = {col["name"] for col in inspector.get_columns("works", schema=cat_schema)}
    cols_to_drop_work = [c for c in ("sort_title", "raw_payload") if c in existing_work_cols]
    if cols_to_drop_work:
        with op.batch_alter_table("works", schema=cat_schema) as batch_op:
            for c in cols_to_drop_work:
                batch_op.drop_column(c)
