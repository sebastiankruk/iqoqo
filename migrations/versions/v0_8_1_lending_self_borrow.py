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
"""Enforce the lending self-borrow invariant at the database boundary.

Revision ID: v0_8_1_lending_self_borrow
Revises: v0_8_1_frbr_relation_management
"""

from alembic import op

revision = "v0_8_1_lending_self_borrow"
down_revision = "v0_8_1_frbr_relation_management"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("""
        CREATE OR REPLACE FUNCTION inventory.prevent_self_borrow_loan_request()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            item_owner uuid;
        BEGIN
            SELECT item.owner_id
              INTO item_owner
              FROM inventory.items AS item
             WHERE item.id = NEW.item_id
             FOR SHARE;

            IF item_owner IS NOT NULL AND item_owner = NEW.requester_id THEN
                RAISE EXCEPTION 'Cannot request to loan your own item'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'loan_requests_not_self_borrow';
            END IF;

            RETURN NEW;
        END;
        $function$
        """)
    op.execute("""
        CREATE TRIGGER trg_loan_requests_prevent_self_borrow
        BEFORE INSERT OR UPDATE ON inventory.loan_requests
        FOR EACH ROW
        EXECUTE FUNCTION inventory.prevent_self_borrow_loan_request()
        """)


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("DROP TRIGGER IF EXISTS trg_loan_requests_prevent_self_borrow ON inventory.loan_requests")
    op.execute("DROP FUNCTION IF EXISTS inventory.prevent_self_borrow_loan_request()")
