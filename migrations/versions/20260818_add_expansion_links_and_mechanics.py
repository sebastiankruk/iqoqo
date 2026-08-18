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
"""Add work expansion links and board game mechanics vocabulary."""

import json
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "20260818_add_expansion_links_and_mechanics"
down_revision = "20260814_feedback_comments"
branch_labels = None
depends_on = None


def _get_catalog_schema(bind):
    return "catalog" if bind.dialect.name == "postgresql" else None


def upgrade():
    bind = op.get_bind()
    catalog = _get_catalog_schema(bind)

    op.create_table(
        "work_expansion_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_work_id", sa.Integer(), nullable=False),
        sa.Column("expansion_work_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["base_work_id"],
            [f"{catalog + '.' if catalog else ''}works.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["expansion_work_id"],
            [f"{catalog + '.' if catalog else ''}works.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expansion_work_id"),
        sa.Index("ix_work_expansion_links_base_work_id", "base_work_id"),
        sa.Index("ix_work_expansion_links_expansion_work_id", "expansion_work_id"),
        schema=catalog,
    )

    op.create_table(
        "boardgame_mechanics",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bgg_id", sa.String(length=50), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_boardgame_mechanics_bgg_id", "bgg_id"),
        schema=catalog,
    )

    # Seed mechanics from the canonical JSON taxonomy.
    data_path = Path(__file__).resolve().parents[2] / "data" / "bgg_mechanics.json"
    if data_path.exists():
        mechanics = json.loads(data_path.read_text(encoding="utf-8"))
        if mechanics:
            op.bulk_insert(
                sa.table(
                    "boardgame_mechanics",
                    sa.column("id", sa.String(length=100)),
                    sa.column("name", sa.String(length=255)),
                    sa.column("description", sa.Text()),
                    sa.column("bgg_id", sa.String(length=50)),
                    sa.column("last_updated", sa.DateTime()),
                    schema=catalog,
                ),
                [
                    {
                        "id": entry["id"],
                        "name": entry.get("name") or entry["id"],
                        "description": entry.get("description"),
                        "bgg_id": entry.get("bgg_id"),
                        "last_updated": datetime.now(UTC),
                    }
                    for entry in mechanics
                ],
            )


def downgrade():
    bind = op.get_bind()
    catalog = _get_catalog_schema(bind)

    op.drop_table("boardgame_mechanics", schema=catalog)
    op.drop_table("work_expansion_links", schema=catalog)
