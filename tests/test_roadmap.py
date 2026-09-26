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
from app.db.core import Expression, Work, db
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
        roadmap = ReadingRoadmap(user_id=user.id, title="Reading Queue")
        db.session.add(roadmap)
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
