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
"""Correct the foreign-key index names to match the model on PostgreSQL.

Revision ID: v0_8_2_fk_index_names
Revises: v0_8_2_fk_indexes_and_quantity
Create Date: 2026-10-01

Why this exists
---------------
`v0_8_2_fk_indexes_and_quantity` created two indexes under bare names::

    ix_items_manifestation_id
    ix_reading_roadmaps_user_id

Those are the names SQLAlchemy generates for a **schema-less** table, which is
correct on SQLite -- where ``schema=None`` and the ``index=True`` column flag
yields exactly ``ix_items_manifestation_id``.

On PostgreSQL the tables are schema-qualified, and SQLAlchemy's convention
inserts the schema into the name. Verified rather than assumed::

    schema='inventory' -> ['ix_inventory_items_manifestation_id']
    schema='catalog'   -> ['ix_catalog_items_manifestation_id']
    schema=None        -> ['ix_items_manifestation_id']

So on PostgreSQL the migration and the model disagreed on **every** index
name, and `alembic revision --autogenerate` against a fully-migrated database
proposed renaming all three indexes on ``inventory.items`` -- including the two
that predate this change (``ix_inventory_items_owner_id``,
``ix_inventory_items_lent_to_user_id``), which are correct. That is the C40
failure mode: a model/migration divergence is invisible on SQLite, where the
names agree by coincidence, and only shows up as permanent autogenerate noise
on PostgreSQL.

Rather than edit a shipped revision, this renames in place. The indexes are
pure performance objects, so a rename needs no data migration and no lock
beyond the one the index already holds.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "v0_8_2_fk_index_names"
down_revision = "v0_8_2_fk_indexes_and_quantity"
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    """Whether the bound dialect names schemas."""
    return op.get_bind().dialect.name == "postgresql"


def _index_exists(table: str, index: str, schema: str | None) -> bool:
    """Whether ``index`` is already present on ``table``.

    @param table: Unqualified table name.
    @param index: Index name to test.
    @param schema: Schema name, or None for a schema-less dialect.
    @returns: True when the index is present.
    """
    inspector = sa.inspect(op.get_bind())
    if schema is None:
        return any(ix["name"] == index for ix in inspector.get_indexes(table))
    return any(ix["name"] == index for ix in inspector.get_indexes(table, schema=schema))


def _rename(old: str, new: str, table: str, schema: str | None) -> None:
    """Rename an index when both the old and the new name are as expected.

    Each side is checked rather than assumed. An operator who already renamed
    the index by hand should not hit "relation already exists", and a database
    restored from a dump may carry only the new name.

    @param old: The name to rename away from.
    @param new: The name the model expects.
    @param table: Unqualified table name.
    @param schema: Schema name, or None for a schema-less dialect.
    """
    if _index_exists(table, new, schema) or not _index_exists(table, old, schema):
        return
    if schema is None:
        op.execute(sa.text(f'ALTER INDEX "{old}" RENAME TO "{new}"'))
    else:
        op.execute(sa.text(f'ALTER INDEX "{schema}"."{old}" RENAME TO "{new}"'))


# (old, new, table, schema) -- the schema is fixed per table by the model.
#
# The third entry predates this change: `v0_7_17_baseline` created
# `instance_settings` while it still lived in `catalog`, so it named the index
# `ix_catalog_instance_settings_key`. `v0_7_18_fixes` moved the table to
# `config`, and the model followed -- but the index kept its old name, so
# autogenerate wanted to rename it on every run ever since.
RENAMES = (
    ("ix_items_manifestation_id", "ix_inventory_items_manifestation_id", "items", "inventory"),
    ("ix_reading_roadmaps_user_id", "ix_catalog_reading_roadmaps_user_id", "reading_roadmaps", "catalog"),
    ("ix_catalog_instance_settings_key", "ix_config_instance_settings_key", "instance_settings", "config"),
)


def upgrade():
    """Rename each index to the schema-qualified name the model generates."""
    if not _is_pg():
        # On SQLite the migration's names are already the model's names.
        return

    for old, new, table, schema in RENAMES:
        _rename(old, new, table, schema)


def downgrade():
    """Restore the pre-existing names.

    On PostgreSQL this reintroduces the divergence with the model, which is the
    state this migration was written to correct; on SQLite nothing was renamed.
    """
    if not _is_pg():
        return

    for old, new, table, schema in RENAMES:
        _rename(new, old, table, schema)
