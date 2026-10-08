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
Integration and unit tests for the Reading Roadmap feature.
Tests cover authentication controls, database persistence, and sequential positioning logic.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.auth import User
from app.db.core import Expression, Item, Manifestation, Work, db
from app.db.roadmap import ReadingRoadmap, RoadmapItem


def test_roadmap_endpoints_require_authentication(client) -> None:
    """Ensure unauthenticated requests are rejected with a 401 Unauthorized status code."""
    response = client.get("/api/v1/roadmaps")
    assert response.status_code == 401

    response = client.post("/api/v1/roadmaps", json={"title": "Queue"})
    assert response.status_code == 401


def test_create_roadmap(client, normal_user_headers) -> None:
    """Verify that an authenticated user can successfully create a new reading roadmap track."""
    payload = {
        "title": "Tech Learning Stack 2026",
        "description": "Distributed systems and semantic web architectures.",
        "is_public": True,
    }

    response = client.post("/api/v1/roadmaps", json=payload, headers=normal_user_headers)
    assert response.status_code == 201

    data = response.get_json()
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["is_public"] is True


def test_add_item_to_roadmap(client, normal_user_headers, app) -> None:
    """Verify item injection to a roadmap automatically calculates the correct tail position."""
    with app.app_context():
        user = db.session.execute(select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        work = Work(id=42, title="FRBR Deep Dive")
        roadmap = ReadingRoadmap(user_id=user.id, title="Reading Queue")
        db.session.add_all([work, roadmap])
        db.session.commit()
        roadmap_id = roadmap.id

    payload = {
        "work_id": 42,
        "notes": "Focus heavily on the FRBR ontology section.",
        "target_date": "2026-06-01",
    }

    response = client.post(
        f"/api/v1/roadmaps/{roadmap_id}/items",
        json=payload,
        headers=normal_user_headers,
    )
    assert response.status_code == 201

    data = response.get_json()
    assert data["work_id"] == 42
    assert data["position"] == 1
    assert data["status"] == "queued"


def test_roadmap_item_constraint_preserves_expression_target_and_rejects_invalid_target_sets(app) -> None:
    """Exactly one existing FRBR target is required; an Expression-only target remains valid."""
    with app.app_context():
        user = User(email="roadmap-frbr-constraint@iqoqo.local", google_id="roadmap-frbr-constraint")
        work = Work(title="Roadmap Expression Target")
        db.session.add_all([user, work])
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text")
        roadmap = ReadingRoadmap(user_id=user.id, title="Expression Target Queue")
        db.session.add_all([expression, roadmap])
        db.session.commit()

        expression_only = RoadmapItem(roadmap_id=roadmap.id, expression_id=expression.id, position=1)
        db.session.add(expression_only)
        db.session.commit()
        retrieved = db.session.get(RoadmapItem, expression_only.id)
        assert retrieved is not None
        assert retrieved.expression_id == expression.id

        no_target = RoadmapItem(roadmap_id=roadmap.id, position=2)
        db.session.add(no_target)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

        multiple_targets = RoadmapItem(
            roadmap_id=roadmap.id,
            work_id=work.id,
            expression_id=expression.id,
            position=2,
        )
        db.session.add(multiple_targets)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

        check_names = {constraint.name for constraint in RoadmapItem.__table__.constraints}
        assert "check_roadmap_item_single_frbr_level" in check_names


def test_reorder_roadmap_items(client, normal_user_headers, app) -> None:
    """Assert that moving an item shifts surrounding records to preserve exact linear ordering keys."""
    with app.app_context():
        user = db.session.execute(select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        roadmap = ReadingRoadmap(user_id=user.id, title="Reorder Queue")
        db.session.add(roadmap)
        db.session.commit()

        # Seed 3 items sequentially
        item1 = RoadmapItem(roadmap_id=roadmap.id, work_id=101, position=1)
        item2 = RoadmapItem(roadmap_id=roadmap.id, work_id=102, position=2)
        item3 = RoadmapItem(roadmap_id=roadmap.id, work_id=103, position=3)
        db.session.add_all([item1, item2, item3])
        db.session.commit()

        item3_id = item3.id
        item1_id = item1.id
        item2_id = item2.id
        roadmap_id = roadmap.id

    # Move item 3 to position 1
    response = client.patch(
        f"/api/v1/roadmaps/items/{item3_id}/position",
        json={"position": 1},
        headers=normal_user_headers,
    )
    assert response.status_code == 200

    # Refresh items from the database to check positioning keys
    with app.app_context():
        i1 = db.session.get(RoadmapItem, item1_id)
        i2 = db.session.get(RoadmapItem, item2_id)
        i3 = db.session.get(RoadmapItem, item3_id)

        assert i1 is not None
        assert i2 is not None
        assert i3 is not None

        assert i3.position == 1
        assert i1.position == 2
        assert i2.position == 3

    # Verify that GET endpoint returns items serialized in sorted order
    get_res = client.get("/api/v1/roadmaps", headers=normal_user_headers)
    assert get_res.status_code == 200
    roadmaps_data = get_res.get_json()
    reorder_roadmap = next((r for r in roadmaps_data if r["id"] == roadmap_id), None)
    assert reorder_roadmap is not None
    assert [item["id"] for item in reorder_roadmap["items"]] == [item3_id, item1_id, item2_id]

    # Move item 3 back to position 3 (shift down)
    response_down = client.patch(
        f"/api/v1/roadmaps/items/{item3_id}/position",
        json={"position": 3},
        headers=normal_user_headers,
    )
    assert response_down.status_code == 200

    with app.app_context():
        i1 = db.session.get(RoadmapItem, item1_id)
        i2 = db.session.get(RoadmapItem, item2_id)
        i3 = db.session.get(RoadmapItem, item3_id)

        assert i1 is not None
        assert i2 is not None
        assert i3 is not None
        assert i1.position == 1
        assert i2.position == 2
        assert i3.position == 3

    # Move item 1 to same position 1 (no-op)
    response_noop = client.patch(
        f"/api/v1/roadmaps/items/{item1_id}/position",
        json={"position": 1},
        headers=normal_user_headers,
    )
    assert response_noop.status_code == 200


def test_roadmap_cascade_deletion(app) -> None:
    """Verify that deleting a roadmap correctly purges all child items from the database."""
    with app.app_context():
        user = User(email="cascade@iqoqo.local", display_name="Cascade", google_id="cascade-user")
        db.session.add(user)
        db.session.commit()

        roadmap = ReadingRoadmap(user_id=user.id, title="Deletion Queue")
        db.session.add(roadmap)
        db.session.commit()

        item = RoadmapItem(roadmap_id=roadmap.id, work_id=201, position=1)
        db.session.add(item)
        db.session.commit()

        roadmap_id = roadmap.id
        item_id = item.id

        # Delete roadmap
        db.session.delete(roadmap)
        db.session.commit()

        assert db.session.get(ReadingRoadmap, roadmap_id) is None
        assert db.session.get(RoadmapItem, item_id) is None


def test_delete_roadmap_endpoint(client, normal_user_headers, app) -> None:
    """Verify that DELETE /api/v1/roadmaps/<id> successfully removes the roadmap and items."""
    with app.app_context():
        user = db.session.execute(select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        roadmap = ReadingRoadmap(user_id=user.id, title="To Be Deleted")
        db.session.add(roadmap)
        db.session.commit()

        item = RoadmapItem(roadmap_id=roadmap.id, work_id=301, position=1)
        db.session.add(item)
        db.session.commit()

        roadmap_id = roadmap.id
        item_id = item.id

    res = client.delete(f"/api/v1/roadmaps/{roadmap_id}", headers=normal_user_headers)
    assert res.status_code == 200
    assert res.get_json() == {"success": True}

    with app.app_context():
        assert db.session.get(ReadingRoadmap, roadmap_id) is None
        assert db.session.get(RoadmapItem, item_id) is None


def test_roadmap_item_four_level_persistence_and_constraints(app) -> None:
    """All four FRBR levels persist; zero or multiple targets fail constraint."""
    with app.app_context():
        user = User(email="four-levels@iqoqo.local", google_id="four-levels-user")
        work = Work(title="Sacred Scroll")
        db.session.add_all([user, work])
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(expression_id=expr.id)
        db.session.add(man)
        db.session.flush()

        item = Item(manifestation_id=man.id, owner_id=user.id)
        roadmap = ReadingRoadmap(user_id=user.id, title="Four Levels Queue")
        db.session.add_all([item, roadmap])
        db.session.commit()

        # 1. Work target
        rm_work = RoadmapItem(roadmap_id=roadmap.id, work_id=work.id, position=1)
        # 2. Expression target
        rm_expr = RoadmapItem(roadmap_id=roadmap.id, expression_id=expr.id, position=2)
        # 3. Manifestation target
        rm_man = RoadmapItem(roadmap_id=roadmap.id, manifestation_id=man.id, position=3)
        # 4. Item target
        rm_item = RoadmapItem(roadmap_id=roadmap.id, item_id=item.id, position=4)
        db.session.add_all([rm_work, rm_expr, rm_man, rm_item])
        db.session.commit()

        assert db.session.get(RoadmapItem, rm_work.id).work_id == work.id
        assert db.session.get(RoadmapItem, rm_expr.id).expression_id == expr.id
        assert db.session.get(RoadmapItem, rm_man.id).manifestation_id == man.id
        assert db.session.get(RoadmapItem, rm_item.id).item_id == item.id
        assert db.session.get(RoadmapItem, rm_item.id).to_dict()["target_type"] == "item"

        # Zero targets fail
        invalid_zero = RoadmapItem(roadmap_id=roadmap.id, position=5)
        db.session.add(invalid_zero)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()

        # Multiple targets fail
        invalid_multi = RoadmapItem(roadmap_id=roadmap.id, work_id=work.id, item_id=item.id, position=5)
        db.session.add(invalid_multi)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


def test_roadmap_item_restrict_target_deletion(app) -> None:
    """Deleting a referenced target is blocked by RESTRICT FK; removing roadmap item permits deletion."""
    from sqlalchemy import text

    with app.app_context():
        is_sqlite = db.engine.dialect.name == "sqlite"
        if is_sqlite:
            db.session.execute(text("PRAGMA foreign_keys=ON"))

        try:
            user = User(email="restrict-del@iqoqo.local", google_id="restrict-del-user")
            work = Work(title="Protected Story")
            db.session.add_all([user, work])
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            man = Manifestation(expression_id=expr.id)
            db.session.add(man)
            db.session.flush()

            item = Item(manifestation_id=man.id, owner_id=user.id)
            roadmap = ReadingRoadmap(user_id=user.id, title="Protected Queue")
            db.session.add_all([item, roadmap])
            db.session.commit()

            rm_sibling = RoadmapItem(roadmap_id=roadmap.id, work_id=work.id, position=1)
            rm_item = RoadmapItem(roadmap_id=roadmap.id, item_id=item.id, position=2)
            db.session.add_all([rm_sibling, rm_item])
            db.session.commit()

            # Attempt to delete referenced item - should fail with IntegrityError because rm_item references it
            db.session.delete(item)
            with pytest.raises(IntegrityError):
                db.session.flush()
            db.session.rollback()

            # Roadmap and items are untouched
            assert db.session.get(Item, item.id) is not None
            assert db.session.get(RoadmapItem, rm_item.id) is not None
            assert db.session.get(RoadmapItem, rm_sibling.id) is not None

            # Remove the roadmap item entry referencing the item
            retrieved_rm_item = db.session.get(RoadmapItem, rm_item.id)
            db.session.delete(retrieved_rm_item)
            db.session.commit()

            # Now deleting the item succeeds!
            retrieved_item = db.session.get(Item, item.id)
            db.session.delete(retrieved_item)
            db.session.commit()

            assert db.session.get(Item, item.id) is None
            # Roadmap and sibling entry remain intact
            assert db.session.get(ReadingRoadmap, roadmap.id) is not None
            assert db.session.get(RoadmapItem, rm_sibling.id) is not None
        finally:
            if is_sqlite:
                db.session.execute(text("PRAGMA foreign_keys=OFF"))
                db.session.commit()


def test_add_item_to_roadmap_validation_and_ownership(client, normal_user_headers, app) -> None:
    """API enforces exactly-one positive integer target, entity existence, and Item ownership."""
    with app.app_context():
        user = db.session.execute(select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        other_user = User(email="other_hunter@iqoqo.local", google_id="other_hunter")
        work = Work(title="Mammoth Hunting Guide", meta={"authors": ["Chief Ogg"]})
        db.session.add_all([other_user, work])
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(expression_id=expr.id, publisher="Cave Press")
        db.session.add(man)
        db.session.flush()

        # Item owned by user
        own_item = Item(manifestation_id=man.id, owner_id=user.id)
        # Item owned by other_user (lent to user)
        borrowed_item = Item(manifestation_id=man.id, owner_id=other_user.id, lent_to_user_id=user.id)
        roadmap = ReadingRoadmap(user_id=user.id, title="Hunter Roadmap")
        db.session.add_all([own_item, borrowed_item, roadmap])
        db.session.commit()

        roadmap_id = roadmap.id
        work_id = work.id
        expr_id = expr.id
        man_id = man.id
        own_item_id = own_item.id
        borrowed_item_id = borrowed_item.id

    # 1. Reject missing target
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={}, headers=normal_user_headers)
    assert res.status_code == 400

    # 2. Reject multiple targets
    res = client.post(
        f"/api/v1/roadmaps/{roadmap_id}/items",
        json={"work_id": work_id, "item_id": own_item_id},
        headers=normal_user_headers,
    )
    assert res.status_code == 400

    # 3. Reject invalid target type or negative ID (e.g. wishlist virtual ID)
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"item_id": -99}, headers=normal_user_headers)
    assert res.status_code == 400
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"item_id": 0}, headers=normal_user_headers)
    assert res.status_code == 400
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"work_id": "abc"}, headers=normal_user_headers)
    assert res.status_code == 400

    # 4. Reject nonexistent target entities
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"work_id": 999999}, headers=normal_user_headers)
    assert res.status_code == 404
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"expression_id": 999999}, headers=normal_user_headers)
    assert res.status_code == 404
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"manifestation_id": 999999}, headers=normal_user_headers)
    assert res.status_code == 404
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"item_id": 999999}, headers=normal_user_headers)
    assert res.status_code == 404

    # 5. Reject borrowed item (not owned by user) - must return 404 without leaking other user's item
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"item_id": borrowed_item_id}, headers=normal_user_headers)
    assert res.status_code == 404

    # 6. Successfully add owned Item target
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"item_id": own_item_id}, headers=normal_user_headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data["item_id"] == own_item_id
    assert data["work_id"] is None
    assert data["expression_id"] is None
    assert data["manifestation_id"] is None
    assert data["target_type"] == "item"
    assert "Personal copy" in data["summary"]
    assert data["title"] == "Mammoth Hunting Guide"
    assert data["creator"] == "Chief Ogg"

    # 7. Successfully add Expression target
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"expression_id": expr_id}, headers=normal_user_headers)
    assert res.status_code == 201
    assert res.get_json()["target_type"] == "expression"

    # 8. Successfully add Manifestation target
    res = client.post(f"/api/v1/roadmaps/{roadmap_id}/items", json={"manifestation_id": man_id}, headers=normal_user_headers)
    assert res.status_code == 201
    assert res.get_json()["target_type"] == "manifestation"


