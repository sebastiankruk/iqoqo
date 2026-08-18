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

import os  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app import create_app  # noqa: E402
from app.db import db  # noqa: E402
from app.db.models import Expression, InstanceSettings, Item, Manifestation, Role, SharedCollection, User, Work  # noqa: E402
from app.utils.covers import COVERS_DIR, add_center_watermark  # noqa: E402
from app.utils.llm_covers import apply_corner_watermark  # noqa: E402


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

        # ── Dedicated E2E lender and borrower for lending lifecycle tests ──────
        LENDER_EMAIL = "lender@iqoqo.local"
        BORROWER_EMAIL = "borrower@iqoqo.local"
        E2E_SHARED_PASSWORD = "SecurePassword123!"

        try:
            lender = User.query.filter_by(email=LENDER_EMAIL).first()
            if not lender:
                lender = User(
                    email=LENDER_EMAIL,
                    display_name="Lender",
                    public_username="lender",
                    visibility="public",
                    is_active=True,
                )
                lender.set_password(E2E_SHARED_PASSWORD)
                db.session.add(lender)
            else:
                lender.public_username = "lender"
                lender.visibility = "public"
                lender.set_password(E2E_SHARED_PASSWORD)
                lender.is_active = True

            # Flush so lender.id is assigned before any filter_by(owner_id=lender.id) queries.
            db.session.flush()

            borrower = User.query.filter_by(email=BORROWER_EMAIL).first()
            if not borrower:
                borrower = User(email=BORROWER_EMAIL, display_name="Borrower", is_active=True)
                borrower.set_password(E2E_SHARED_PASSWORD)
                db.session.add(borrower)
            else:
                borrower.set_password(E2E_SHARED_PASSWORD)
                borrower.is_active = True

            db.session.flush()

            # Give lender some items so the lending test has items to request.
            # collection_status must be 'available' so the public API can surface them.
            # status must be a *progress* status (e.g. 'want_to_read'), NOT 'available'.
            if Item.query.filter_by(owner_id=lender.id).count() == 0:
                w_lend = Work(title="Lendable Book", meta={"authors": ["Lender Author"]})
                db.session.add(w_lend)
                db.session.flush()
                e_lend = Expression(work_id=w_lend.id, content_type="text", language="en")
                db.session.add(e_lend)
                db.session.flush()
                m_lend = Manifestation(expression_id=e_lend.id, isbn13="4444444444444")
                db.session.add(m_lend)
                db.session.flush()
                for _ in range(3):
                    item = Item(
                        owner_id=lender.id,
                        manifestation_id=m_lend.id,
                        is_hidden=False,
                        # 'status' is a progress status (reading/want_to_read/…), NOT collection_status
                        status="want_to_read",
                        collection_status="available",
                    )
                    db.session.add(item)
            else:
                # Always reset collection_status to available and clear stale loan state
                for item in Item.query.filter_by(owner_id=lender.id).all():
                    item.collection_status = "available"
                    item.status = "want_to_read"
                    item.lent_to_user_id = None
                    db.session.add(item)

            # Clean up stale loan requests from previous test runs
            from app.db.lending import LoanRequest  # noqa: E402

            lender_item_ids = [i.id for i in Item.query.filter_by(owner_id=lender.id).all()]
            if lender_item_ids:
                LoanRequest.query.filter(LoanRequest.item_id.in_(lender_item_ids)).delete(synchronize_session=False)

            db.session.commit()
        except (SQLAlchemyError, ValueError, AttributeError, KeyError, RuntimeError) as exc:
            db.session.rollback()
            print(f"WARNING: lender/borrower seed failed (non-fatal): {exc}")

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

        # Create items for e2e-admin to populate the shared wishlist
        if Item.query.filter_by(owner_id=e2e_admin.id).count() == 0:
            w_shared = Work(title="Shared Wishlist Book")
            db.session.add(w_shared)
            db.session.flush()
            e_shared = Expression(work_id=w_shared.id, content_type="text", language="en")
            db.session.add(e_shared)
            db.session.flush()
            m_shared = Manifestation(expression_id=e_shared.id, isbn13="5555555555555")
            db.session.add(m_shared)
            db.session.flush()
            shared_item = Item(
                owner_id=e2e_admin.id, manifestation_id=m_shared.id, is_hidden=False, status="available", collection_status="wish_list"
            )
            db.session.add(shared_item)

        # Create SharedCollection for the token-based wishlist test
        SHARE_TOKEN = "wishlist-token-xyz-7890"
        existing = SharedCollection.query.filter_by(share_token=SHARE_TOKEN).first()
        if not existing:
            shared_coll = SharedCollection(
                user_id=e2e_admin.id,
                share_token=SHARE_TOKEN,
                name="E2E Wishlist",
                description="Shared wishlist for E2E token-based sharing tests",
                filters={"status": "wish_list"},
            )
            db.session.add(shared_coll)

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

        # Seed global Fiction/Atlantic novel that has no user-owned items
        global_work_stmt = select(Work).filter(Work.title == "Global Fiction Novel")
        global_work = db.session.execute(global_work_stmt).scalar_one_or_none()
        if not global_work:
            global_work = Work(
                title="Global Fiction Novel",
                meta={"genres": ["Fiction"], "authors": ["Atlantic Author"]},
            )
            db.session.add(global_work)
            db.session.flush()
            global_expr = Expression(
                work_id=global_work.id,
                content_type="text",
                language="en",
            )
            db.session.add(global_expr)
            db.session.flush()
            global_manif = Manifestation(
                expression_id=global_expr.id,
                isbn13="9999999999999",
                publisher="Atlantic",
                cover_url="https://images.unsplash.com/photo-1543002588-bfa74002ed7e",
            )
            db.session.add(global_manif)
            db.session.flush()

        # ── Roadmap E2E test data ───────────────────────────────────────────────
        # Seed two books that the roadmap E2E test searches for by title.
        ddia_stmt = select(Work).filter(Work.title == "Designing Data-Intensive Applications")
        ddia_work = db.session.execute(ddia_stmt).scalar_one_or_none()
        if not ddia_work:
            ddia_work = Work(
                title="Designing Data-Intensive Applications",
                meta={"authors": ["Martin Kleppmann"]},
            )
            db.session.add(ddia_work)
            db.session.flush()
            ddia_expr = Expression(work_id=ddia_work.id, content_type="text", language="en")
            db.session.add(ddia_expr)
            db.session.flush()
            ddia_manif = Manifestation(expression_id=ddia_expr.id, isbn13="9781491903629")
            db.session.add(ddia_manif)
            db.session.flush()

        dist_sys_stmt = select(Work).filter(Work.title == "Distributed Systems: Principles and Paradigms")
        dist_sys_work = db.session.execute(dist_sys_stmt).scalar_one_or_none()
        if not dist_sys_work:
            dist_sys_work = Work(
                title="Distributed Systems: Principles and Paradigms",
                meta={"authors": ["Andrew S. Tanenbaum", "Maarten Van Steen"]},
            )
            db.session.add(dist_sys_work)
            db.session.flush()
            dist_sys_expr = Expression(work_id=dist_sys_work.id, content_type="text", language="en")
            db.session.add(dist_sys_expr)
            db.session.flush()
            dist_sys_manif = Manifestation(expression_id=dist_sys_expr.id, isbn13="9780132392273")
            db.session.add(dist_sys_manif)
            db.session.flush()

        # ── Watermark E2E test covers ────────────────────────────────────────────
        watermark_asset = os.getenv("IQOQO_WATERMARK_PATH", "resources/images/iqoqo-logo.png")
        if os.path.exists(watermark_asset):
            PH_ISBN = "6000000000001"
            LLM_ISBN = "6000000000002"

            # Placeholder cover manifestation
            placeholder_manif = Manifestation.query.filter_by(isbn13=PH_ISBN).first()
            if not placeholder_manif:
                w_ph = Work(title="Watermark Placeholder Cover", meta={"authors": ["E2E System"]})
                db.session.add(w_ph)
                db.session.flush()
                e_ph = Expression(work_id=w_ph.id, content_type="text", language="en")
                db.session.add(e_ph)
                db.session.flush()
                placeholder_manif = Manifestation(expression_id=e_ph.id, isbn13=PH_ISBN, publisher="E2E Test")
                db.session.add(placeholder_manif)
                db.session.flush()

            # Generate 600x900 solid gray placeholder image
            ph_path = os.path.join(COVERS_DIR, "e2e_placeholder.jpg")
            Image.new("RGB", (600, 900), color=(200, 200, 200)).save(ph_path, "JPEG", quality=85)

            # Apply center watermark
            wm_ph = os.path.join(COVERS_DIR, "e2e_placeholder_wm.jpg")
            add_center_watermark(ph_path, watermark_asset, wm_ph)

            placeholder_manif.cover_url = "/static/covers/e2e_placeholder_wm.jpg"
            placeholder_manif.update_meta(cover_source="fallback_pil", cover_status="ready", cover_status_updated_at="2026-01-01T00:00:00Z")

            # Ensure an item exists for e2e-admin so it shows on /collection
            ph_item = Item.query.filter_by(manifestation_id=placeholder_manif.id, owner_id=e2e_admin.id).first()
            if not ph_item:
                ph_item = Item(
                    owner_id=e2e_admin.id,
                    manifestation_id=placeholder_manif.id,
                    is_hidden=False,
                    status="want_to_read",
                    collection_status="available",
                )
                db.session.add(ph_item)

            # LLM cover manifestation
            llm_manif = Manifestation.query.filter_by(isbn13=LLM_ISBN).first()
            if not llm_manif:
                w_llm = Work(title="Watermark LLM Cover", meta={"authors": ["E2E System"]})
                db.session.add(w_llm)
                db.session.flush()
                e_llm = Expression(work_id=w_llm.id, content_type="text", language="en")
                db.session.add(e_llm)
                db.session.flush()
                llm_manif = Manifestation(expression_id=e_llm.id, isbn13=LLM_ISBN, publisher="E2E Test")
                db.session.add(llm_manif)
                db.session.flush()

            # Generate 600x900 warm-toned image
            llm_path = os.path.join(COVERS_DIR, "e2e_llm_gen.jpg")
            Image.new("RGB", (600, 900), color=(180, 160, 220)).save(llm_path, "JPEG", quality=85)

            # Apply corner watermark
            wm_llm = os.path.join(COVERS_DIR, "e2e_llm_gen_wm.jpg")
            apply_corner_watermark(llm_path, watermark_asset, wm_llm)

            llm_manif.cover_url = "/static/covers/e2e_llm_gen_wm.jpg"
            llm_manif.update_meta(cover_source="llm_gemini", cover_status="ready", cover_status_updated_at="2026-01-01T00:00:00Z")

            # Ensure an item exists for e2e-admin
            llm_item = Item.query.filter_by(manifestation_id=llm_manif.id, owner_id=e2e_admin.id).first()
            if not llm_item:
                llm_item = Item(
                    owner_id=e2e_admin.id,
                    manifestation_id=llm_manif.id,
                    is_hidden=False,
                    status="want_to_read",
                    collection_status="available",
                )
                db.session.add(llm_item)
        else:
            print(f"WARNING: Watermark asset not found at {watermark_asset}. Skipping watermark cover seeding.")

        db.session.commit()
        print("E2E seed data created successfully")

        # ── Escalation E2E test data ────────────────────────────────────────
        from app.db.social import EscalationRequest  # noqa: E402

        existing_esc = EscalationRequest.query.filter_by(user_id=test_user.id, manifestation_id=m_public.id).first()
        if not existing_esc:
            esc = EscalationRequest(
                user_id=test_user.id,
                manifestation_id=m_public.id,
                field_name="title",
                suggested_value="Public Treasure (Corrected)",
                current_value="Public Treasure",
                note="This title should be corrected",
                request_type="correction",
                status="pending",
            )
            db.session.add(esc)
            db.session.commit()
            print("E2E escalation seed data created successfully")

        # ── Allegro Instance Settings for E2E device flow tests ────────────
        for k, v in [
            ("ALLEGRO_CLIENT_ID", "mock_allegro_client_id_12345"),
            ("ALLEGRO_CLIENT_SECRET", "mock_allegro_client_secret_67890"),
        ]:
            setting = db.session.execute(db.select(InstanceSettings).filter_by(key=k)).scalar_one_or_none()
            if not setting:
                setting = InstanceSettings(key=k, value=v)
                db.session.add(setting)
            else:
                setting.value = v
        db.session.commit()
        print("E2E Allegro instance settings seeded successfully")


if __name__ == "__main__":
    seed_e2e_data()
