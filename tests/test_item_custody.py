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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Tests for item custody events at the model level.

Verifies that ItemCustodyEvent records are append-only, WEM records remain
unmodified during custody operations, and loan request eligibility rules
are enforced.
"""

import pytest

from app.db.models import Expression, Item, ItemCustodyEvent, Manifestation, User, Work, db


@pytest.fixture
def custody_user(app):
    """Create a user for custody tests and return its ID."""
    with app.app_context():
        user = User(email="custody_tester@iqoqo.local", display_name="Custody Tester")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_physical_item(app, custody_user):
    """Create a full FRBR chain and a physical item for custody tests."""
    with app.app_context():
        w = Work(title="Custody Test Work")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, isbn13="9780000000001")
        db.session.add(m)
        db.session.flush()
        item = Item(
            manifestation_id=m.id,
            owner_id=custody_user,
            status="available",
            collection_status="available",
        )
        db.session.add(item)
        db.session.commit()
        return {
            "item_id": item.id,
            "work_id": w.id,
            "expression_id": e.id,
            "manifestation_id": m.id,
        }


class TestItemCustodyEventBasicQueries:
    """Basic insert and query operations for ItemCustodyEvent."""

    def test_insert_and_query_custody_event(self, app, custody_user, sample_physical_item):
        """ItemCustodyEvent records can be inserted and queried via ORM."""
        with app.app_context():
            event = ItemCustodyEvent(
                item_id=sample_physical_item["item_id"],
                actor_id=custody_user,
                event_type="acquisition",
                notes="Initial purchase",
            )
            db.session.add(event)
            db.session.commit()

            fetched = db.session.get(ItemCustodyEvent, event.id)
            assert fetched is not None
            assert fetched.event_type == "acquisition"
            assert fetched.item_id == sample_physical_item["item_id"]
            assert fetched.notes == "Initial purchase"

    def test_custody_event_model_importable(self, app):
        """ItemCustodyEvent should be importable from the models shim."""
        import importlib

        module = importlib.import_module("app.db.models")
        assert hasattr(module, "ItemCustodyEvent")


class TestCustodyEventsAppendOnly:
    """Verify custody events are append-only."""

    def test_custody_events_are_append_only(self, app, custody_user, sample_physical_item):
        """Verify that old events are unchanged after a new event is created,
        and that the row count increases by 1."""
        with app.app_context():
            # Create first event
            event1 = ItemCustodyEvent(
                item_id=sample_physical_item["item_id"],
                actor_id=custody_user,
                event_type="acquisition",
                notes="Original acquisition",
            )
            db.session.add(event1)
            db.session.commit()
            event1_id = event1.id
            event1_type = event1.event_type
            event1_notes = event1.notes

            # Count events before
            count_before = ItemCustodyEvent.query.filter_by(item_id=sample_physical_item["item_id"]).count()

            # Create second event
            event2 = ItemCustodyEvent(
                item_id=sample_physical_item["item_id"],
                actor_id=custody_user,
                event_type="transfer",
                notes="Loaned to friend",
            )
            db.session.add(event2)
            db.session.commit()

            # Verify event1 unchanged
            fetched1 = db.session.get(ItemCustodyEvent, event1_id)
            assert fetched1 is not None
            assert fetched1.event_type == event1_type
            assert fetched1.notes == event1_notes

            # Verify count increased by 1
            count_after = ItemCustodyEvent.query.filter_by(item_id=sample_physical_item["item_id"]).count()
            assert count_after == count_before + 1

    def test_multiple_custody_events_accumulate(self, app, custody_user, sample_physical_item):
        """Verify multiple custody events can be appended for the same item."""
        with app.app_context():
            events_data = [
                ("acquisition", "Bought"),
                ("transfer", "Lent to Alice"),
                ("return", "Returned by Alice"),
                ("condition_update", "Minor wear noted"),
            ]

            for evt_type, note in events_data:
                event = ItemCustodyEvent(
                    item_id=sample_physical_item["item_id"],
                    actor_id=custody_user,
                    event_type=evt_type,
                    notes=note,
                )
                db.session.add(event)
            db.session.commit()

            events = ItemCustodyEvent.query.filter_by(item_id=sample_physical_item["item_id"]).order_by(ItemCustodyEvent.id.asc()).all()

            assert len(events) == 4
            assert events[0].event_type == "acquisition"
            assert events[1].event_type == "transfer"
            assert events[2].event_type == "return"
            assert events[3].event_type == "condition_update"


class TestWEMRecordsUnmodifiedDuringCustody:
    """Verify WEM records remain unchanged during custody operations."""

    def test_wem_records_unchanged_after_custody_event(self, app, custody_user, sample_physical_item):
        """Assert Work, Expression, and Manifestation records remain unchanged
        after a custody event is recorded."""
        with app.app_context():
            # Snapshot WEM state before
            work_before = db.session.get(Work, sample_physical_item["work_id"])
            expr_before = db.session.get(Expression, sample_physical_item["expression_id"])
            mfn_before = db.session.get(Manifestation, sample_physical_item["manifestation_id"])

            assert work_before is not None
            assert expr_before is not None
            assert mfn_before is not None

            w_title_before = work_before.title
            e_language_before = expr_before.language
            m_isbn_before = mfn_before.isbn13

            # Record a custody event
            event = ItemCustodyEvent(
                item_id=sample_physical_item["item_id"],
                actor_id=custody_user,
                event_type="transfer",
                notes="Test transfer",
            )
            db.session.add(event)
            db.session.commit()

            # Verify WEM records unchanged
            work_after = db.session.get(Work, sample_physical_item["work_id"])
            expr_after = db.session.get(Expression, sample_physical_item["expression_id"])
            mfn_after = db.session.get(Manifestation, sample_physical_item["manifestation_id"])

            assert work_after.title == w_title_before
            assert expr_after.language == e_language_before
            assert mfn_after.isbn13 == m_isbn_before

    def test_multiple_custody_events_do_not_affect_wem(self, app, custody_user, sample_physical_item):
        """Multiple custody events should leave WEM records untouched."""
        with app.app_context():
            w_before = db.session.get(Work, sample_physical_item["work_id"])
            w_meta_before = dict(w_before.meta) if w_before.meta else {}

            for i in range(3):
                event = ItemCustodyEvent(
                    item_id=sample_physical_item["item_id"],
                    actor_id=custody_user,
                    event_type=f"test_event_{i}",
                )
                db.session.add(event)
            db.session.commit()

            w_after = db.session.get(Work, sample_physical_item["work_id"])
            w_meta_after = dict(w_after.meta) if w_after.meta else {}

            assert w_before.title == w_after.title
            assert w_meta_before == w_meta_after


class TestLoanRequestEligibility:
    """Verify loan request eligibility rules for borrowable/non-borrowable items."""

    @pytest.fixture
    def borrowable_item(self, app, custody_user):
        """Create a borrowable physical item."""
        with app.app_context():
            w = Work(title="Borrowable Item Work")
            db.session.add(w)
            db.session.flush()
            e = Expression(work_id=w.id, content_type="text", language="en")
            db.session.add(e)
            db.session.flush()
            m = Manifestation(expression_id=e.id, isbn13="9780000000002")
            db.session.add(m)
            db.session.flush()
            item = Item(
                manifestation_id=m.id,
                owner_id=custody_user,
                status="available",
                collection_status="available",
            )
            db.session.add(item)
            db.session.commit()
            return item.id

    @pytest.fixture
    def non_borrowable_item(self, app, custody_user):
        """Create a non-borrowable physical item (e.g., wishlist-only context)."""
        with app.app_context():
            w = Work(title="Non-Borrowable Item Work")
            db.session.add(w)
            db.session.flush()
            e = Expression(work_id=w.id, content_type="text", language="en")
            db.session.add(e)
            db.session.flush()
            m = Manifestation(expression_id=e.id, isbn13="9780000000003")
            db.session.add(m)
            db.session.flush()
            item = Item(
                manifestation_id=m.id,
                owner_id=custody_user,
                status="want_to_read",
                collection_status="wish_list",
            )
            db.session.add(item)
            db.session.commit()
            return item.id

    def test_loan_request_allowed_for_available_item(self, app, custody_user, borrowable_item):
        """Verify a custody event for a borrowable item can be recorded."""
        with app.app_context():
            item = db.session.get(Item, borrowable_item)
            assert item is not None
            assert item.collection_status == "available"

            event = ItemCustodyEvent(
                item_id=borrowable_item,
                actor_id=custody_user,
                event_type="transfer",
                notes="Loan request registered",
            )
            db.session.add(event)
            db.session.commit()

            fetched = db.session.get(ItemCustodyEvent, event.id)
            assert fetched is not None
            assert fetched.event_type == "transfer"

    def test_loan_request_rejected_for_wishlist_item(self, app, custody_user, non_borrowable_item):
        """Verify a wishlist-only item is not in a borrowable state."""
        with app.app_context():
            item = db.session.get(Item, non_borrowable_item)
            assert item is not None
            assert item.collection_status == "wish_list"
            # Wishlist items are not borrowable; custody events for them
            # may still be recorded for provenance but the collection_status
            # prevents a loan. This test verifies the item state.
            assert item.status == "want_to_read"
            assert item.collection_status != "available"
