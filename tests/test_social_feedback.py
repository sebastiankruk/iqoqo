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

"""Tests for social feedback (ratings and comments) on FRBR levels."""

import pytest

from app.api.auth import generate_internal_jwt
from app.db import db
from app.db.models import Expression, Item, Manifestation, Permission, Role, SocialFeedback, User, Work


@pytest.fixture
def social_setup(app):
    """Seed database with user, role, and the FRBR hierarchy items."""
    with app.app_context():
        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            user_role = Role(name="user")
            db.session.add(user_role)

        # Ensure user permissions
        for perm_name in ["write:item", "delete:item"]:
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
            if perm not in user_role.permissions:
                user_role.permissions.append(perm)

        # Create two users
        u1 = User(email="critic1@iqoqo.local", display_name="Critic One", public_username="critic1")
        u2 = User(email="critic2@iqoqo.local", display_name="Critic Two", public_username="critic2")
        u1.roles.append(user_role)
        u2.roles.append(user_role)
        db.session.add_all([u1, u2])
        db.session.flush()

        # Create FRBR structure
        work = Work(title="Test Conceptual Work", meta={"authors": ["Author X"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780000000001", meta={"format": "book"})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=u1.id, status="reading", collection_status="available")
        db.session.add(item)
        db.session.flush()

        db.session.commit()
        return {
            "u1_id": u1.id,
            "u2_id": u2.id,
            "work_id": work.id,
            "expression_id": expr.id,
            "manifestation_id": manif.id,
            "item_id": item.id,
        }


def get_headers(app, user_id):
    """Generate auth headers for a user."""
    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


def test_feedback_target_existence_check(client, social_setup, app):
    """POST and GET returns 404 for nonexistent targets."""
    headers = get_headers(app, social_setup["u1_id"])

    # Nonexistent work feedback POST
    response = client.post(
        "/api/feedback/work/99999",
        json={"rating": 5, "comment": "Nice"},
        headers=headers,
    )
    assert response.status_code == 404
    assert "Work not found" in response.json["error"]

    # Nonexistent expression feedback GET
    response = client.get("/api/feedback/expression/99999")
    assert response.status_code == 404
    assert "Expression not found" in response.json["error"]


def test_feedback_level_validation(client, social_setup, app):
    """Endpoints reject invalid level parameters with 400."""
    headers = get_headers(app, social_setup["u1_id"])

    response = client.post(
        "/api/feedback/invalidlevel/1",
        json={"rating": 5},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Invalid level" in response.json["error"]


def test_feedback_rating_validation(client, social_setup, app):
    """POST feedback validates rating values and types."""
    headers = get_headers(app, social_setup["u1_id"])
    work_id = social_setup["work_id"]

    # Rating too high
    response = client.post(
        f"/api/feedback/work/{work_id}",
        json={"rating": 6, "comment": "Too good"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Rating must be between 1 and 5" in response.json["error"]

    # Rating not an integer
    response = client.post(
        f"/api/feedback/work/{work_id}",
        json={"rating": "excellent"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Rating must be a valid integer" in response.json["error"]


def test_work_level_feedback_lifecycle(client, social_setup, app):
    """Comprehensive test of GET, POST, and DELETE feedback at Work level."""
    u1_headers = get_headers(app, social_setup["u1_id"])
    u2_headers = get_headers(app, social_setup["u2_id"])
    work_id = social_setup["work_id"]

    # 1. Critic One posts 5-star review
    response = client.post(
        f"/api/feedback/work/{work_id}",
        json={"rating": 5, "comment": "A masterpiece of narrative design!"},
        headers=u1_headers,
    )
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["data"]["rating"] == 5

    # 2. Critic Two posts 3-star review
    response = client.post(
        f"/api/feedback/work/{work_id}",
        json={"rating": 3, "comment": "Interesting but a bit slow."},
        headers=u2_headers,
    )
    assert response.status_code == 200

    # 3. GET feedback lists reviews and computes averages
    response = client.get(f"/api/feedback/work/{work_id}")
    assert response.status_code == 200
    assert response.json["success"] is True
    assert len(response.json["feedbacks"]) == 2
    assert response.json["stats"]["average_rating"] == 4.0
    assert response.json["stats"]["total_ratings"] == 2
    assert response.json["stats"]["rating_counts"]["5"] == 1
    assert response.json["stats"]["rating_counts"]["3"] == 1

    # 4. Critic One updates review to 4-star
    response = client.post(
        f"/api/feedback/work/{work_id}",
        json={"rating": 4, "comment": "Updated thoughts: still great, but not perfect."},
        headers=u1_headers,
    )
    assert response.status_code == 200

    # 5. Verify average and reviews list updated
    response = client.get(f"/api/feedback/work/{work_id}")
    assert response.json["stats"]["average_rating"] == 3.5
    assert response.json["stats"]["rating_counts"]["4"] == 1
    assert response.json["stats"]["rating_counts"]["5"] == 0

    # 6. Critic One deletes review
    response = client.delete(f"/api/feedback/work/{work_id}", headers=u1_headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    # 7. Verify review deleted in list and stats updated
    response = client.get(f"/api/feedback/work/{work_id}")
    assert len(response.json["feedbacks"]) == 1
    assert response.json["stats"]["average_rating"] == 3.0


def test_other_frbr_levels_feedback(client, social_setup, app):
    """Verify feedback CRUD functions properly on Expression, Manifestation, and Item levels."""
    headers = get_headers(app, social_setup["u1_id"])
    expr_id = social_setup["expression_id"]
    manif_id = social_setup["manifestation_id"]
    item_id = social_setup["item_id"]

    # Expression Feedback
    response = client.post(
        f"/api/feedback/expression/{expr_id}",
        json={"rating": 4, "comment": "Great English translation!"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json["data"]["comment"] == "Great English translation!"

    # Manifestation Feedback
    response = client.post(
        f"/api/feedback/manifestation/{manif_id}",
        json={"rating": 5, "comment": "Stunning hardcover packaging and paper quality!"},
        headers=headers,
    )
    assert response.status_code == 200

    # Item Feedback (Personal Copy Notes)
    response = client.post(
        f"/api/feedback/item/{item_id}",
        json={"rating": 3, "comment": "My personal copy has some notes on page 42."},
        headers=headers,
    )
    assert response.status_code == 200

    # Verify all list correctly
    for level, target_id, expected_rating in [
        ("expression", expr_id, 4),
        ("manifestation", manif_id, 5),
        ("item", item_id, 3),
    ]:
        res = client.get(f"/api/feedback/{level}/{target_id}")
        assert res.status_code == 200
        assert len(res.json["feedbacks"]) == 1
        assert res.json["stats"]["average_rating"] == expected_rating


def test_cascading_deletes_reviews(social_setup, app):
    """Verify reviews cascade delete correctly when target resources are deleted."""
    with app.app_context():
        u1_id = social_setup["u1_id"]
        work_id = social_setup["work_id"]

        # Add feedbacks
        f1 = SocialFeedback(user_id=u1_id, work_id=work_id, rating=5, comment="Love it")
        db.session.add(f1)
        db.session.commit()
        f1_id = f1.id

        # Delete the Work
        work = db.session.get(Work, work_id)
        db.session.delete(work)
        db.session.commit()

        # Feedback should be deleted automatically by cascade constraint
        feedback = db.session.get(SocialFeedback, f1_id)
        assert feedback is None
