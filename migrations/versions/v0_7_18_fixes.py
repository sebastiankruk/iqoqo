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
"""Consolidated incremental schema fixes for v0.7.18.

Revision ID: v0_7_18_fixes
Revises: v0_7_17_baseline
Create Date: 2026-09-12
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "v0_7_18_fixes"
down_revision = "v0_7_17_baseline"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    s_auth = "auth" if is_pg else None
    s_cat = "catalog" if is_pg else None
    s_inv = "inventory" if is_pg else None
    s_cfg = "config" if is_pg else None

    # 1. Config schema and instance_settings migration (PostgreSQL)
    if is_pg:
        op.execute("CREATE SCHEMA IF NOT EXISTS config")
        if inspector.has_table("instance_settings", schema=s_cat):
            op.execute("ALTER TABLE catalog.instance_settings SET SCHEMA config")
            op.execute(
                "ALTER INDEX IF EXISTS catalog.ix_catalog_instance_settings_key "
                "RENAME TO ix_config_instance_settings_key"
            )

    # 2. Token blocklist expiration column & index
    tbl_cols = [c["name"] for c in inspector.get_columns("token_blocklist", schema=s_auth)]
    if "expires_at" not in tbl_cols:
        with op.batch_alter_table("token_blocklist", schema=s_auth) as batch_op:
            batch_op.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
            batch_op.create_index("ix_auth_token_blocklist_expires_at", ["expires_at"], unique=False)
    else:
        indexes = [idx["name"] for idx in inspector.get_indexes("token_blocklist", schema=s_auth)]
        if "ix_auth_token_blocklist_expires_at" not in indexes:
            with op.batch_alter_table("token_blocklist", schema=s_auth) as batch_op:
                batch_op.create_index("ix_auth_token_blocklist_expires_at", ["expires_at"], unique=False)

    # 3. Check constraints on users, items, user_work_intents, loan_requests
    user_checks = {c["name"] for c in inspector.get_check_constraints("users", schema=s_auth)}
    if "ck_users_visibility" not in user_checks:
        with op.batch_alter_table("users", schema=s_auth) as batch_op:
            batch_op.create_check_constraint(
                "ck_users_visibility",
                "visibility IN ('public', 'private')",
            )

    item_checks = {c["name"] for c in inspector.get_check_constraints("items", schema=s_inv)}
    with op.batch_alter_table("items", schema=s_inv) as batch_op:
        if "ck_items_status" not in item_checks:
            batch_op.create_check_constraint(
                "ck_items_status",
                "status IN ('wish_list', 'ordered', 'available', 'lent', 'damaged', 'lost', "
                "'dnf', 'listened', 'listening', 'played', 'playing', 'read', 'reading', 'unread', "
                "'want_to_listen', 'want_to_play', 'want_to_read', 'want_to_watch', 'watched', 'watching')",
            )
        if "ck_items_collection_status" not in item_checks:
            batch_op.create_check_constraint(
                "ck_items_collection_status",
                "collection_status IN ('wish_list', 'ordered', 'available', 'lent', 'damaged', 'lost')",
            )

    uwi_checks = {c["name"] for c in inspector.get_check_constraints("user_work_intents", schema=s_inv)}
    if "ck_user_work_intents_status" not in uwi_checks:
        with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
            batch_op.create_check_constraint(
                "ck_user_work_intents_status",
                "status IN ('dnf', 'fulfilled', 'listened', 'listening', 'played', 'playing', 'read', 'reading', 'unread', "
                "'want_to_listen', 'want_to_play', 'want_to_read', 'want_to_watch', 'watched', 'watching')",
            )

    loan_checks = {c["name"] for c in inspector.get_check_constraints("loan_requests", schema=s_inv)}
    if "ck_loan_requests_status" not in loan_checks:
        with op.batch_alter_table("loan_requests", schema=s_inv) as batch_op:
            batch_op.create_check_constraint(
                "ck_loan_requests_status",
                "status IN ('pending', 'approved', 'rejected')",
            )

    # 4. UserCollection parent_id FK update to SET NULL on delete
    if is_pg:
        fks = inspector.get_foreign_keys("user_collections", schema=s_inv)
        parent_fk_name = None
        for fk in fks:
            if "parent_id" in fk.get("constrained_columns", []):
                parent_fk_name = fk.get("name")
                break

        if parent_fk_name:
            op.drop_constraint(parent_fk_name, "user_collections", type_="foreignkey", schema=s_inv)
        op.create_foreign_key(
            "user_collections_parent_id_fkey",
            "user_collections",
            "user_collections",
            ["parent_id"],
            ["id"],
            source_schema=s_inv,
            referent_schema=s_inv,
            ondelete="SET NULL",
        )


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)

    s_auth = "auth" if is_pg else None
    s_cat = "catalog" if is_pg else None
    s_inv = "inventory" if is_pg else None
    s_cfg = "config" if is_pg else None

    # 1. Revert user_collections parent_id FK to CASCADE
    if is_pg:
        fks = inspector.get_foreign_keys("user_collections", schema=s_inv)
        parent_fk_name = None
        for fk in fks:
            if "parent_id" in fk.get("constrained_columns", []):
                parent_fk_name = fk.get("name")
                break

        if parent_fk_name:
            op.drop_constraint(parent_fk_name, "user_collections", type_="foreignkey", schema=s_inv)
        op.create_foreign_key(
            "user_collections_parent_id_fkey",
            "user_collections",
            "user_collections",
            ["parent_id"],
            ["id"],
            source_schema=s_inv,
            referent_schema=s_inv,
            ondelete="CASCADE",
        )

    # 2. Drop check constraints
    loan_checks = {c["name"] for c in inspector.get_check_constraints("loan_requests", schema=s_inv)}
    if "ck_loan_requests_status" in loan_checks:
        with op.batch_alter_table("loan_requests", schema=s_inv) as batch_op:
            batch_op.drop_constraint("ck_loan_requests_status", type_="check")

    uwi_checks = {c["name"] for c in inspector.get_check_constraints("user_work_intents", schema=s_inv)}
    if "ck_user_work_intents_status" in uwi_checks:
        with op.batch_alter_table("user_work_intents", schema=s_inv) as batch_op:
            batch_op.drop_constraint("ck_user_work_intents_status", type_="check")

    item_checks = {c["name"] for c in inspector.get_check_constraints("items", schema=s_inv)}
    with op.batch_alter_table("items", schema=s_inv) as batch_op:
        if "ck_items_collection_status" in item_checks:
            batch_op.drop_constraint("ck_items_collection_status", type_="check")
        if "ck_items_status" in item_checks:
            batch_op.drop_constraint("ck_items_status", type_="check")

    user_checks = {c["name"] for c in inspector.get_check_constraints("users", schema=s_auth)}
    if "ck_users_visibility" in user_checks:
        with op.batch_alter_table("users", schema=s_auth) as batch_op:
            batch_op.drop_constraint("ck_users_visibility", type_="check")

    # 3. Drop expires_at column and index
    tbl_cols = [c["name"] for c in inspector.get_columns("token_blocklist", schema=s_auth)]
    if "expires_at" in tbl_cols:
        with op.batch_alter_table("token_blocklist", schema=s_auth) as batch_op:
            indexes = [idx["name"] for idx in inspector.get_indexes("token_blocklist", schema=s_auth)]
            if "ix_auth_token_blocklist_expires_at" in indexes:
                batch_op.drop_index("ix_auth_token_blocklist_expires_at")
            batch_op.drop_column("expires_at")

    # 4. Move instance_settings back to catalog schema and drop config schema
    if is_pg:
        if inspector.has_table("instance_settings", schema=s_cfg):
            op.execute(
                "ALTER INDEX IF EXISTS config.ix_config_instance_settings_key "
                "RENAME TO ix_catalog_instance_settings_key"
            )
            op.execute("ALTER TABLE config.instance_settings SET SCHEMA catalog")
        op.execute("DROP SCHEMA IF EXISTS config CASCADE")
