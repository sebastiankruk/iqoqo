"""Add operation_type to llm_telemetry and update composite unique constraint

Revision ID: 20260330_add_operation_type_to_llm_telemetry
Revises: 46385ad9cce1
Create Date: 2026-03-30 20:37:00.000000

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
#
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260330_add_operation_type_to_llm_telemetry"
down_revision = "46385ad9cce1"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns_llm = [c["name"] for c in inspector.get_columns("llm_telemetry")]

    # Add operation_type column if missing
    if "operation_type" not in columns_llm:
        with op.batch_alter_table("llm_telemetry", schema=None) as batch_op:
            batch_op.add_column(sa.Column("operation_type", sa.String(length=50), nullable=True, server_default="cover_generation"))

        # Ensure existing rows have a sensible default
        op.execute("UPDATE llm_telemetry SET operation_type = 'cover_generation' WHERE operation_type IS NULL")

        # Make column non-nullable and remove server default
        with op.batch_alter_table("llm_telemetry", schema=None) as batch_op:
            batch_op.alter_column(
                "operation_type",
                existing_type=sa.String(length=50),
                nullable=False,
                existing_nullable=True,
                server_default=None,
                existing_server_default="cover_generation",
            )

    # Reconcile unique constraints: replace old provider-user constraint with provider-user-operation_type
    uqs = inspector.get_unique_constraints("llm_telemetry")
    uq_names = [u["name"] for u in uqs]

    with op.batch_alter_table("llm_telemetry", schema=None) as batch_op:
        # drop legacy single-column provider unique if present
        if "llm_telemetry_provider_key" in uq_names:
            batch_op.drop_constraint("llm_telemetry_provider_key", type_="unique")
        # drop old provider-user composite if present
        if "uq_provider_user" in uq_names:
            batch_op.drop_constraint("uq_provider_user", type_="unique")
        # create new composite constraint if absent
        if "uq_provider_user_op" not in uq_names:
            batch_op.create_unique_constraint("uq_provider_user_op", ["provider", "user_id", "operation_type"]) 


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns_llm = [c["name"] for c in inspector.get_columns("llm_telemetry")]
    uqs = inspector.get_unique_constraints("llm_telemetry")
    uq_names = [u["name"] for u in uqs]

    with op.batch_alter_table("llm_telemetry", schema=None) as batch_op:
        # remove new constraint if present
        if "uq_provider_user_op" in uq_names:
            batch_op.drop_constraint("uq_provider_user_op", type_="unique")
        # recreate older provider-user composite if missing
        if "uq_provider_user" not in uq_names:
            batch_op.create_unique_constraint("uq_provider_user", ["provider", "user_id"])
        # restore legacy provider_key unique if needed (no-op if already present)
        if "llm_telemetry_provider_key" not in uq_names:
            # do not recreate single-column provider unique unconditionally as it may be undesirable
            pass

        # drop operation_type column if present
        if "operation_type" in columns_llm:
            batch_op.drop_column("operation_type")
