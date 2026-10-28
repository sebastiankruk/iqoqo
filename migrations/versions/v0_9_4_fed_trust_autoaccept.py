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
"""Normalize federation trust levels to 3 tiers and add auto_accept_follows.

Revision ID: v0_9_4_fed_trust_autoaccept
Revises: v0_9_3_pats
Create Date: 2026-10-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic (MUST NOT exceed 32 characters)
revision = "v0_9_4_fed_trust_autoaccept"
down_revision = "v0_9_3_pats"
branch_labels = None
depends_on = None


def upgrade():
    """Normalize pending trust levels to untrusted and add consent auto_accept_follows."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    fed_schema = "federation" if is_pg else None

    # 1. Normalize existing 'pending' trust levels to 'untrusted' in federation_instances
    if inspector.has_table("federation_instances", schema=fed_schema):
        instances_table = (
            sa.Table(
                "federation_instances",
                sa.MetaData(),
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column("trust_level", sa.String(20)),
                schema=fed_schema,
            )
        )
        op.execute(
            instances_table.update()
            .where(instances_table.c.trust_level == "pending")
            .values(trust_level="untrusted")
        )
        with op.batch_alter_table("federation_instances", schema=fed_schema) as batch_op:
            batch_op.alter_column(
                "trust_level",
                existing_type=sa.String(20),
                server_default="untrusted",
                nullable=False,
            )

    # 2. Add auto_accept_follows column to federation_consents table
    if inspector.has_table("federation_consents", schema=fed_schema):
        consent_cols = [c["name"] for c in inspector.get_columns("federation_consents", schema=fed_schema)]
        if "auto_accept_follows" not in consent_cols:
            with op.batch_alter_table("federation_consents", schema=fed_schema) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "auto_accept_follows",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("false"),
                    )
                )


def downgrade():
    """Revert auto_accept_follows column from federation_consents."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    fed_schema = "federation" if is_pg else None

    if inspector.has_table("federation_consents", schema=fed_schema):
        consent_cols = [c["name"] for c in inspector.get_columns("federation_consents", schema=fed_schema)]
        if "auto_accept_follows" in consent_cols:
            with op.batch_alter_table("federation_consents", schema=fed_schema) as batch_op:
                batch_op.drop_column("auto_accept_follows")
