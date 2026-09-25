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
"""Tighten visibility and authentication constraints and validate aggregations.

Revision ID: v0_8_1_security_constraints
Revises: v0_8_1_lending_self_borrow
"""

import sqlalchemy as sa
from alembic import op

revision = "v0_8_1_security_constraints"
down_revision = "v0_8_1_lending_self_borrow"
branch_labels = None
depends_on = None


def _schema_names(bind):
    is_pg = bind.dialect.name == "postgresql"
    return ("auth" if is_pg else None, "catalog" if is_pg else None)


def _table_name(schema, table):
    return f"{schema}.{table}" if schema else table


def upgrade():
    bind = op.get_bind()
    auth_schema, catalog_schema = _schema_names(bind)
    inspector = sa.inspect(bind)

    # Fail closed rather than inventing credentials or silently deleting accounts.
    users_table = _table_name(auth_schema, "users")
    users_without_auth = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {users_table} WHERE password_hash IS NULL AND google_id IS NULL")
    ).scalar_one()
    if users_without_auth:
        raise RuntimeError(
            f"Cannot add check_user_auth_method: {users_without_auth} user account(s) have no password or Google identity; "
            "repair those accounts before upgrading."
        )

    user_checks = {check["name"] for check in inspector.get_check_constraints("users", schema=auth_schema)}
    with op.batch_alter_table("users", schema=auth_schema) as batch_op:
        if "ck_users_visibility" in user_checks:
            batch_op.drop_constraint("ck_users_visibility", type_="check")
        if "check_user_visibility" not in user_checks:
            batch_op.create_check_constraint("check_user_visibility", "visibility IN ('private', 'shared', 'public')")
        if "check_user_auth_method" not in user_checks:
            batch_op.create_check_constraint("check_user_auth_method", "password_hash IS NOT NULL OR google_id IS NOT NULL")

    aggregation_table = _table_name(catalog_schema, "container_aggregations")
    invalid_aggregations = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {aggregation_table} WHERE aggregated_type NOT IN ('work', 'item')")
    ).scalar_one()
    if invalid_aggregations:
        raise RuntimeError(
            f"Cannot add check_container_aggregation_type: {invalid_aggregations} container aggregation(s) have an invalid target type."
        )

    aggregation_checks = {
        check["name"] for check in inspector.get_check_constraints("container_aggregations", schema=catalog_schema)
    }
    if "check_container_aggregation_type" not in aggregation_checks:
        with op.batch_alter_table("container_aggregations", schema=catalog_schema) as batch_op:
            batch_op.create_check_constraint("check_container_aggregation_type", "aggregated_type IN ('work', 'item')")


def downgrade():
    bind = op.get_bind()
    auth_schema, catalog_schema = _schema_names(bind)

    shared_users = bind.execute(sa.text(f"SELECT COUNT(*) FROM {_table_name(auth_schema, 'users')} WHERE visibility = 'shared'")).scalar_one()
    if shared_users:
        raise RuntimeError("Cannot restore the previous visibility constraint while shared-visibility users exist.")

    user_checks = {check["name"] for check in sa.inspect(bind).get_check_constraints("users", schema=auth_schema)}
    with op.batch_alter_table("users", schema=auth_schema) as batch_op:
        if "check_user_auth_method" in user_checks:
            batch_op.drop_constraint("check_user_auth_method", type_="check")
        if "check_user_visibility" in user_checks:
            batch_op.drop_constraint("check_user_visibility", type_="check")
        if "ck_users_visibility" not in user_checks:
            batch_op.create_check_constraint("ck_users_visibility", "visibility IN ('public', 'private')")

    aggregation_checks = {
        check["name"] for check in sa.inspect(bind).get_check_constraints("container_aggregations", schema=catalog_schema)
    }
    if "check_container_aggregation_type" in aggregation_checks:
        with op.batch_alter_table("container_aggregations", schema=catalog_schema) as batch_op:
            batch_op.drop_constraint("check_container_aggregation_type", type_="check")