def test_roadmap_item_target_replacement_and_deletion(client, normal_user_headers, app) -> None:
    """Target replacement preserves entry state; entry deletion compacts positions."""
    with app.app_context():
        user = db.session.execute(select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        work = Work(title="Campfire Tales")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(expression_id=expr.id)
        db.session.add(man)
        db.session.flush()

        item = Item(manifestation_id=man.id, owner_id=user.id)
        roadmap = ReadingRoadmap(user_id=user.id, title="Campfire Roadmap")
        db.session.add_all([item, roadmap])
        db.session.commit()

        ri1 = RoadmapItem(roadmap_id=roadmap.id, work_id=work.id, position=1, notes="Note 1")
        ri2 = RoadmapItem(roadmap_id=roadmap.id, manifestation_id=man.id, position=2, notes="Note 2")
        ri3 = RoadmapItem(roadmap_id=roadmap.id, item_id=item.id, position=3, notes="Note 3")
        db.session.add_all([ri1, ri2, ri3])
        db.session.commit()

        ri2_id = ri2.id
        ri3_id = ri3.id
        item_id = item.id

    # Replace target of ri2 from manifestation to owned item
    res = client.patch(
        f"/api/v1/roadmaps/items/{ri2_id}",
        json={"item_id": item_id},
        headers=normal_user_headers,
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["item_id"] == item_id
    assert data["manifestation_id"] is None
    assert data["target_type"] == "item"
    assert data["position"] == 2  # preserved!
    assert data["notes"] == "Note 2"  # preserved!

    # Delete ri2 (position 2) -> ri3 (position 3) should be compacted to position 2
    res = client.delete(f"/api/v1/roadmaps/items/{ri2_id}", headers=normal_user_headers)
    assert res.status_code == 200
    assert res.get_json() == {"success": True}

    with app.app_context():
        assert db.session.get(RoadmapItem, ri2_id) is None
        remaining_ri3 = db.session.get(RoadmapItem, ri3_id)
        assert remaining_ri3 is not None
        assert remaining_ri3.position == 2  # Compacted from 3 to 2!


def test_delete_target_returns_409_conflict(client, admin_headers, app) -> None:
    """Deleting a catalog or inventory entity referenced by a roadmap returns HTTP 409."""
    from sqlalchemy import text

    with app.app_context():
        is_sqlite = db.engine.dialect.name == "sqlite"
        if is_sqlite:
            db.session.execute(text("PRAGMA foreign_keys=ON"))

        try:
            user = db.session.execute(select(User).filter_by(email="test_admin@iqoqo.local")).scalar_one()
            work = Work(title="Protected FRBR Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            man = Manifestation(expression_id=expr.id)
            db.session.add(man)
            db.session.flush()

            item = Item(manifestation_id=man.id, owner_id=user.id)
            roadmap = ReadingRoadmap(user_id=user.id, title="Lock Queue")
            db.session.add_all([item, roadmap])
            db.session.commit()

            rm_item = RoadmapItem(roadmap_id=roadmap.id, item_id=item.id, position=1)
            db.session.add(rm_item)
            db.session.commit()

            item_id = item.id
            rm_item_id = rm_item.id

            # Attempt to delete the item via API - should return 409 Conflict
            res = client.delete(f"/api/items/{item_id}", headers=admin_headers)
            assert res.status_code == 409
            assert "reading roadmap" in res.get_json()["error"]

            # Remove roadmap item
            res = client.delete(f"/api/v1/roadmaps/items/{rm_item_id}", headers=admin_headers)
            assert res.status_code == 200

            # Now delete item succeeds
            res = client.delete(f"/api/items/{item_id}", headers=admin_headers)
            assert res.status_code == 200
        finally:
            if is_sqlite:
                db.session.execute(text("PRAGMA foreign_keys=OFF"))
                db.session.commit()


def test_items_owner_only_filter(client, normal_user_headers, app) -> None:
    """GET /api/items?owner_only=true returns only physical items owned by requester."""
    with app.app_context():
        user = db.session.execute(select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        other_user = User(email="second_user@iqoqo.local", google_id="second_user")
        work = Work(title="Flint and Fire")
        db.session.add_all([other_user, work])
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(expression_id=expr.id)
        db.session.add(man)
        db.session.flush()

        own_item = Item(manifestation_id=man.id, owner_id=user.id)
        borrowed_item = Item(manifestation_id=man.id, owner_id=other_user.id, lent_to_user_id=user.id)
        db.session.add_all([own_item, borrowed_item])
        db.session.commit()

        own_id = own_item.id
        borrowed_id = borrowed_item.id

    # With owner_only=true: borrowed_item is excluded
    res = client.get("/api/items?owner_only=true", headers=normal_user_headers)
    assert res.status_code == 200
    returned_ids = [it["id"] for it in res.get_json()["data"]]
    assert own_id in returned_ids
    assert borrowed_id not in returned_ids


def test_get_roadmaps_pagination(client, normal_user_headers, app) -> None:
    """GET /api/v1/roadmaps supports page and limit pagination."""
    with app.app_context():
        user = db.session.execute(select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        roadmaps = [ReadingRoadmap(user_id=user.id, title=f"Track Page {i}") for i in range(1, 6)]
        db.session.add_all(roadmaps)
        db.session.commit()

    # Request limit=2, page=1
    res = client.get("/api/v1/roadmaps?page=1&limit=2", headers=normal_user_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 2

    # Request limit=2, page=2
    res2 = client.get("/api/v1/roadmaps?page=2&limit=2", headers=normal_user_headers)
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert len(data2) == 2
    # Ensure disjoint pages
    page1_ids = {r["id"] for r in data}
    page2_ids = {r["id"] for r in data2}
    assert page1_ids.isdisjoint(page2_ids)
