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
"""Tests for entity audit logging at the model level.

Verifies that EntityAuditLog records are correctly created and queryable
for merge operations and metadata edits, and that audit and custody logs
remain independent.
"""

import pytest

from app.db.models import EntityAuditLog, ItemCustodyEvent, User, Work, db


@pytest.fixture
def audit_user(app):
    """Create a user for audit log tests and return its ID."""
    with app.app_context():
        user = User(email="audit_tester@iqoqo.local", display_name="Audit Tester")
        db.session.add(user)
        db.session.commit()
        return user.id


class TestEntityAuditLogBasicQueries:
    """Basic insert and query operations for EntityAuditLog."""

    def test_insert_and_query_merge_event(self, app, audit_user):
        """Verify audit log entry created on entity merge (assert row exists
        with merge event type, source/target entity IDs)."""
        with app.app_context():
            audit = EntityAuditLog(
                entity_type="work",
                entity_id=42,
                actor_id=audit_user,
                change_type="merge",
                diff={"source_entity_id": 1, "target_entity_id": 2},
            )
            db.session.add(audit)
            db.session.commit()

            fetched = db.session.get(EntityAuditLog, audit.id)
            assert fetched is not None
            assert fetched.entity_type == "work"
            assert fetched.entity_id == 42
            assert fetched.change_type == "merge"
            assert fetched.diff is not None
            assert fetched.diff["source_entity_id"] == 1
            assert fetched.diff["target_entity_id"] == 2

    def test_insert_and_query_metadata_edit_event(self, app, audit_user):
        """Verify audit log entry created on metadata edit (assert row exists
        with edit event type, changed fields recorded)."""
        with app.app_context():
            audit = EntityAuditLog(
                entity_type="work",
                entity_id=99,
                actor_id=audit_user,
                change_type="metadata_edit",
                diff={"title": {"before": "Old Title", "after": "New Title"}},
            )
            db.session.add(audit)
            db.session.commit()

            fetched = db.session.get(EntityAuditLog, audit.id)
            assert fetched is not None
            assert fetched.change_type == "metadata_edit"
            assert fetched.diff is not None
            assert "title" in fetched.diff

    def test_entity_audit_log_model_importable(self, app):
        """EntityAuditLog should be importable from the models shim."""
        from app.db.models import EntityAuditLog as EAL

        assert EAL is not None


class TestAuditCustodyIndependence:
    """Verify audit log and custody log are independent tables."""

    def test_audit_entry_not_in_custody_table(self, app, audit_user):
        """Assert audit entry does NOT appear in custody events table."""
        with app.app_context():
            # Create audit log entry
            audit = EntityAuditLog(
                entity_type="work",
                entity_id=1,
                actor_id=audit_user,
                change_type="merge",
                diff={},
            )
            db.session.add(audit)
            db.session.commit()

            # Verify custody events table does NOT contain this entry
            custody_events = ItemCustodyEvent.query.filter_by(
                item_id=1,
                event_type="merge",
            ).all()
            assert len(custody_events) == 0

    def test_custody_entry_not_in_audit_table(self, app, audit_user):
        """Assert custody event does NOT appear in entity audit log."""
        with app.app_context():
            # Create a work and manifestation for the item chain (needed for FK)
            w = Work(title="Custody Test Work")
            db.session.add(w)
            db.session.flush()
            from app.db.models import Expression, Item, Manifestation

            e = Expression(work_id=w.id, content_type="text", language="en")
            db.session.add(e)
            db.session.flush()
            m = Manifestation(expression_id=e.id)
            db.session.add(m)
            db.session.flush()
            item = Item(manifestation_id=m.id, owner_id=audit_user)
            db.session.add(item)
            db.session.commit()

            # Create custody event
            custody = ItemCustodyEvent(
                item_id=item.id,
                actor_id=audit_user,
                event_type="acquisition",
                notes="Test custody event",
            )
            db.session.add(custody)
            db.session.commit()

            # Verify entity_audit_logs table does NOT contain this event
            audit_entries = EntityAuditLog.query.filter_by(
                entity_type="item",
                entity_id=item.id,
                change_type="acquisition",
            ).all()
            assert len(audit_entries) == 0

    def test_both_logs_can_coexist(self, app, audit_user):
        """Verify both audit and custody logs can store records independently."""
        with app.app_context():
            # Create audit log
            audit = EntityAuditLog(
                entity_type="work",
                entity_id=5,
                actor_id=audit_user,
                change_type="metadata_edit",
                diff={},
            )
            db.session.add(audit)
            db.session.flush()

            # Create custody event in parallel
            w = Work(title="Coexist Test")
            db.session.add(w)
            db.session.flush()
            from app.db.models import Expression, Item, Manifestation

            e = Expression(work_id=w.id, content_type="text", language="en")
            db.session.add(e)
            db.session.flush()
            m = Manifestation(expression_id=e.id)
            db.session.add(m)
            db.session.flush()
            item = Item(manifestation_id=m.id, owner_id=audit_user)
            db.session.add(item)
            db.session.flush()

            custody = ItemCustodyEvent(
                item_id=item.id,
                actor_id=audit_user,
                event_type="transfer",
            )
            db.session.add(custody)
            db.session.commit()

            # Both records should exist
            assert db.session.get(EntityAuditLog, audit.id) is not None
            assert db.session.get(ItemCustodyEvent, custody.id) is not None

    def test_multiple_audit_entries_for_same_entity(self, app, audit_user):
        """Verify multiple audit log entries can exist for the same entity."""
        with app.app_context():
            entry1 = EntityAuditLog(
                entity_type="work",
                entity_id=10,
                actor_id=audit_user,
                change_type="metadata_edit",
                diff={"title": {"before": "A", "after": "B"}},
            )
            db.session.add(entry1)
            db.session.flush()

            entry2 = EntityAuditLog(
                entity_type="work",
                entity_id=10,
                actor_id=audit_user,
                change_type="merge",
                diff={"source_entity_id": 20, "target_entity_id": 10},
            )
            db.session.add(entry2)
            db.session.commit()

            entries = EntityAuditLog.query.filter_by(entity_type="work", entity_id=10).all()
            assert len(entries) == 2
            change_types = {e.change_type for e in entries}
            assert "metadata_edit" in change_types
            assert "merge" in change_types
