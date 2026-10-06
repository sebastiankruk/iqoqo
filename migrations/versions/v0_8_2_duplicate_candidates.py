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
"""Add inventory.duplicate_candidates table for FRBR duplicate review queue.

Revision ID: v0_8_2_duplicate_candidates
Revises: v0_8_2_semantic_links
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_2_duplicate_candidates"
down_revision = "v0_8_2_semantic_links"
branch_labels = None
depends_on = None


def _pair_ordering() -> tuple[sa.TextClause, sa.TextClause]:
    """Return portable canonical-ordering expressions for the pair columns.

    ``LEAST``/``GREATEST`` are PostgreSQL-only, while the test suite and local
    development runs on SQLite.  Scalar ``CASE`` expressions are supported by
    both dialects.

    Each expression is wrapped in its own parentheses because PostgreSQL parses
    an unwrapped expression as a column separator inside ``CREATE INDEX``.  The
    column names are unambiguous here (single-table index), so raw ``text()`` is
    safe and keeps the emitted DDL identical across dialects.
    """
    low = sa.text("(CASE WHEN source_id <= target_id THEN source_id ELSE target_id END)")
    high = sa.text("(CASE WHEN source_id <= target_id THEN target_id ELSE source_id END)")
    return low, high


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inventory_schema = "inventory" if is_pg else None
    auth_schema = "auth" if is_pg else None
    auth_users_table = f"{auth_schema}.users" if auth_schema else "users"

    op.create_table(
        "duplicate_candidates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_tier", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("llm_reasoning", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["resolved_by_id"], [auth_users_table + ".id"], ondelete="SET NULL"),
        sa.CheckConstraint("entity_tier IN ('work', 'manifestation')", name="ck_duplicate_candidates_entity_tier"),
        sa.CheckConstraint("status IN ('pending', 'merged', 'dismissed')", name="ck_duplicate_candidates_status"),
        sa.CheckConstraint("source_id <> target_id", name="ck_duplicate_candidates_distinct_entities"),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_duplicate_candidates_confidence_range"),
        schema=inventory_schema,
    )

    op.create_index(
        "ix_duplicate_candidates_status_confidence",
        "duplicate_candidates",
        ["status", "confidence"],
        schema=inventory_schema,
    )
    op.create_index(
        "ix_duplicate_candidates_tier_pair",
        "duplicate_candidates",
        ["entity_tier", "source_id", "target_id"],
        schema=inventory_schema,
    )
    op.create_index(
        "ix_duplicate_candidates_resolved_by_id",
        "duplicate_candidates",
        ["resolved_by_id"],
        schema=inventory_schema,
    )

    # Order-insensitive uniqueness: (5, 9) and (9, 5) collide on the same pair.
    low, high = _pair_ordering()
    op.create_index(
        "uq_duplicate_candidates_pair",
        "duplicate_candidates",
        ["entity_tier", low, high],
        unique=True,
        schema=inventory_schema,
    )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inventory_schema = "inventory" if is_pg else None

    op.drop_index("uq_duplicate_candidates_pair", table_name="duplicate_candidates", schema=inventory_schema)
    op.drop_index("ix_duplicate_candidates_resolved_by_id", table_name="duplicate_candidates", schema=inventory_schema)
    op.drop_index("ix_duplicate_candidates_tier_pair", table_name="duplicate_candidates", schema=inventory_schema)
    op.drop_index("ix_duplicate_candidates_status_confidence", table_name="duplicate_candidates", schema=inventory_schema)
    op.drop_table("duplicate_candidates", schema=inventory_schema)
