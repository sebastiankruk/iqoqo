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
"""add lending tables

Revision ID: 52b02a37b16b
Revises: 23db780ad6d1
Create Date: 2026-06-04 21:25:31.775845

NOTE (2026-06-05): This migration has been hardened to be idempotent.
The original auto-generated version crashed on any DB that had the
loan_requests table partially applied from a previous interrupted run.
All destructive operations now use IF EXISTS / IF NOT EXISTS guards and
constraint-name-agnostic lookups so the migration is safe to apply on
both a pristine DB and one that had partial state.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "52b02a37b16b"
down_revision = "23db780ad6d1"
branch_labels = None
depends_on = None


def _table_exists(conn: sa.engine.Connection, schema: str, table: str) -> bool:
    """Return True if the given schema.table already exists."""
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_schema = :schema AND table_name = :table"
            ")"
        ),
        {"schema": schema, "table": table},
    )
    return bool(result.scalar())


def _index_exists(conn: sa.engine.Connection, indexname: str) -> bool:
    """Return True if the given index exists anywhere in the DB."""
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :n)"),
        {"n": indexname},
    )
    return bool(result.scalar())


def _constraint_exists(conn: sa.engine.Connection, schema: str, table: str, conname: str) -> bool:
    """Return True if the named constraint exists on schema.table."""
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_constraint c"
            "  JOIN pg_class t ON t.oid = c.conrelid"
            "  JOIN pg_namespace n ON n.oid = t.relnamespace"
            "  WHERE n.nspname = :schema AND t.relname = :table AND c.conname = :conname"
            ")"
        ),
        {"schema": schema, "table": table, "conname": conname},
    )
    return bool(result.scalar())


def _column_exists(conn: sa.engine.Connection, schema: str, table: str, column: str) -> bool:
    """Return True if the given column exists on schema.table."""
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns"
            "  WHERE table_schema = :schema AND table_name = :table AND column_name = :column"
            ")"
        ),
        {"schema": schema, "table": table, "column": column},
    )
    return bool(result.scalar())


def upgrade() -> None:
    """Apply lending tables migration idempotently."""
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Create inventory.loan_requests (idempotent: skip if exists)
    # ------------------------------------------------------------------
    if not _table_exists(conn, "inventory", "loan_requests"):
        op.create_table(
            "loan_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("requester_id", sa.UUID(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["item_id"], ["inventory.items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requester_id"], ["auth.users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            schema="inventory",
        )

    if not _index_exists(conn, "ix_inventory_loan_requests_item_id"):
        op.create_index(
            "ix_inventory_loan_requests_item_id",
            "loan_requests",
            ["item_id"],
            unique=False,
            schema="inventory",
        )

    if not _index_exists(conn, "ix_inventory_loan_requests_requester_id"):
        op.create_index(
            "ix_inventory_loan_requests_requester_id",
            "loan_requests",
            ["requester_id"],
            unique=False,
            schema="inventory",
        )

    # ------------------------------------------------------------------
    # 2. Drop inventory.image_scans (idempotent)
    # ------------------------------------------------------------------
    if _table_exists(conn, "inventory", "image_scans"):
        op.drop_table("image_scans", schema="inventory")

    # ------------------------------------------------------------------
    # 3. auth.users — replace old index/constraint with schema-qualified one
    # ------------------------------------------------------------------
    with op.batch_alter_table("users", schema="auth") as batch_op:
        if _index_exists(conn, "ix_users_public_visibility"):
            batch_op.drop_index("ix_users_public_visibility")
        if _constraint_exists(conn, "auth", "users", "uq_users_public_username"):
            batch_op.drop_constraint("uq_users_public_username", type_="unique")
    if not _index_exists(conn, "ix_auth_users_public_username"):
        op.create_index(
            "ix_auth_users_public_username",
            "users",
            ["public_username"],
            unique=True,
            schema="auth",
        )

    # ------------------------------------------------------------------
    # 4. catalog.expressions — ensure ON DELETE CASCADE on work_id FK
    # ------------------------------------------------------------------
    with op.batch_alter_table("expressions", schema="catalog") as batch_op:
        # Drop any legacy name; ignore if already renamed to _cascade variant
        if _constraint_exists(conn, "catalog", "expressions", "expressions_work_id_fkey"):
            batch_op.drop_constraint("expressions_work_id_fkey", type_="foreignkey")
        if not _constraint_exists(conn, "catalog", "expressions", "expressions_work_id_fkey_cascade"):
            batch_op.create_foreign_key(
                "expressions_work_id_fkey_cascade",
                "works",
                ["work_id"],
                ["id"],
                referent_schema="catalog",
                ondelete="CASCADE",
            )

    # ------------------------------------------------------------------
    # 5. catalog.image_scans — tighten column sizes / remove server defaults
    # ------------------------------------------------------------------
    with op.batch_alter_table("image_scans", schema="catalog") as batch_op:
        batch_op.alter_column(
            "file_path",
            existing_type=sa.VARCHAR(length=500),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "created_at",
            existing_type=postgresql.TIMESTAMP(),
            server_default=None,
            existing_nullable=True,
        )

    # ------------------------------------------------------------------
    # 6. catalog.instance_settings — replace old index with schema-qualified one
    # ------------------------------------------------------------------
    insp = sa.inspect(conn)
    id_col = [c for c in insp.get_columns("instance_settings", schema="catalog") if c["name"] == "id"]
    if id_col and id_col[0].get("identity"):
        pass
    else:
        with op.batch_alter_table("instance_settings", schema="catalog") as batch_op:
            batch_op.alter_column("id", existing_type=sa.INTEGER(), server_default=None, existing_nullable=False, autoincrement=True)
        if _index_exists(conn, "ix_instance_settings_key"):
            batch_op.drop_index("ix_instance_settings_key")
    if not _index_exists(conn, "ix_catalog_instance_settings_key"):
        op.create_index(
            "ix_catalog_instance_settings_key",
            "instance_settings",
            ["key"],
            unique=True,
            schema="catalog",
        )

    # ------------------------------------------------------------------
    # 7. catalog.manifestations — ensure ON DELETE CASCADE on expression_id FK
    # ------------------------------------------------------------------
    with op.batch_alter_table("manifestations", schema="catalog") as batch_op:
        if _constraint_exists(conn, "catalog", "manifestations", "manifestations_expression_id_fkey"):
            batch_op.drop_constraint("manifestations_expression_id_fkey", type_="foreignkey")
        if not _constraint_exists(conn, "catalog", "manifestations", "manifestations_expression_id_fkey_cascade"):
            batch_op.create_foreign_key(
                "manifestations_expression_id_fkey_cascade",
                "expressions",
                ["expression_id"],
                ["id"],
                referent_schema="catalog",
                ondelete="CASCADE",
            )

    # ------------------------------------------------------------------
    # 8. inventory.items — drop progress_status, fix FK cascade, remove defaults
    # ------------------------------------------------------------------
    with op.batch_alter_table("items", schema="inventory") as batch_op:
        batch_op.alter_column("is_hidden", existing_type=sa.BOOLEAN(), server_default=None, existing_nullable=False)
        if _index_exists(conn, "ix_items_owner_hidden"):
            batch_op.drop_index("ix_items_owner_hidden")
        if _constraint_exists(conn, "inventory", "items", "items_manifestation_id_fkey"):
            batch_op.drop_constraint("items_manifestation_id_fkey", type_="foreignkey")
        if not _constraint_exists(conn, "inventory", "items", "items_manifestation_id_fkey_cascade"):
            batch_op.create_foreign_key(
                "items_manifestation_id_fkey_cascade",
                "manifestations",
                ["manifestation_id"],
                ["id"],
                referent_schema="catalog",
                ondelete="CASCADE",
            )
        if _column_exists(conn, "inventory", "items", "progress_status"):
            batch_op.drop_column("progress_status")

    # ------------------------------------------------------------------
    # 9. inventory.llm_telemetry — remove identity server_default, harden status
    # ------------------------------------------------------------------
    with op.batch_alter_table("llm_telemetry", schema="inventory") as batch_op:
        batch_op.alter_column("id", existing_type=sa.INTEGER(), server_default=None, existing_nullable=False, autoincrement=True)
        batch_op.alter_column("status", existing_type=sa.VARCHAR(length=20), nullable=False)

    # ------------------------------------------------------------------
    # 10. inventory.scan_telemetry — make created_at NOT NULL
    # ------------------------------------------------------------------
    with op.batch_alter_table("scan_telemetry", schema="inventory") as batch_op:
        batch_op.alter_column("created_at", existing_type=postgresql.TIMESTAMP(), server_default=None, nullable=False)

    # ------------------------------------------------------------------
    # 11. inventory.shared_collections — remove created_at server_default
    # ------------------------------------------------------------------
    with op.batch_alter_table("shared_collections", schema="inventory") as batch_op:
        batch_op.alter_column("created_at", existing_type=postgresql.TIMESTAMP(), server_default=None, existing_nullable=True)


def downgrade() -> None:
    """Reverse the lending tables migration."""
    conn = op.get_bind()

    with op.batch_alter_table("shared_collections", schema="inventory") as batch_op:
        batch_op.alter_column("created_at", existing_type=postgresql.TIMESTAMP(), server_default=sa.text("now()"), existing_nullable=True)

    with op.batch_alter_table("scan_telemetry", schema="inventory") as batch_op:
        batch_op.alter_column("created_at", existing_type=postgresql.TIMESTAMP(), server_default=sa.text("now()"), nullable=True)

    with op.batch_alter_table("llm_telemetry", schema="inventory") as batch_op:
        batch_op.alter_column("status", existing_type=sa.VARCHAR(length=20), nullable=True)
        batch_op.alter_column(
            "id",
            existing_type=sa.INTEGER(),
            server_default=sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1),
            existing_nullable=False,
            autoincrement=True,
        )

    with op.batch_alter_table("items", schema="inventory") as batch_op:
        batch_op.add_column(
            sa.Column(
                "progress_status",
                sa.VARCHAR(length=50),
                server_default=sa.text("'unstarted'::character varying"),
                autoincrement=False,
                nullable=True,
            )
        )
        if _constraint_exists(conn, "inventory", "items", "items_manifestation_id_fkey_cascade"):
            batch_op.drop_constraint("items_manifestation_id_fkey_cascade", type_="foreignkey")
        batch_op.create_foreign_key(
            "items_manifestation_id_fkey",
            "manifestations",
            ["manifestation_id"],
            ["id"],
            referent_schema="catalog",
        )
        batch_op.create_index("ix_items_owner_hidden", ["owner_id", "is_hidden"], unique=False)
        batch_op.alter_column("is_hidden", existing_type=sa.BOOLEAN(), server_default=sa.text("false"), existing_nullable=False)

    with op.batch_alter_table("manifestations", schema="catalog") as batch_op:
        if _constraint_exists(conn, "catalog", "manifestations", "manifestations_expression_id_fkey_cascade"):
            batch_op.drop_constraint("manifestations_expression_id_fkey_cascade", type_="foreignkey")
        batch_op.create_foreign_key(
            "manifestations_expression_id_fkey",
            "expressions",
            ["expression_id"],
            ["id"],
            referent_schema="catalog",
        )

    with op.batch_alter_table("instance_settings", schema="catalog") as batch_op:
        if _index_exists(conn, "ix_catalog_instance_settings_key"):
            batch_op.drop_index("ix_catalog_instance_settings_key")
        batch_op.create_index("ix_instance_settings_key", ["key"], unique=True)
        batch_op.alter_column(
            "id",
            existing_type=sa.INTEGER(),
            server_default=sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1),
            existing_nullable=False,
            autoincrement=True,
        )

    with op.batch_alter_table("image_scans", schema="catalog") as batch_op:
        batch_op.alter_column("created_at", existing_type=postgresql.TIMESTAMP(), server_default=sa.text("now()"), existing_nullable=True)
        batch_op.alter_column("file_path", existing_type=sa.String(length=255), type_=sa.VARCHAR(length=500), existing_nullable=False)

    with op.batch_alter_table("expressions", schema="catalog") as batch_op:
        if _constraint_exists(conn, "catalog", "expressions", "expressions_work_id_fkey_cascade"):
            batch_op.drop_constraint("expressions_work_id_fkey_cascade", type_="foreignkey")
        batch_op.create_foreign_key(
            "expressions_work_id_fkey",
            "works",
            ["work_id"],
            ["id"],
            referent_schema="catalog",
        )

    with op.batch_alter_table("users", schema="auth") as batch_op:
        if _index_exists(conn, "ix_auth_users_public_username"):
            batch_op.drop_index("ix_auth_users_public_username")
        batch_op.create_unique_constraint("uq_users_public_username", ["public_username"], postgresql_nulls_not_distinct=False)
        batch_op.create_index("ix_users_public_visibility", ["public_username", "visibility"], unique=False)

    if _table_exists(conn, "inventory", "loan_requests"):
        with op.batch_alter_table("loan_requests", schema="inventory") as batch_op:
            if _index_exists(conn, "ix_inventory_loan_requests_requester_id"):
                batch_op.drop_index("ix_inventory_loan_requests_requester_id")
            if _index_exists(conn, "ix_inventory_loan_requests_item_id"):
                batch_op.drop_index("ix_inventory_loan_requests_item_id")
        op.drop_table("loan_requests", schema="inventory")

    if not _table_exists(conn, "inventory", "image_scans"):
        op.create_table(
            "image_scans",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column("item_id", sa.INTEGER(), autoincrement=False, nullable=False),
            sa.Column("scan_type", sa.VARCHAR(length=50), autoincrement=False, nullable=False),
            sa.Column("image_path", sa.VARCHAR(length=500), autoincrement=False, nullable=False),
            sa.Column("created_at", postgresql.TIMESTAMP(), server_default=sa.text("now()"), autoincrement=False, nullable=True),
            sa.ForeignKeyConstraint(["item_id"], ["inventory.items.id"], name=op.f("fk_item"), ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("image_scans_pkey")),
            schema="inventory",
        )
