"""Add Expression.kind for concert/live-performance typing

Revision ID: cdd1a0a92bfa
Revises: b7ad7843fb4a
Create Date: 2026-07-25 12:00:00.000000

Adds a nullable ``kind`` column (String(50), indexed) to
``catalog.expressions`` so live recordings can be typed as Performance Event
Expressions (``live_performance``) instead of being flattened into genre
tags or item-level flags.  The controlled vocabulary is enforced at the
service layer (``app.db.core.EXPRESSION_KINDS``); the database column stays
unconstrained so future kinds do not require a schema migration.

Fully reversible: downgrade drops the column and its index.  No data is
touched on downgrade beyond the column itself.
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

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cdd1a0a92bfa"
down_revision = "b7ad7843fb4a"
branch_labels = None
depends_on = None

_SCHEMA = "catalog"
_TABLE = "expressions"
_INDEX = "ix_expressions_kind"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns(_TABLE, schema=_SCHEMA)}

    with op.batch_alter_table(_TABLE, schema=_SCHEMA) as batch_op:
        if "kind" not in existing_cols:
            batch_op.add_column(sa.Column("kind", sa.String(length=50), nullable=True))

    existing_indexes = {idx["name"] for idx in inspector.get_indexes(_TABLE, schema=_SCHEMA)}
    if _INDEX not in existing_indexes:
        op.create_index(_INDEX, _TABLE, ["kind"], schema=_SCHEMA)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes(_TABLE, schema=_SCHEMA)}
    if _INDEX in existing_indexes:
        op.drop_index(_INDEX, table_name=_TABLE, schema=_SCHEMA)

    existing_cols = {col["name"] for col in inspector.get_columns(_TABLE, schema=_SCHEMA)}
    if "kind" in existing_cols:
        with op.batch_alter_table(_TABLE, schema=_SCHEMA) as batch_op:
            batch_op.drop_column("kind")
