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

This migration promotes physical Manifestation attributes from JSON metadata
to typed columns: isbn13, publisher, and format_type.

IMPORTANT: This migration includes preflight checks to ensure data quality
before schema changes. Run preflight separately if needed:
    from migrations.versions.v0_7_19_f3_column_promotion import run_preflight
    report = run_preflight(bind)
    print(report)
"""

import json
import logging
from typing import Any
import sqlalchemy as sa
from alembic import op

# Import shared validation utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.core.f3_validation import (
    MAX_PUBLISHER_LENGTH,
    PreflightReport,
    extract_promoted_key_case_insensitive,
    normalize_isbn,
    validate_publisher,
    validate_format_type,
    ISBNValidationError,
)

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "v0_7_19_f3_column_promotion"
down_revision = "v0_7_18_fixes"
branch_labels = None
depends_on = None

BATCH_SIZE = 500


def run_preflight(bind) -> PreflightReport:
    """Run preflight checks before migration.

    This function scans the manifestations table for data quality issues
    that could cause migration failures or data loss.

    Args:
        bind: SQLAlchemy connection/binding

    Returns:
        PreflightReport with all detected issues
    """
    report = PreflightReport()
    is_pg = bind.dialect.name == "postgresql"
    s_cat = "catalog" if is_pg else None

    manifestations_tbl = sa.Table(
        "manifestations",
        sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("isbn13", sa.String(length=13), nullable=True),
        sa.Column("publisher", sa.String(length=500), nullable=True),
        sa.Column("format_type", sa.String(length=50), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        schema=s_cat,
    )

    # Scan all manifestations
    last_id = 0
    isbn_map: dict[str, list[int]] = {}  # Track ISBN duplicates

    while True:
        select_stmt = (
            sa.select(
                manifestations_tbl.c.id,
                manifestations_tbl.c.isbn13,
                manifestations_tbl.c.publisher,
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
            raw_meta = row[3]
            last_id = m_id

            # Check publisher length
            if curr_pub and len(curr_pub) > MAX_PUBLISHER_LENGTH:
                report.add_long_publisher(m_id, curr_pub, len(curr_pub))

            # Check ISBN validity and track duplicates
            if curr_isbn:
                if curr_isbn not in isbn_map:
                    isbn_map[curr_isbn] = []
                isbn_map[curr_isbn].append(m_id)

                # Validate ISBN
                try:
                    normalize_isbn(curr_isbn)
                except ISBNValidationError as e:
                    report.add_invalid_isbn(m_id, curr_isbn, str(e))

            # Check metadata for mixed-case promoted keys
            if raw_meta and isinstance(raw_meta, dict):
                promoted_keys = ["isbn13", "isbn", "publisher", "format_type"]
                for key in promoted_keys:
                    value = extract_promoted_key_case_insensitive(raw_meta, key)
                    if value is not None:
                        # Check if the actual key has different casing
                        for actual_key in raw_meta.keys():
                            if isinstance(actual_key, str) and actual_key.lower() == key.lower():
                                if actual_key != key:
                                    report.add_mixed_case_key(m_id, actual_key, key)
                                break

    # Check for ISBN conflicts
    for isbn, m_ids in isbn_map.items():
        if len(m_ids) > 1:
            report.add_isbn_conflict(isbn, m_ids)

    return report


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    s_cat = "catalog" if is_pg else None

    # STEP 0: Run preflight checks
    logger.info("Running preflight checks...")
    report = run_preflight(bind)

    if report.blocking_issues:
        logger.error("Preflight found blocking issues:\n%s", report)
        raise RuntimeError(
            "Migration blocked by preflight issues. "
            "Resolve the issues and retry. "
            "See report for details."
        )

    if report.has_issues:
        logger.warning("Preflight found non-blocking issues:\n%s", report)

    logger.info("Preflight passed. Proceeding with migration...")

    # STEP 1: Add format_type column if not exists
    manif_cols = {c["name"]: c for c in inspector.get_columns("manifestations", schema=s_cat)}

    with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
        if "format_type" not in manif_cols:
            batch_op.add_column(sa.Column("format_type", sa.String(length=50), nullable=True))

    # STEP 2: Add index on format_type if not exists
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=s_cat)}
    idx_format_name = "ix_catalog_manifestations_format_type" if is_pg else "ix_manifestations_format_type"
    if idx_format_name not in existing_indexes:
        with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
            batch_op.create_index(idx_format_name, ["format_type"], unique=False)

    # STEP 3: Batch backfill from meta and prune promoted keys
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
    backfill_count = 0

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

            # Backfill isbn13 if missing using shared validation
            if not new_isbn:
                raw_isbn = extract_promoted_key_case_insensitive(meta_dict, "isbn13")
                if not raw_isbn:
                    raw_isbn = extract_promoted_key_case_insensitive(meta_dict, "isbn")
                if raw_isbn and isinstance(raw_isbn, str):
                    try:
                        normalized = normalize_isbn(raw_isbn)
                        if normalized:
                            new_isbn = normalized
                    except ISBNValidationError:
                        # Skip invalid ISBNs
                        logger.warning(f"Skipping invalid ISBN for manifestation {m_id}: {raw_isbn}")

            # Backfill publisher if missing using shared validation
            if not new_pub:
                raw_pub = extract_promoted_key_case_insensitive(meta_dict, "publisher")
                if raw_pub and isinstance(raw_pub, str):
                    normalized = validate_publisher(raw_pub, strict=False)
                    if normalized:
                        new_pub = normalized

            # Backfill format_type if missing using shared validation
            if not new_fmt_type:
                raw_fmt = (
                    extract_promoted_key_case_insensitive(meta_dict, "format_type")
                    or curr_fmt
                    or extract_promoted_key_case_insensitive(meta_dict, "format")
                    or extract_promoted_key_case_insensitive(meta_dict, "video_format")
                )
                if raw_fmt and isinstance(raw_fmt, str):
                    normalized = validate_format_type(raw_fmt, strict=False)
                    if normalized:
                        new_fmt_type = normalized

            # Prune promoted keys from meta (case-insensitive)
            promoted_keys = ["isbn13", "isbn", "publisher", "format_type"]
            for key in promoted_keys:
                keys_to_remove = [
                    k for k in meta_dict.keys()
                    if isinstance(k, str) and k.lower() == key.lower()
                ]
                for k in keys_to_remove:
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
                backfill_count += 1

    logger.info(f"Backfilled {backfill_count} manifestations")

    # STEP 4: Narrow publisher column AFTER backfill (safe ordering)
    with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
        if "publisher" in manif_cols:
            batch_op.alter_column(
                "publisher",
                type_=sa.String(length=255),
                existing_type=sa.String(length=500),
                existing_nullable=True,
            )

    logger.info("Migration completed successfully")


def downgrade():
    """Downgrade migration: restore publisher column width and remove format_type.

    IMPORTANT: This downgrade restores promoted values back to metadata where possible.
    However, if metadata was pruned during upgrade, some values may not be recoverable
    unless a verified backup exists.

    Reversibility contract:
    - format_type column values are restored to meta["format_type"]
    - isbn13, publisher values remain in columns (not restored to meta)
    - Pruned metadata keys are NOT restored (requires backup)

    For production downgrades, ensure a verified backup exists before proceeding.
    """
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    s_cat = "catalog" if is_pg else None

    # STEP 1: Widen publisher column BEFORE backfill (safe ordering)
    manif_cols = {c["name"]: c for c in inspector.get_columns("manifestations", schema=s_cat)}
    with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
        if "publisher" in manif_cols:
            batch_op.alter_column(
                "publisher",
                type_=sa.String(length=500),
                existing_type=sa.String(length=255),
                existing_nullable=True,
            )

    # STEP 2: Backfill format_type back to meta before dropping column
    manifestations_tbl = sa.Table(
        "manifestations",
        sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("format_type", sa.String(length=50), nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
        schema=s_cat,
    )

    last_id = 0
    restore_count = 0
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
                restore_count += 1

    logger.info(f"Restored {restore_count} format_type values to metadata")

    # STEP 3: Drop index on format_type
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=s_cat)}
    idx_format_name = "ix_catalog_manifestations_format_type" if is_pg else "ix_manifestations_format_type"
    if idx_format_name in existing_indexes:
        with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
            batch_op.drop_index(idx_format_name)

    # STEP 4: Drop column format_type
    with op.batch_alter_table("manifestations", schema=s_cat) as batch_op:
        if "format_type" in manif_cols:
            batch_op.drop_column("format_type")

    logger.info("Downgrade completed successfully")
