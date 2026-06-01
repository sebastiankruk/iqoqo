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

"""Add federation schema and tables.

Revision ID: 20260531_federation_schema
Revises: 20260529_add_social_notes
Create Date: 2026-05-31 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "20260531_federation_schema"
down_revision = "20260529_add_social_notes"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create federation schema
    op.execute("CREATE SCHEMA IF NOT EXISTS federation")

    # 1. FederationInstance
    if not inspector.has_table("federation_instances", schema="federation"):
        op.create_table(
            "federation_instances",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("domain", sa.String(255), nullable=False),
            sa.Column("shared_inbox_url", sa.String(500), nullable=True),
            sa.Column("software_name", sa.String(100), nullable=True),
            sa.Column("software_version", sa.String(50), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("trust_level", sa.String(20), nullable=False, server_default="untrusted"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("domain", name="uq_federation_instances_domain"),
            schema="federation",
        )
        with op.batch_alter_table("federation_instances", schema="federation") as batch_op:
            batch_op.create_index("ix_federation_instances_domain", ["domain"], unique=True)

    # 2. FederationActor
    if not inspector.has_table("federation_actors", schema="federation"):
        op.create_table(
            "federation_actors",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("actor_uri", sa.String(500), nullable=False),
            sa.Column("inbox_url", sa.String(500), nullable=False),
            sa.Column("outbox_url", sa.String(500), nullable=True),
            sa.Column("public_key_pem", sa.Text(), nullable=True),
            sa.Column("instance_id", sa.Integer(), nullable=False),
            sa.Column("display_name", sa.String(200), nullable=True),
            sa.Column("username", sa.String(100), nullable=True),
            sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("actor_uri", name="uq_federation_actors_actor_uri"),
            sa.ForeignKeyConstraint(["instance_id"], ["federation.federation_instances.id"], ondelete="CASCADE"),
            schema="federation",
        )
        with op.batch_alter_table("federation_actors", schema="federation") as batch_op:
            batch_op.create_index("ix_federation_actors_actor_uri", ["actor_uri"], unique=True)
            batch_op.create_index("ix_federation_actors_instance_id", ["instance_id"], unique=False)

    # 3. FederationFollower
    if not inspector.has_table("federation_followers", schema="federation"):
        op.create_table(
            "federation_followers",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("local_user_id", UUID(as_uuid=True), nullable=False),
            sa.Column("remote_actor_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["local_user_id"], ["auth.users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["remote_actor_id"], ["federation.federation_actors.id"], ondelete="CASCADE"),
            schema="federation",
        )
        with op.batch_alter_table("federation_followers", schema="federation") as batch_op:
            batch_op.create_index("ix_federation_followers_local_user_id", ["local_user_id"], unique=False)
            batch_op.create_index("ix_federation_followers_remote_actor_id", ["remote_actor_id"], unique=False)

    # 4. FederationActivity
    if not inspector.has_table("federation_activities", schema="federation"):
        op.create_table(
            "federation_activities",
            sa.Column("id", UUID(as_uuid=True), nullable=False),
            sa.Column("actor_uri", sa.String(500), nullable=False),
            sa.Column("activity_type", sa.String(50), nullable=False),
            sa.Column("object_json", JSONB(), nullable=True),
            sa.Column("target_uri", sa.String(500), nullable=True),
            sa.Column("direction", sa.String(10), nullable=False, server_default="outbound"),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            schema="federation",
        )
        with op.batch_alter_table("federation_activities", schema="federation") as batch_op:
            batch_op.create_index("ix_federation_activities_actor_uri", ["actor_uri"], unique=False)
            batch_op.create_index("ix_federation_activities_activity_type", ["activity_type"], unique=False)
            batch_op.create_index("ix_federation_activities_status", ["status"], unique=False)

    # 5. FederationConsent
    if not inspector.has_table("federation_consents", schema="federation"):
        op.create_table(
            "federation_consents",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("user_id", UUID(as_uuid=True), nullable=False),
            sa.Column("federated_profile", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("federated_collection", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_federation_consents_user_id"),
            sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
            schema="federation",
        )
        with op.batch_alter_table("federation_consents", schema="federation") as batch_op:
            batch_op.create_index("ix_federation_consents_user_id", ["user_id"], unique=True)

    # 6. Add federation key columns to auth.users
    if not inspector.has_table("users", schema="auth"):
        return

    columns = [col["name"] for col in inspector.get_columns("users", schema="auth")]
    if "federation_key_id" not in columns:
        op.add_column("users", sa.Column("federation_key_id", sa.String(255), nullable=True), schema="auth")
    if "federation_public_key" not in columns:
        op.add_column("users", sa.Column("federation_public_key", sa.Text(), nullable=True), schema="auth")


def downgrade():
    # Remove columns from auth.users
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("users", schema="auth"):
        columns = [col["name"] for col in inspector.get_columns("users", schema="auth")]
        if "federation_public_key" in columns:
            op.drop_column("users", "federation_public_key", schema="auth")
        if "federation_key_id" in columns:
            op.drop_column("users", "federation_key_id", schema="auth")

    # Drop federation tables in reverse order (respecting FKs)
    op.drop_table("federation_consents", schema="federation")
    op.drop_table("federation_activities", schema="federation")
    op.drop_table("federation_followers", schema="federation")
    op.drop_table("federation_actors", schema="federation")
    op.drop_table("federation_instances", schema="federation")

    op.execute("DROP SCHEMA IF EXISTS federation")
