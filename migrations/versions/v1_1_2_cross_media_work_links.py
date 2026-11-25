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
"""Add catalog.work_relations and inventory.work_link_candidates for cross-media Work linking.

Revision ID: v1_1_2_cross_media_work_links
Revises: v1_1_1_norm_legacy_formats
Create Date: 2026-11-24 17:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "v1_1_2_cross_media_work_links"
down_revision = "v1_1_1_norm_legacy_formats"
branch_labels = None
depends_on = None

_RELATION_TYPES = ("is_adaptation_of", "is_derivative_of", "inspired_by", "sequel_to", "spin_off_of", "companion_to")
_CANDIDATE_STATUSES = ("pending", "accepted", "dismissed")
_RESOLUTION_SOURCES = ("heuristic", "llm")


def _schema_names() -> tuple[str | None, str | None, str | None, str, str, str]:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    catalog = "catalog" if is_pg else None
    inventory = "inventory" if is_pg else None
    auth = "auth" if is_pg else None
    catalog_pfx = "catalog." if is_pg else ""
    inventory_pfx = "inventory." if is_pg else ""
    auth_pfx = "auth." if is_pg else ""
    return catalog, inventory, auth, catalog_pfx, inventory_pfx, auth_pfx


def upgrade() -> None:
    """Create work_relations and work_link_candidates tables with constraints and indexes."""
    catalog, inventory, _auth, catalog_pfx, inventory_pfx, auth_pfx = _schema_names()
    uuid_type = postgresql.UUID(as_uuid=True) if op.get_bind().dialect.name == "postgresql" else sa.String(length=36)

    op.create_table(
        "work_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_work_id", sa.Integer(), sa.ForeignKey(f"{catalog_pfx}works.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_work_id", sa.Integer(), sa.ForeignKey(f"{catalog_pfx}works.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False, server_default="is_adaptation_of"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", uuid_type, sa.ForeignKey(f"{auth_pfx}users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("source_work_id <> target_work_id", name="ck_work_relations_no_self_link"),
        sa.CheckConstraint(
            f"relation_type IN ({', '.join(repr(t) for t in _RELATION_TYPES)})",
            name="ck_work_relations_relation_type",
        ),
        sa.UniqueConstraint("source_work_id", "target_work_id", "relation_type", name="uq_work_relations_triple"),
        schema=catalog,
    )
    op.create_index("ix_work_relations_source_work_id", "work_relations", ["source_work_id"], schema=catalog)
    op.create_index("ix_work_relations_target_work_id", "work_relations", ["target_work_id"], schema=catalog)

    op.create_table(
        "work_link_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_work_id", sa.Integer(), sa.ForeignKey(f"{catalog_pfx}works.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_work_id", sa.Integer(), sa.ForeignKey(f"{catalog_pfx}works.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposed_relation_type", sa.String(length=50), nullable=False, server_default="is_adaptation_of"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("resolution_source", sa.String(length=20), nullable=False, server_default="heuristic"),
        sa.Column("llm_reasoning", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by_id", uuid_type, sa.ForeignKey(f"{auth_pfx}users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("source_work_id <> target_work_id", name="ck_work_link_candidates_no_self_link"),
        sa.CheckConstraint(
            f"proposed_relation_type IN ({', '.join(repr(t) for t in _RELATION_TYPES)})",
            name="ck_work_link_candidates_relation_type",
        ),
        sa.CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in _CANDIDATE_STATUSES)})",
            name="ck_work_link_candidates_status",
        ),
        sa.CheckConstraint(
            f"resolution_source IN ({', '.join(repr(r) for r in _RESOLUTION_SOURCES)})",
            name="ck_work_link_candidates_resolution_source",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_work_link_candidates_confidence_range",
        ),
        schema=inventory,
    )
    op.create_index("ix_work_link_candidates_status_confidence", "work_link_candidates", ["status", "confidence"], schema=inventory)
    op.create_index("ix_work_link_candidates_source_work_id", "work_link_candidates", ["source_work_id"], schema=inventory)
    op.create_index("ix_work_link_candidates_target_work_id", "work_link_candidates", ["target_work_id"], schema=inventory)
    op.execute(
        f"CREATE UNIQUE INDEX uq_work_link_candidates_pair ON {inventory_pfx}work_link_candidates "
        "((CASE WHEN source_work_id <= target_work_id THEN source_work_id ELSE target_work_id END), "
        "(CASE WHEN source_work_id <= target_work_id THEN target_work_id ELSE source_work_id END))"
    )


def downgrade() -> None:
    """Drop work_link_candidates and work_relations tables."""
    catalog, inventory, _auth, _catalog_pfx, inventory_pfx, _auth_pfx = _schema_names()
    op.execute(f"DROP INDEX IF EXISTS {inventory_pfx}uq_work_link_candidates_pair")
    op.drop_index("ix_work_link_candidates_target_work_id", table_name="work_link_candidates", schema=inventory)
    op.drop_index("ix_work_link_candidates_source_work_id", table_name="work_link_candidates", schema=inventory)
    op.drop_index("ix_work_link_candidates_status_confidence", table_name="work_link_candidates", schema=inventory)
    op.drop_table("work_link_candidates", schema=inventory)

    op.drop_index("ix_work_relations_target_work_id", table_name="work_relations", schema=catalog)
    op.drop_index("ix_work_relations_source_work_id", table_name="work_relations", schema=catalog)
    op.drop_table("work_relations", schema=catalog)
