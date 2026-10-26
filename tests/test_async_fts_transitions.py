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
"""Tests for asynchronous transition ingestion and background FTS re-indexing."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.api.auth import generate_internal_jwt
from app.core.tasks import _in_memory_fts_queue, batch_fts_reindex, enqueue_fts_reindex
from app.db import db
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, Work


@pytest.fixture
def test_user_and_item(app):
    """Seed test user and item for transition tests."""
    with app.app_context():
        role = db.session.execute(select(Role).where(Role.name == "user")).scalars().first()
        if not role:
            role = Role(name="user")
            db.session.add(role)

        perm = db.session.execute(select(Permission).where(Permission.name == "write:item")).scalars().first()
        if not perm:
            perm = Permission(name="write:item")
            db.session.add(perm)
        if perm not in role.permissions:
            role.permissions.append(perm)

        user = User(
            email="async_tester@iqoqo.local",
            display_name="Async Tester",
            public_username="asynctester",
        )
        user.roles.append(role)
        db.session.add(user)
        db.session.flush()

        work = Work(title="Dune Messiah", meta={"authors": "Frank Herbert"})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book")
        db.session.add(expr)
        db.session.flush()

        mani = Manifestation(expression_id=expr.id, publisher="Chilton Books")
        db.session.add(mani)
        db.session.flush()

        item = Item(
            manifestation_id=mani.id,
            owner_id=user.id,
            status="want_to_read",
            collection_status="available",
        )
        db.session.add(item)
        db.session.commit()

        token = generate_internal_jwt(user)

        return {
            "user_id": user.id,
            "token": token,
            "item_id": item.id,
            "manifestation_id": mani.id,
            "work_id": work.id,
        }


def test_enqueue_fts_reindex_coalesces_duplicate_entity_keys(app):
    """Verify that multiple rapid enqueue calls for the same entity coalesce and debounce dispatch."""
    with app.app_context():
        import app.core.tasks as tasks_module
        from app.core.events import get_redis_client

        client = get_redis_client()
        if client:
            client.delete(tasks_module.REDIS_FTS_QUEUE_KEY)
            client.delete(tasks_module.REDIS_FTS_SCHEDULED_KEY)
        tasks_module._in_memory_fts_queue.clear()
        tasks_module._in_memory_debounce_time = 0.0

        # Patch apply_async to isolate enqueueing and prevent eager test execution
        with patch.object(tasks_module.batch_fts_reindex, "apply_async") as mock_apply:
            enqueue_fts_reindex("item", 42, countdown=5)
            enqueue_fts_reindex("item", 42, countdown=5)
            enqueue_fts_reindex("item", 42, countdown=5)

            if client:
                members = {m.decode() if isinstance(m, bytes) else m for m in client.smembers(tasks_module.REDIS_FTS_QUEUE_KEY)}
                assert "item:42" in members
                assert len(members) == 1
                client.delete(tasks_module.REDIS_FTS_QUEUE_KEY)
                client.delete(tasks_module.REDIS_FTS_SCHEDULED_KEY)
            else:
                assert "item:42" in tasks_module._in_memory_fts_queue
                assert len(tasks_module._in_memory_fts_queue) == 1
            assert mock_apply.call_count == 1


def test_batch_fts_reindex_task_drains_queue_and_updates_entities(app, test_user_and_item):
    """Verify that batch_fts_reindex drains the queue, updates entities, and updates Work.search_vector."""
    with app.app_context():
        import app.core.tasks as tasks_module

        item_id = test_user_and_item["item_id"]
        mani_id = test_user_and_item["manifestation_id"]

        tasks_module._in_memory_fts_queue.add(f"item:{item_id}")
        tasks_module._in_memory_fts_queue.add(f"manifestation:{mani_id}")

        result = batch_fts_reindex()

        assert result["status"] == "success"
        assert result["reindexed_count"] >= 2
        assert f"item:{item_id}" in result["entities"]
        assert len(tasks_module._in_memory_fts_queue) == 0

        work = db.session.get(Work, test_user_and_item["work_id"])
        assert work.search_vector is not None
        assert "Dune Messiah" in work.search_vector


def test_item_update_transition_enqueues_fts_reindex(client, test_user_and_item):
    """Verify that PUT/PATCH /api/items/<id> triggers enqueue_fts_reindex."""
    item_id = test_user_and_item["item_id"]
    headers = {"Authorization": f"Bearer {test_user_and_item['token']}"}

    with patch("app.api.items.enqueue_fts_reindex") as mock_enqueue:
        res = client.patch(
            f"/api/items/{item_id}",
            json={"status": "reading"},
            headers=headers,
        )
        assert res.status_code == 200
        mock_enqueue.assert_called_with("item", item_id)
