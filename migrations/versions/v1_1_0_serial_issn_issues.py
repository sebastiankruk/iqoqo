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
"""Add serial Work (ISSN/work_kind) and issue Manifestation columns.

Revision ID: v1_1_0_serial_issn_issues
Revises: v1_0_0_add_apple_id_to_users
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic (MUST NOT exceed 32 characters)
revision = "v1_1_0_serial_issn_issues"
down_revision = "v1_0_0_add_apple_id_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add serial ISSN/work_kind columns on works and issue columns on manifestations."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    catalog_schema = "catalog" if is_pg else None

    work_idx_prefix = "ix_catalog_works_" if is_pg else "ix_works_"
    manif_idx_prefix = "ix_catalog_manifestations_" if is_pg else "ix_manifestations_"

    if inspector.has_table("works", schema=catalog_schema):
        work_cols = {col["name"] for col in inspector.get_columns("works", schema=catalog_schema)}
        work_indexes = {idx["name"] for idx in inspector.get_indexes("works", schema=catalog_schema)}
        with op.batch_alter_table("works", schema=catalog_schema) as batch_op:
            if "issn" not in work_cols:
                batch_op.add_column(sa.Column("issn", sa.String(9), nullable=True))
            if f"{work_idx_prefix}issn" not in work_indexes:
                batch_op.create_index(f"{work_idx_prefix}issn", ["issn"], unique=False)

            if "eissn" not in work_cols:
                batch_op.add_column(sa.Column("eissn", sa.String(9), nullable=True))
            if f"{work_idx_prefix}eissn" not in work_indexes:
                batch_op.create_index(f"{work_idx_prefix}eissn", ["eissn"], unique=False)

            if "work_kind" not in work_cols:
                batch_op.add_column(sa.Column("work_kind", sa.String(32), nullable=True))
            if f"{work_idx_prefix}work_kind" not in work_indexes:
                batch_op.create_index(f"{work_idx_prefix}work_kind", ["work_kind"], unique=False)

    if inspector.has_table("manifestations", schema=catalog_schema):
        manif_cols = {col["name"] for col in inspector.get_columns("manifestations", schema=catalog_schema)}
        manif_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=catalog_schema)}
        with op.batch_alter_table("manifestations", schema=catalog_schema) as batch_op:
            if "issue_number" not in manif_cols:
                batch_op.add_column(sa.Column("issue_number", sa.String(32), nullable=True))
            if "cumulative_issue_number" not in manif_cols:
                batch_op.add_column(sa.Column("cumulative_issue_number", sa.Integer(), nullable=True))
            if "volume" not in manif_cols:
                batch_op.add_column(sa.Column("volume", sa.String(32), nullable=True))
            if "publication_year" not in manif_cols:
                batch_op.add_column(sa.Column("publication_year", sa.Integer(), nullable=True))
            if f"{manif_idx_prefix}publication_year" not in manif_indexes:
                batch_op.create_index(f"{manif_idx_prefix}publication_year", ["publication_year"], unique=False)
            if "publication_month" not in manif_cols:
                batch_op.add_column(sa.Column("publication_month", sa.Integer(), nullable=True))
            if "ean_addon" not in manif_cols:
                batch_op.add_column(sa.Column("ean_addon", sa.String(8), nullable=True))
            if "full_barcode" not in manif_cols:
                batch_op.add_column(sa.Column("full_barcode", sa.String(20), nullable=True))
            if f"{manif_idx_prefix}full_barcode" not in manif_indexes:
                batch_op.create_index(f"{manif_idx_prefix}full_barcode", ["full_barcode"], unique=False)


def downgrade() -> None:
    """Drop serial ISSN/work_kind columns on works and issue columns on manifestations."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    catalog_schema = "catalog" if is_pg else None

    work_idx_prefix = "ix_catalog_works_" if is_pg else "ix_works_"
    manif_idx_prefix = "ix_catalog_manifestations_" if is_pg else "ix_manifestations_"

    if inspector.has_table("manifestations", schema=catalog_schema):
        manif_cols = {col["name"] for col in inspector.get_columns("manifestations", schema=catalog_schema)}
        manif_indexes = {idx["name"] for idx in inspector.get_indexes("manifestations", schema=catalog_schema)}
        with op.batch_alter_table("manifestations", schema=catalog_schema) as batch_op:
            if f"{manif_idx_prefix}full_barcode" in manif_indexes:
                batch_op.drop_index(f"{manif_idx_prefix}full_barcode")
            if f"{manif_idx_prefix}publication_year" in manif_indexes:
                batch_op.drop_index(f"{manif_idx_prefix}publication_year")
            for col in (
                "full_barcode",
                "ean_addon",
                "publication_month",
                "publication_year",
                "volume",
                "cumulative_issue_number",
                "issue_number",
            ):
                if col in manif_cols:
                    batch_op.drop_column(col)

    if inspector.has_table("works", schema=catalog_schema):
        work_cols = {col["name"] for col in inspector.get_columns("works", schema=catalog_schema)}
        work_indexes = {idx["name"] for idx in inspector.get_indexes("works", schema=catalog_schema)}
        with op.batch_alter_table("works", schema=catalog_schema) as batch_op:
            for col in ("work_kind", "eissn", "issn"):
                if f"{work_idx_prefix}{col}" in work_indexes:
                    batch_op.drop_index(f"{work_idx_prefix}{col}")
                if col in work_cols:
                    batch_op.drop_column(col)
