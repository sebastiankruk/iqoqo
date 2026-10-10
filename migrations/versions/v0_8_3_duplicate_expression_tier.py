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
"""Widen duplicate_candidates entity_tier check constraint to include expression.

Allows duplicate detection, classification, and merge tracking at the FRBR
Expression (F2) tier in the review queue.

Revision ID: v0_8_3_duplicate_expression_tier
Revises: v0_8_3_roadmap_item_target
Create Date: 2026-10-08
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_3_duplicate_expression_tier"
down_revision = "v0_8_3_roadmap_item_target"
branch_labels = None
depends_on = None

_TABLE = "duplicate_candidates"


def _schema() -> str | None:
    """Return the schema name when the dialect has one.

    Returns:
        ``"inventory"`` on PostgreSQL, ``None`` elsewhere.
    """
    return "inventory" if op.get_bind().dialect.name == "postgresql" else None


def _qualified(schema: str | None) -> str:
    """Return the schema-qualified name for raw SQL.

    Args:
        schema: Schema name, or ``None`` on dialects without one.

    Returns:
        The table reference to interpolate into a SQL string.
    """
    return _TABLE if schema is None else f"{schema}.{_TABLE}"


def upgrade() -> None:
    """Relax ck_duplicate_candidates_entity_tier to include 'expression'."""
    schema = _schema()
    with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
        batch_op.drop_constraint("ck_duplicate_candidates_entity_tier", type_="check")
        batch_op.create_check_constraint(
            "ck_duplicate_candidates_entity_tier",
            "entity_tier IN ('work', 'expression', 'manifestation')",
        )


def downgrade() -> None:
    """Restore the two-value constraint, failing loudly if expression candidates exist.

    Existing review history is never discarded: if expression-tier candidates
    exist in the table, downgrade raises RuntimeError listing the offending
    candidate IDs.
    """
    bind = op.get_bind()
    schema = _schema()
    table_name = _qualified(schema)

    rows = bind.execute(
        sa.text(f"SELECT id FROM {table_name} WHERE entity_tier = 'expression' ORDER BY id")
    ).scalars().all()
    if rows:
        ids_str = ", ".join(str(r) for r in rows)
        raise RuntimeError(
            f"Cannot downgrade migration while {len(rows)} expression-tier candidate(s) exist: "
            f"candidate ID(s) [{ids_str}]. Resolve or remove them before downgrading."
        )

    with op.batch_alter_table(_TABLE, schema=schema) as batch_op:
        batch_op.drop_constraint("ck_duplicate_candidates_entity_tier", type_="check")
        batch_op.create_check_constraint(
            "ck_duplicate_candidates_entity_tier",
            "entity_tier IN ('work', 'manifestation')",
        )
