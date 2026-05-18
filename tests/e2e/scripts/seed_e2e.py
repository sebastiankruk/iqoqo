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
"""
Seed E2E data for Playwright tests.
"""

from dotenv import load_dotenv

# Load .env before importing any app models so that SCHEMA assignments (like auth.users)
# are correctly evaluated based on the DATABASE_URL.
load_dotenv()

from app import create_app  # noqa: E402
from app.db import db  # noqa: E402
from app.db.models import Expression, Item, Manifestation, Role, User, Work  # noqa: E402


def seed_e2e_data():
    app = create_app()
    with app.app_context():
        # ── Dedicated E2E admin with stable credentials ────────────────────────
        # Always upserted so tests work in the live local DB (VS Code /
        # Antigravity) as well as after a full db-reset (make test-e2e).
        E2E_EMAIL = "e2e-admin@iqoqo.local"
        E2E_PASSWORD = "E2ETestPassword123!"
        admin_role = Role.query.filter_by(name="admin").first()
        e2e_admin = User.query.filter_by(email=E2E_EMAIL).first()
        if not e2e_admin:
            e2e_admin = User(
                email=E2E_EMAIL,
                display_name="E2E Admin",
                public_username="e2e_admin",
                is_active=True,
            )
            e2e_admin.set_password(E2E_PASSWORD)
            if admin_role:
                e2e_admin.roles.append(admin_role)  # type: ignore[attr-defined]
            db.session.add(e2e_admin)
        else:
            # Always reset to known password so VS-Code runs stay stable
            e2e_admin.set_password(E2E_PASSWORD)
            e2e_admin.is_active = True
            if admin_role and admin_role not in e2e_admin.roles:  # type: ignore[operator]
                e2e_admin.roles.append(admin_role)  # type: ignore[attr-defined]
        db.session.commit()

        # Create privateuser
        private_user = User.query.filter_by(public_username="privateuser").first()
        if not private_user:
            private_user = User(
                email="private@example.com", display_name="Private User", public_username="privateuser", visibility="private"
            )
            db.session.add(private_user)
        else:
            private_user.visibility = "private"

        # Create testuser
        test_user = User.query.filter_by(public_username="testuser").first()
        if not test_user:
            test_user = User(email="test@example.com", display_name="Test User", public_username="testuser", visibility="public")
            db.session.add(test_user)
        else:
            test_user.visibility = "public"

        # Create emptyuser
        empty_user = User.query.filter_by(public_username="emptyuser").first()
        if not empty_user:
            empty_user = User(email="empty@example.com", display_name="Empty User", public_username="emptyuser", visibility="public")
            db.session.add(empty_user)
        else:
            empty_user.visibility = "public"

        db.session.commit()

        # Add items for testuser
        # We need at least one manifestation
        m = Manifestation.query.first()
        if not m:
            print("No manifestations found, run db-init first")
            return

        # Public Item
        public_item = Item.query.filter_by(owner_id=test_user.id, is_hidden=False).first()
        if not public_item:
            # Try to find or create a manifestation with "Public Treasure" title
            # Actually, the test looks for TEXT "Public Treasure"
            # The CollectionGrid probably renders manifestation titles.

            # Let's update manifestation title or create new one
            w_public = Work(title="Public Treasure")
            db.session.add(w_public)
            db.session.flush()
            e_public = Expression(work_id=w_public.id, content_type="text", language="en")
            db.session.add(e_public)
            db.session.flush()
            m_public = Manifestation(expression_id=e_public.id, isbn13="1111111111111")
            db.session.add(m_public)
            db.session.flush()

            public_item = Item(owner_id=test_user.id, manifestation_id=m_public.id, is_hidden=False, status="available")
            db.session.add(public_item)

        # Hidden Item
        hidden_item = Item.query.filter_by(owner_id=test_user.id, is_hidden=True).first()
        if not hidden_item:
            w_hidden = Work(title="Hidden Treasure")
            db.session.add(w_hidden)
            db.session.flush()
            e_hidden = Expression(work_id=w_hidden.id, content_type="text", language="en")
            db.session.add(e_hidden)
            db.session.flush()
            m_hidden = Manifestation(expression_id=e_hidden.id, isbn13="2222222222222")
            db.session.add(m_hidden)
            db.session.flush()

            hidden_item = Item(owner_id=test_user.id, manifestation_id=m_hidden.id, is_hidden=True, status="available")
            db.session.add(hidden_item)

        db.session.commit()
        print("E2E seed data created successfully")


if __name__ == "__main__":
    seed_e2e_data()
