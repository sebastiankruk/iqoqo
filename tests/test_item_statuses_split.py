# tests/test_item_statuses_split.py
"""Integration tests for split progress and collection statuses."""

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

import pytest

from app.db.models import Expression, Item, Manifestation, Work, db


@pytest.fixture
def sample_item(app, normal_user_headers):
    """Fixture to create a sample item for testing."""
    with app.app_context():
        w = Work(title="Status Split Test")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, isbn13="1112223334445")
        db.session.add(m)
        db.session.commit()

        # Manifestation is ready, but item doesn't exist yet
        # We find out the actual user_id from the system
        from app.db.models import User

        user = User.query.filter_by(email="test_user@iqoqo.local").first()

        item = Item(manifestation_id=m.id, owner_id=user.id, status="want_to_read", collection_status="available")
        db.session.add(item)
        db.session.commit()

        yield item


def test_add_item_defaults(client, normal_user_headers):
    """Verify that adding a new item sets correct default statuses."""
    # We use a manifestation that already exists in conftest or we mock lookup
    # Actually, we can just use the ISBN lookup in the API
    with client.application.app_context():
        # Ensure a manifestation exists for this ISBN
        w = Work(title="New Item Defaults Test")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, isbn13="9998887776665")
        db.session.add(m)
        db.session.commit()

    response = client.post("/api/item/9998887776665", json={}, headers=normal_user_headers)
    assert response.status_code == 200
    item_id = response.json["data"]["item_id"]

    with client.application.app_context():
        item = db.session.get(Item, item_id)
        assert item.status == "want_to_read"
        assert item.collection_status == "available"


def test_update_item_progress_status(client, sample_item, normal_user_headers):
    """Verify updating only progress status."""
    item_id = sample_item.id

    response = client.put(f"/api/items/{item_id}", json={"status": "reading"}, headers=normal_user_headers)
    assert response.status_code == 200

    with client.application.app_context():
        item = db.session.get(Item, item_id)
        assert item.status == "reading"
        assert item.collection_status == "available"
        assert item.status_logs.count() >= 1
        assert item.status_logs.order_by(db.desc("changed_at")).first().new_status == "reading"


def test_update_item_collection_status(client, sample_item, normal_user_headers):
    """Verify updating only collection status."""
    item_id = sample_item.id

    response = client.put(
        f"/api/items/{item_id}", json={"collection_status": "lent", "lent_to_name": "Caveman friend"}, headers=normal_user_headers
    )
    assert response.status_code == 200

    with client.application.app_context():
        item = db.session.get(Item, item_id)
        assert item.status == "want_to_read"  # Unchanged
        assert item.collection_status == "lent"
        assert item.status_logs.count() >= 1
        assert item.status_logs.order_by(db.desc("changed_at")).first().new_status == "lent"


def test_update_item_dual_status(client, sample_item, normal_user_headers):
    """Verify updating both statuses simultaneously."""
    item_id = sample_item.id

    response = client.put(f"/api/items/{item_id}", json={"status": "read", "collection_status": "lost"}, headers=normal_user_headers)
    assert response.status_code == 200

    with client.application.app_context():
        item = db.session.get(Item, item_id)
        assert item.status == "read"
        assert item.collection_status == "lost"
        # Since we send two distinct updates in the backend currently,
        # it should result in two log entries
        assert item.status_logs.count() >= 2
