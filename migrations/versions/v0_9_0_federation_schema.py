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
"""Create federation schema and models.

Revision ID: v0_9_0_federation_schema
Revises: v0_8_4_item_local_barcode
Create Date: 2026-10-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "v0_9_0_federation_schema"
down_revision = "v0_8_4_item_local_barcode"
branch_labels = None
depends_on = None


def upgrade():
    """Create federation schema, tables, and User federation key columns."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    fed_schema = "federation" if is_pg else None
    auth_schema = "auth" if is_pg else None
    json_type = JSONB if is_pg else sa.JSON
    uuid_type = UUID(as_uuid=True) if is_pg else sa.String(36)

    auth_users_fk = "auth.users.id" if is_pg else "users.id"
    fed_instances_fk = "federation.federation_instances.id" if is_pg else "federation_instances.id"
    fed_actors_fk = "federation.federation_actors.id" if is_pg else "federation_actors.id"

    # Create federation schema on PostgreSQL
    if is_pg:
        op.execute("CREATE SCHEMA IF NOT EXISTS federation")

    fed_idx_prefix = "ix_federation_federation_" if is_pg else "ix_federation_"

    # 1. FederationInstance
    if not inspector.has_table("federation_instances", schema=fed_schema):
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
            schema=fed_schema,
        )
        with op.batch_alter_table("federation_instances", schema=fed_schema) as batch_op:
            batch_op.create_index(f"{fed_idx_prefix}instances_domain", ["domain"], unique=True)

    # 2. FederationActor
    if not inspector.has_table("federation_actors", schema=fed_schema):
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
            sa.ForeignKeyConstraint(["instance_id"], [fed_instances_fk], ondelete="CASCADE"),
            schema=fed_schema,
        )
        with op.batch_alter_table("federation_actors", schema=fed_schema) as batch_op:
            batch_op.create_index(f"{fed_idx_prefix}actors_actor_uri", ["actor_uri"], unique=True)

    # 3. FederationFollower
    if not inspector.has_table("federation_followers", schema=fed_schema):
        op.create_table(
            "federation_followers",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("local_user_id", uuid_type, nullable=False),
            sa.Column("remote_actor_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["local_user_id"], [auth_users_fk], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["remote_actor_id"], [fed_actors_fk], ondelete="CASCADE"),
            schema=fed_schema,
        )
        with op.batch_alter_table("federation_followers", schema=fed_schema) as batch_op:
            batch_op.create_index(f"{fed_idx_prefix}followers_local_user_id", ["local_user_id"], unique=False)
            batch_op.create_index(f"{fed_idx_prefix}followers_remote_actor_id", ["remote_actor_id"], unique=False)

    # 4. FederationActivity
    if not inspector.has_table("federation_activities", schema=fed_schema):
        op.create_table(
            "federation_activities",
            sa.Column("id", uuid_type, nullable=False),
            sa.Column("actor_uri", sa.String(500), nullable=False),
            sa.Column("activity_type", sa.String(50), nullable=False),
            sa.Column("object_json", json_type, nullable=True),
            sa.Column("target_uri", sa.String(500), nullable=True),
            sa.Column("direction", sa.String(10), nullable=False, server_default="outbound"),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            schema=fed_schema,
        )
        with op.batch_alter_table("federation_activities", schema=fed_schema) as batch_op:
            batch_op.create_index(f"{fed_idx_prefix}activities_actor_uri", ["actor_uri"], unique=False)
            batch_op.create_index(f"{fed_idx_prefix}activities_activity_type", ["activity_type"], unique=False)

    # 5. FederationConsent
    if not inspector.has_table("federation_consents", schema=fed_schema):
        op.create_table(
            "federation_consents",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("user_id", uuid_type, nullable=False),
            sa.Column("federated_profile", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("federated_collection", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_federation_consents_user_id"),
            sa.ForeignKeyConstraint(["user_id"], [auth_users_fk], ondelete="CASCADE"),
            schema=fed_schema,
        )
        with op.batch_alter_table("federation_consents", schema=fed_schema) as batch_op:
            batch_op.create_index(f"{fed_idx_prefix}consents_user_id", ["user_id"], unique=True)

    # 6. Add federation key columns to auth.users / users
    if inspector.has_table("users", schema=auth_schema):
        columns = [col["name"] for col in inspector.get_columns("users", schema=auth_schema)]
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            if "federation_key_id" not in columns:
                batch_op.add_column(sa.Column("federation_key_id", sa.String(255), nullable=True))
            if "federation_public_key" not in columns:
                batch_op.add_column(sa.Column("federation_public_key", sa.Text(), nullable=True))


def downgrade():
    """Drop federation tables, schema, and columns."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    fed_schema = "federation" if is_pg else None
    auth_schema = "auth" if is_pg else None

    # Remove columns from users
    if inspector.has_table("users", schema=auth_schema):
        columns = [col["name"] for col in inspector.get_columns("users", schema=auth_schema)]
        with op.batch_alter_table("users", schema=auth_schema) as batch_op:
            if "federation_public_key" in columns:
                batch_op.drop_column("federation_public_key")
            if "federation_key_id" in columns:
                batch_op.drop_column("federation_key_id")

    # Drop federation tables in reverse order (respecting FKs)
    if inspector.has_table("federation_consents", schema=fed_schema):
        op.drop_table("federation_consents", schema=fed_schema)
    if inspector.has_table("federation_activities", schema=fed_schema):
        op.drop_table("federation_activities", schema=fed_schema)
    if inspector.has_table("federation_followers", schema=fed_schema):
        op.drop_table("federation_followers", schema=fed_schema)
    if inspector.has_table("federation_actors", schema=fed_schema):
        op.drop_table("federation_actors", schema=fed_schema)
    if inspector.has_table("federation_instances", schema=fed_schema):
        op.drop_table("federation_instances", schema=fed_schema)

    if is_pg:
        op.execute("DROP SCHEMA IF EXISTS federation")
