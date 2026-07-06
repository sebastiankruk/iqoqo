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

"""Tests for social notes (comments/remarks) on FRBR levels."""

import pytest

from app.api.auth import generate_internal_jwt
from app.db import db
from app.db.models import Expression, Item, Manifestation, Permission, Role, SocialNote, User, Work


@pytest.fixture
def social_notes_setup(app):
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

        # Create user
        u1 = User(email="writer1@iqoqo.local", display_name="Writer One", public_username="writer1")
        u1.roles.append(user_role)
        db.session.add(u1)
        db.session.flush()

        # Create FRBR structure
        work = Work(title="Test Notes Conceptual Work", meta={"authors": ["Author Y"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780000000002", meta={"format": "book"})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=u1.id, status="reading", collection_status="available")
        db.session.add(item)
        db.session.flush()

        db.session.commit()
        return {
            "u1_id": u1.id,
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


def test_note_target_existence_check(client, social_notes_setup, app):
    """POST and GET returns 404 for nonexistent targets."""
    headers = get_headers(app, social_notes_setup["u1_id"])

    # Nonexistent work note POST
    response = client.post(
        "/api/notes/work/99999",
        json={"note": "Nice note"},
        headers=headers,
    )
    assert response.status_code == 404
    assert "Work not found" in response.json["error"]

    # Nonexistent expression note GET
    response = client.get("/api/notes/expression/99999")
    assert response.status_code == 404
    assert "Expression not found" in response.json["error"]


def test_note_level_validation(client, social_notes_setup, app):
    """Endpoints reject invalid level parameters with 400."""
    headers = get_headers(app, social_notes_setup["u1_id"])

    response = client.post(
        "/api/notes/invalidlevel/1",
        json={"note": "Hello"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Invalid level" in response.json["error"]


def test_note_validation(client, social_notes_setup, app):
    """POST/PUT notes validates content exists and is not empty."""
    headers = get_headers(app, social_notes_setup["u1_id"])
    work_id = social_notes_setup["work_id"]

    # Missing note content
    response = client.post(
        f"/api/notes/work/{work_id}",
        json={},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Missing note content" in response.json["error"]

    # Empty note content
    response = client.post(
        f"/api/notes/work/{work_id}",
        json={"note": "   "},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Note content cannot be empty" in response.json["error"]


def test_work_level_notes_lifecycle(client, social_notes_setup, app):
    """Comprehensive test of GET, POST, PUT, and DELETE for multiple notes."""
    headers = get_headers(app, social_notes_setup["u1_id"])
    work_id = social_notes_setup["work_id"]

    # 1. Post first note
    response = client.post(
        f"/api/notes/work/{work_id}",
        json={"note": "First note content"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json["success"] is True
    assert response.json["data"]["note"] == "First note content"
    note1_id = response.json["data"]["id"]

    # 2. Post second note for the same user and resource (verifying multiple notes allowed!)
    response = client.post(
        f"/api/notes/work/{work_id}",
        json={"note": "Second note content"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json["success"] is True
    assert response.json["data"]["note"] == "Second note content"
    note2_id = response.json["data"]["id"]

    # 3. GET notes lists both chronologically (newest first)
    response = client.get(f"/api/notes/work/{work_id}")
    assert response.status_code == 200
    assert response.json["success"] is True
    assert len(response.json["data"]) == 2
    assert response.json["data"][0]["id"] == note2_id
    assert response.json["data"][1]["id"] == note1_id

    # 4. Update the first note
    response = client.put(
        f"/api/notes/{note1_id}",
        json={"note": "First note updated content"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["data"]["note"] == "First note updated content"

    # 5. Delete the second note
    response = client.delete(f"/api/notes/{note2_id}", headers=headers)
    assert response.status_code == 200
    assert response.json["success"] is True

    # 6. Verify GET notes returns only the first updated note
    response = client.get(f"/api/notes/work/{work_id}")
    assert len(response.json["data"]) == 1
    assert response.json["data"][0]["note"] == "First note updated content"


def test_cascading_deletes_notes(social_notes_setup, app):
    """Verify notes cascade delete correctly when target resources are deleted."""
    with app.app_context():
        u1_id = social_notes_setup["u1_id"]
        work_id = social_notes_setup["work_id"]

        # Add note
        n1 = SocialNote(user_id=u1_id, work_id=work_id, note="To be deleted soon")
        db.session.add(n1)
        db.session.commit()
        n1_id = n1.id

        # Delete the Work
        work = db.session.get(Work, work_id)
        db.session.delete(work)
        db.session.commit()

        # Note should be deleted automatically by cascade constraint
        note = db.session.get(SocialNote, n1_id)
        assert note is None


def test_note_html_stripping(client, social_notes_setup, app):
    """POST note strips HTML tags from note content (only tags removed, text preserved)."""
    headers = get_headers(app, social_notes_setup["u1_id"])
    work_id = social_notes_setup["work_id"]

    response = client.post(
        f"/api/notes/work/{work_id}",
        json={"note": "Hello <script>alert('xss')</script> world"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json["data"]
    assert "<script>" not in data["note"]
    assert "Hello" in data["note"]
    assert "world" in data["note"]


def test_note_max_length(client, social_notes_setup, app):
    """POST note rejects content exceeding 2048 characters."""
    headers = get_headers(app, social_notes_setup["u1_id"])
    work_id = social_notes_setup["work_id"]

    # Exactly 2048 chars should succeed
    short_note = "x" * 2048
    response = client.post(
        f"/api/notes/work/{work_id}",
        json={"note": short_note},
        headers=headers,
    )
    assert response.status_code == 201

    # 2049 chars should fail
    long_note = "x" * 2049
    response = client.post(
        f"/api/notes/work/{work_id}",
        json={"note": long_note},
        headers=headers,
    )
    assert response.status_code == 400
