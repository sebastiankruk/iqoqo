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
"""Index two unindexed foreign keys and constrain aggregation quantity.

Three separate integrity findings, one migration.

``inventory.items.manifestation_id`` and ``catalog.reading_roadmaps.user_id``
are foreign keys with no index.  PostgreSQL does not create one automatically,
so every lookup by parent and -- more importantly -- every ``ON DELETE CASCADE``
from the parent -- scans the child table.  Deleting a Manifestation currently
plans a sequential scan of ``items``.  ``user_id`` is a UUID column, which makes
the absence doubly likely, since a naive fix might reach for an integer-oriented
convention instead of the type.

``catalog.container_aggregations.quantity`` is nullable with a Python-side
``default=1``.  A column default applies on INSERT only, so an UPDATE can still
store NULL -- and ``frbr_service.py`` serialises ``agg.quantity or 1``, making a
NULL indistinguishable from a genuine 1 at the API boundary.  A data-entry bug
would therefore be invisible rather than caught.  The column is made NOT NULL and
given a positive-value CHECK, since a box containing zero of a component is not
a meaningful state to persist.

Both quantity changes go through ``batch_alter_table`` because SQLite has no
``ALTER COLUMN``; batch mode rebuilds the table there, matching the existing
revisions that handle cross-dialect changes.

Preflight: verified against a production clone that ``container_aggregations``
holds 0 NULL and 0 non-positive rows, so the constraint does not fail on
existing data.  The guard in :func:`upgrade` asserts that at runtime rather than
trusting a one-off check, so a future instance with dirty data fails loudly
instead of midway through a rebuild.

Revision ID: v0_8_2_fk_indexes_and_quantity
Revises: v0_8_2_duplicate_provenance
Create Date: 2026-10-01
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_2_fk_indexes_and_quantity"
down_revision = "v0_8_2_duplicate_provenance"
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    """Whether the bound connection is PostgreSQL, which has named schemas."""
    return op.get_bind().dialect.name == "postgresql"


def _catalog() -> str | None:
    """Return the catalog schema name, or None on dialects without one."""
    return "catalog" if _is_pg() else None


def _inventory() -> str | None:
    """Return the inventory schema name, or None on dialects without one."""
    return "inventory" if _is_pg() else None


def _index_exists(table: str, index: str, schema: str | None) -> bool:
    """Whether ``index`` is already present on ``table``.

    Used so the migration is re-runnable.  An operator who added the index by
    hand, or a database restored from a dump that already has it, should not hit
    "relation already exists".

    Args:
        table: Unqualified table name.
        index: Index name to look for.
        schema: Schema name, or None for a schema-less dialect.

    Returns:
        True when the index exists in the target schema.
    """
    inspector = sa.inspect(op.get_bind())
    return index in {idx["name"] for idx in inspector.get_indexes(table, schema=schema)}


def _bad_quantity_rows(table: str, schema: str | None) -> int:
    """Count rows whose quantity is NULL or non-positive.

    Args:
        table: Unqualified table name.
        schema: Schema name, or None for a schema-less dialect.

    Returns:
        Number of rows that would violate the new NOT NULL + CHECK constraint.
    """
    qualified = table if schema is None else f"{schema}.{table}"
    return int(
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT count(*) FROM {qualified} WHERE quantity IS NULL OR quantity <= 0"
            )  # noqa: S608 - fixed identifiers, not user input
        )
        .scalar_one()
    )


def upgrade():
    """Add the two foreign-key indexes and constrain ``quantity``."""
    catalog = _catalog()
    inventory = _inventory()

    if not _index_exists("items", "ix_items_manifestation_id", inventory):
        op.create_index("ix_items_manifestation_id", "items", ["manifestation_id"], schema=inventory)

    if not _index_exists("reading_roadmaps", "ix_reading_roadmaps_user_id", catalog):
        op.create_index("ix_reading_roadmaps_user_id", "reading_roadmaps", ["user_id"], schema=catalog)

    offenders = _bad_quantity_rows("container_aggregations", catalog)
    if offenders:
        raise RuntimeError(
            f"container_aggregations holds {offenders} row(s) with a NULL or non-positive quantity; "
            "correct them before applying this migration, otherwise the new constraint would fail "
            "partway through a table rebuild"
        )

    with op.batch_alter_table("container_aggregations", schema=catalog) as batch_op:
        batch_op.alter_column("quantity", existing_type=sa.Integer(), nullable=False, server_default="1")
        batch_op.create_check_constraint("check_container_aggregation_quantity", "quantity > 0")


def downgrade():
    """Drop the constraint and both indexes.

    The indexes are dropped unconditionally: they are pure performance objects,
    so leaving one behind would silently change planner behaviour after a
    downgrade, and ``op.drop_index`` raises if the index is missing.
    """
    catalog = _catalog()
    inventory = _inventory()

    with op.batch_alter_table("container_aggregations", schema=catalog) as batch_op:
        batch_op.drop_constraint("check_container_aggregation_quantity", type_="check")
        batch_op.alter_column("quantity", existing_type=sa.Integer(), nullable=True, server_default=None)

    op.drop_index("ix_reading_roadmaps_user_id", table_name="reading_roadmaps", schema=catalog)
    op.drop_index("ix_items_manifestation_id", table_name="items", schema=inventory)
