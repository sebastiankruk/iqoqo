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

    is_pg = bind.dialect.name == "postgresql"
    users_table = _table_name(auth_schema, "users")

    # Clean up or lock the transitional legacy system user (00000000-0000-4000-a000-000000000000 / legacy@iqoqo.cc)
    # seeded by 2973a4475ace_add_user_profiles_auth_and_rbac during v0.2.0 before authentication constraints existed.
    legacy_user_id = "00000000-0000-4000-a000-000000000000"

    def _legacy_has_items() -> bool:
        """Whether the legacy user still owns anything.

        A failure here must not be read as "owns nothing". `auth.users.owner_id`
        references cascade (`Item.owner_id` is `ondelete="CASCADE"`), so
        concluding that a user owns nothing and deleting their row would take
        their entire collection with it. The original code caught `Exception`
        and defaulted to `False`, which made every transient error -- a dropped
        connection, a permission problem, a typo -- destructive.

        Failing closed matches the pattern the same migration uses twenty lines
        below for `check_user_auth_method`, and it is the only safe direction:
        a false negative merely disables the account, which is reversible.

        @returns: True when the legacy user owns at least one row.
        @raises RuntimeError: If the check cannot be performed.
        """
        if is_pg:
            sql = sa.text(f"SELECT 1 FROM inventory.items WHERE owner_id::text = '{legacy_user_id}' LIMIT 1")
        else:
            sql = sa.text(
                f"SELECT 1 FROM items WHERE (owner_id = '{legacy_user_id}' OR owner_id IN "
                f"(SELECT id FROM {users_table} WHERE email = 'legacy@iqoqo.cc')) LIMIT 1"
            )
        try:
            return bool(bind.execute(sql).scalar())
        except Exception as exc:
            raise RuntimeError(
                "Cannot determine whether the legacy system user owns items, so the migration "
                "refuses to decide between deleting and disabling that account. Re-run once "
                "inventory.items is readable; nothing has been changed."
            ) from exc

    has_items = _legacy_has_items()

    if is_pg:
        if not has_items:
            bind.execute(
                sa.text(
                    f"DELETE FROM {users_table} WHERE (id::text = '{legacy_user_id}' OR email = 'legacy@iqoqo.cc') "
                    "AND password_hash IS NULL AND google_id IS NULL"
                )
            )
        else:
            bind.execute(
                sa.text(
                    f"UPDATE {users_table} SET password_hash = '!disabled', is_active = false "
                    f"WHERE (id::text = '{legacy_user_id}' OR email = 'legacy@iqoqo.cc') "
                    "AND password_hash IS NULL AND google_id IS NULL"
                )
            )
    else:
        if not has_items:
            bind.execute(
                sa.text(
                    f"DELETE FROM {users_table} WHERE email = 'legacy@iqoqo.cc' "
                    "AND password_hash IS NULL AND google_id IS NULL"
                )
            )
        else:
            user_cols = {col["name"] for col in inspector.get_columns("users")}
            if "is_active" in user_cols:
                bind.execute(
                    sa.text(
                        f"UPDATE {users_table} SET password_hash = '!disabled', is_active = 0 "
                        "WHERE email = 'legacy@iqoqo.cc' "
                        "AND password_hash IS NULL AND google_id IS NULL"
                    )
                )
            else:
                bind.execute(
                    sa.text(
                        f"UPDATE {users_table} SET password_hash = '!disabled' "
                        "WHERE email = 'legacy@iqoqo.cc' "
                        "AND password_hash IS NULL AND google_id IS NULL"
                    )
                )

    # Fail closed rather than inventing credentials or silently deleting accounts.
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
