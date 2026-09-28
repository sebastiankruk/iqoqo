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
"""Add resolution_source and allow a null confidence on duplicate_candidates.

A candidate queued by the deterministic classifier carries no probability: the
classifier's verdict is categorical ("these two records share an edition
identifier"), not a model-reported belief.  Storing that in the same
``confidence`` column as an LLM verdict made the two indistinguishable in the
review queue, so provenance is now recorded explicitly and ``confidence`` is
nullable.

``confidence`` is altered inside ``op.batch_alter_table`` because SQLite has no
``ALTER COLUMN``; batch mode rebuilds the table there, matching the 44 existing
revisions that handle cross-dialect column changes.

Revision ID: v0_8_2_duplicate_provenance
Revises: v0_8_2_duplicate_candidates
Create Date: 2026-09-28
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_2_duplicate_provenance"
down_revision = "v0_8_2_duplicate_candidates"
branch_labels = None
depends_on = None


def _qualified(schema: str | None) -> str:
    """Return the schema-qualified table name for DDL emitted by ``op.execute``.

    Args:
        schema: Schema name, or ``None`` on dialects without one.

    Returns:
        The table reference to interpolate into raw SQL.
    """
    return "duplicate_candidates" if schema is None else f"{schema}.duplicate_candidates"


def upgrade():
    """Add the provenance column, relax ``confidence``, and backfill."""
    schema = "inventory" if op.get_bind().dialect.name == "postgresql" else None
    table = _qualified(schema)

    op.add_column(
        table,
        sa.Column("resolution_source", sa.String(length=20), nullable=False, server_default="heuristic"),
    )
    # Every existing row came from the LLM path, so derive provenance from the
    # presence of a rationale rather than trusting the column default.
    op.execute(f"UPDATE {table} SET resolution_source = 'llama' WHERE llm_reasoning IS NOT NULL")

    with op.batch_alter_table(table, schema=schema) as batch_op:
        batch_op.alter_column("confidence", existing_type=sa.Float(), nullable=True)


def downgrade():
    """Restore NOT NULL, clearing heuristic-only candidates first.

    Candidates with a ``NULL`` confidence cannot be represented under the
    previous schema, so they are deleted rather than failing the downgrade.
    That is lossy, but it only ever discards candidates the deterministic
    classifier queued and that no human has reviewed yet: a candidate carrying a
    ``merged`` or ``dismissed`` status necessarily passed through a review
    action, and a reviewed candidate always has a confidence value.
    """
    schema = "inventory" if op.get_bind().dialect.name == "postgresql" else None
    table = _qualified(schema)

    op.execute(f"DELETE FROM {table} WHERE confidence IS NULL")
    with op.batch_alter_table(table, schema=schema) as batch_op:
        batch_op.alter_column("confidence", existing_type=sa.Float(), nullable=False)
    op.drop_column(table, "resolution_source", schema=schema)
