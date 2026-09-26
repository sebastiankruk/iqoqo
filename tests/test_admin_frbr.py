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

"""Tests for the FRBR entity management API endpoints."""

from app.core import frbr_service
from app.db.core import Expression, Item, Manifestation, Work, db


def test_get_frbr_tree_unauthorized(client):
    """Ensure unauthenticated users are blocked."""
    res = client.get("/api/v1/admin/frbr/tree/manifestation/1")
    assert res.status_code in [401, 403]


def test_get_frbr_tree_forbidden(client, normal_user_headers):
    """Ensure non-admin users get forbidden."""
    res = client.get("/api/v1/admin/frbr/tree/manifestation/1", headers=normal_user_headers)
    assert res.status_code in [401, 403]


def test_get_frbr_tree_not_found(client, admin_headers):
    """Ensure 404 is returned for non-existent manifestation."""
    res = client.get("/api/v1/admin/frbr/tree/manifestation/999999", headers=admin_headers)
    assert res.status_code == 404
    assert res.json["success"] is False


def test_get_frbr_tree_success(client, admin_headers, app):
    """Test fetching the full FRBR tree for a manifestation."""
    with app.app_context():
        # Create a complete FRBR hierarchy
        work = frbr_service.create_work(title="Test FRBR Book")
        expression = frbr_service.create_expression(work_id=work.id, content_type="text", language="en")
        manifestation = frbr_service.create_manifestation(
            expression_id=expression.id, isbn13="9781234567897", publisher="Test Publisher", meta={"TestMeta": "test_value"}
        )
        work_id = work.id
        manif_id = manifestation.id

    res = client.get(f"/api/v1/admin/frbr/tree/manifestation/{manif_id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True

    data = res.json["data"]
    assert data["work"]["title"] == "Test FRBR Book"
    assert data["work"]["id"] == work_id
    assert data["expression"]["content_type"] == "text"
    assert data["expression"]["language"] == "en"
    assert data["manifestation"]["isbn13"] == "9781234567897"
    assert data["manifestation"]["publisher"] == "Test Publisher"


def test_get_frbr_tree_with_items(client, admin_headers, app):
    """Test fetching FRBR tree including items."""
    with app.app_context():
        from app.db.models import User

        # Create work, expression, manifestation
        work = frbr_service.create_work(title="Book with Items")
        expression = frbr_service.create_expression(work_id=work.id)
        manifestation = frbr_service.create_manifestation(expression_id=expression.id, isbn13="111")

        # Get a test user for item ownership
        user = User.query.first()
        if not user:
            user = User(email="item_owner@iqoqo.local", display_name="Item Owner")
            db.session.add(user)
            db.session.commit()

        # Create items using direct Item creation to use UUID
        item1 = Item(manifestation_id=manifestation.id, owner_id=user.id, status="available", meta={})
        item2 = Item(manifestation_id=manifestation.id, owner_id=user.id, status="lent", meta={})
        db.session.add_all([item1, item2])
        db.session.commit()
        manif_id = manifestation.id

    res = client.get(f"/api/v1/admin/frbr/tree/manifestation/{manif_id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.json["data"]
    assert len(data["items"]) == 2

    # Sort items by status to ensure deterministic assertion
    items = sorted(data["items"], key=lambda x: x["status"])
    assert items[0]["status"] == "available"
    assert items[1]["status"] == "lent"


def test_update_work(client, admin_headers, app):
    """Test updating a Work entity."""
    with app.app_context():
        work = frbr_service.create_work(title="Original Title", meta={"original_key": "original_value"})
        work_id = work.id

    res = client.put(
        f"/api/v1/admin/frbr/work/{work_id}", json={"title": "Updated Title", "meta": {"new_key": "new_value"}}, headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["id"] == work_id

    # Verify the update in the database
    with app.app_context():
        updated_work = db.session.get(Work, work_id)
        assert updated_work.title == "Updated Title"
        assert updated_work.meta["original_key"] == "original_value"
        assert updated_work.meta["new_key"] == "new_value"


def test_update_expression(client, admin_headers, app):
    """Test updating an Expression entity."""
    with app.app_context():
        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id, content_type="text", language="en")
        expr_id = expression.id

    res = client.put(
        f"/api/v1/admin/frbr/expression/{expr_id}",
        json={"content_type": "audio", "language": "pl", "meta": {"TrackCount": 10}},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_expr = db.session.get(Expression, expr_id)
        assert updated_expr.content_type == "audio"
        assert updated_expr.language == "pl"
        assert updated_expr.meta["TrackCount"] == 10


def test_update_manifestation(client, admin_headers, app):
    """Test updating a Manifestation entity."""
    with app.app_context():
        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id)
        manifestation = frbr_service.create_manifestation(
            expression_id=expression.id, isbn13="9780000000000", publisher="Original Publisher"
        )
        manif_id = manifestation.id

    res = client.put(
        f"/api/v1/admin/frbr/manifestation/{manif_id}",
        json={"isbn13": "9781111111111", "publisher": "New Publisher", "meta": {"Pages": 300}},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_manif = db.session.get(Manifestation, manif_id)
        assert updated_manif.isbn13 == "9781111111111"
        assert updated_manif.publisher == "New Publisher"
        assert updated_manif.meta["Pages"] == 300


def test_update_item(client, admin_headers, app):
    """Test updating an Item entity."""
    with app.app_context():
        from app.db.models import User

        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id)
        manifestation = frbr_service.create_manifestation(expression_id=expression.id)

        user = User.query.first()
        if not user:
            user = User(email="item_test@iqoqo.local", display_name="Item Test")
            db.session.add(user)
            db.session.commit()

        # Use direct Item creation to use UUID
        item = Item(manifestation_id=manifestation.id, owner_id=user.id, status="available", condition="Like New", meta={})
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    res = client.put(
        f"/api/v1/admin/frbr/item/{item_id}",
        json={"status": "lent", "condition": "Fair", "meta": {"LentTo": "Friend"}},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_item = db.session.get(Item, item_id)
        assert updated_item.status == "lent"
        assert updated_item.condition == "Fair"
        assert updated_item.meta["LentTo"] == "Friend"


def test_update_work_not_found(client, admin_headers):
    """Test updating non-existent work returns 404."""
    res = client.put("/api/v1/admin/frbr/work/999999", json={"title": "New Title"}, headers=admin_headers)
    assert res.status_code == 404
    assert res.json["success"] is False


def test_update_expression_invalid_work(client, admin_headers, app):
    """Test updating expression with invalid work_id returns 404."""
    with app.app_context():
        work = frbr_service.create_work(title="Test Work")
        expression = frbr_service.create_expression(work_id=work.id)
        expr_id = expression.id

    res = client.put(f"/api/v1/admin/frbr/expression/{expr_id}", json={"work_id": 999999}, headers=admin_headers)
    assert res.status_code == 404
    assert res.json["success"] is False


def test_search_frbr_manifestation_by_isbn(client, admin_headers, app):
    """Test searching manifestations by ISBN."""
    with app.app_context():
        work = frbr_service.create_work(title="Searchable Book")
        expression = frbr_service.create_expression(work_id=work.id)
        frbr_service.create_manifestation(expression_id=expression.id, isbn13="9781234567897")

    res = client.get("/api/v1/admin/frbr/search?q=9781234567897&type=manifestation", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) >= 1
    assert res.json["data"][0]["isbn13"] == "9781234567897"


def test_search_frbr_manifestation_by_upc(client, admin_headers, app):
    """Test searching manifestations by UPC."""
    with app.app_context():
        work = frbr_service.create_work(title="UPC Book")
        expression = frbr_service.create_expression(work_id=work.id)
        frbr_service.create_manifestation(expression_id=expression.id, upc="123456789012")

    res = client.get("/api/v1/admin/frbr/search?q=123456789012&type=manifestation", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) >= 1
    assert res.json["data"][0]["upc"] == "123456789012"


def test_search_frbr_work_by_title(client, admin_headers, app):
    """Test searching works by title."""
    with app.app_context():
        frbr_service.create_work(title="Unique Work Title XYZ")

    res = client.get("/api/v1/admin/frbr/search?q=Unique Work Title XYZ&type=work", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert len(res.json["data"]) >= 1
    assert res.json["data"][0]["title"] == "Unique Work Title XYZ"


def test_search_frbr_empty_query(client, admin_headers):
    """Test search with empty query returns empty results."""
    res = client.get("/api/v1/admin/frbr/search?q=&type=manifestation", headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"] == []


def test_custodian_can_upload_manifestation_image(client, custodian_headers, app):
    """Custodian (write:metadata, NOT admin) can POST manifestation image."""
    from io import BytesIO

    with app.app_context():
        work = Work(title="Upload Image Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780000000300", meta={})
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    data = {"image": (BytesIO(b"fake-image-data"), "test.jpg"), "label": "back"}
    resp = client.post(
        f"/api/manifestations/{manif_id}/images",
        data=data,
        headers=custodian_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code in [200, 201, 400]  # 400 possible if image validation fails on fake data; 200/201 if it passes


# ---------------------------------------------------------------------------
# Contributor UX overhaul — structured contributions in API
# ---------------------------------------------------------------------------


def test_get_frbr_tree_includes_contributions(client, admin_headers, app):
    """get_frbr_tree should serialize contributions for each entity level."""
    from app.core.frbr_service import add_work_contribution, get_or_create_contributor

    with app.app_context():
        work = frbr_service.create_work(title="Contrib Tree Test")
        expr = frbr_service.create_expression(work_id=work.id, content_type="text")
        manif = frbr_service.create_manifestation(expression_id=expr.id, isbn13="9780000000999")

        contrib = get_or_create_contributor("Test Author")
        add_work_contribution(work_id=work.id, contributor_id=contrib.id, role="author", sequence=0)
        manif_id = manif.id

    res = client.get(f"/api/v1/admin/frbr/tree/manifestation/{manif_id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.json["data"]
    assert "contributions" in data["work"]
    assert len(data["work"]["contributions"]) == 1
    assert data["work"]["contributions"][0]["name"] == "Test Author"
    assert data["work"]["contributions"][0]["role"] == "author"


def test_get_frbr_tree_legacy_meta_fallback(client, admin_headers, app):
    """When no relational contributions exist, fall back to meta.authors."""
    with app.app_context():
        work = frbr_service.create_work(title="Legacy Meta Test", meta={"authors": ["Legacy Author"]})
        expr = frbr_service.create_expression(work_id=work.id, content_type="text")
        manif = frbr_service.create_manifestation(expression_id=expr.id, isbn13="9780000000888")
        manif_id = manif.id

    res = client.get(f"/api/v1/admin/frbr/tree/manifestation/{manif_id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.json["data"]
    # Fallback should parse legacy authors into contributions.
    assert len(data["work"]["contributions"]) == 1
    assert data["work"]["contributions"][0]["name"] == "Legacy Author"


def test_update_work_with_contributions(client, admin_headers, app):
    """PUT work should accept structured contributions."""
    from app.db.contributions import WorkContribution

    with app.app_context():
        work = frbr_service.create_work(title="Contrib Update Test")
        work_id = work.id

    payload = {
        "title": "Contrib Update Test",
        "contributions": [
            {"name": "New Author", "role": "author", "sequence": 0},
        ],
    }
    res = client.put(f"/api/v1/admin/frbr/work/{work_id}", json=payload, headers=admin_headers)
    assert res.status_code == 200

    with app.app_context():
        rows = WorkContribution.query.filter_by(work_id=work_id).all()
        assert len(rows) == 1
        assert rows[0].contributor.name == "New Author"


def test_update_expression_with_contributions(client, admin_headers, app):
    """PUT expression should accept structured contributions."""
    from app.db.contributions import ExpressionContribution

    with app.app_context():
        work = frbr_service.create_work(title="Expr Contrib Test")
        expr = frbr_service.create_expression(work_id=work.id, content_type="text")
        expr_id = expr.id

    payload = {
        "contributions": [
            {"name": "Narrator Name", "role": "narrator", "sequence": 0},
        ],
    }
    res = client.put(f"/api/v1/admin/frbr/expression/{expr_id}", json=payload, headers=admin_headers)
    assert res.status_code == 200

    with app.app_context():
        rows = ExpressionContribution.query.filter_by(expression_id=expr_id).all()
        assert len(rows) == 1
        assert rows[0].contributor.name == "Narrator Name"


def test_update_manifestation_with_contributions(client, admin_headers, app):
    """PUT manifestation should accept structured contributions."""
    from app.db.contributions import ManifestationContribution

    with app.app_context():
        work = frbr_service.create_work(title="Manif Contrib Test")
        expr = frbr_service.create_expression(work_id=work.id, content_type="text")
        manif = frbr_service.create_manifestation(expression_id=expr.id, isbn13="9780000000777")
        manif_id = manif.id

    payload = {
        "contributions": [
            {"name": "Big Publishing House", "role": "publisher", "sequence": 0},
        ],
    }
    res = client.put(f"/api/v1/admin/frbr/manifestation/{manif_id}", json=payload, headers=admin_headers)
    assert res.status_code == 200

    with app.app_context():
        rows = ManifestationContribution.query.filter_by(manifestation_id=manif_id).all()
        assert len(rows) == 1
        assert rows[0].contributor.name == "Big Publishing House"


# ---------------------------------------------------------------------------
# FRBR Relation Management Tests
# ---------------------------------------------------------------------------


def test_reassign_expression_to_different_work(client, admin_headers, app):
    """Test reassigning an Expression to a different Work."""
    with app.app_context():
        work1 = frbr_service.create_work(title="Original Work")
        work2 = frbr_service.create_work(title="Target Work")
        expr = frbr_service.create_expression(work_id=work1.id, content_type="text")
        expr_id = expr.id
        work2_id = work2.id

    res = client.post(
        "/api/v1/admin/frbr/relations/reassign",
        json={"entity_type": "expression", "entity_id": expr_id, "new_parent_id": work2_id},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_expr = db.session.get(Expression, expr_id)
        assert updated_expr.work_id == work2_id


def test_reassign_manifestation_to_different_expression(client, admin_headers, app):
    """Test reassigning a Manifestation to a different Expression."""
    with app.app_context():
        work = frbr_service.create_work(title="Test Work")
        expr1 = frbr_service.create_expression(work_id=work.id, content_type="text", language="en")
        expr2 = frbr_service.create_expression(work_id=work.id, content_type="text", language="pl")
        manif = frbr_service.create_manifestation(expression_id=expr1.id, isbn13="9781234567897")
        manif_id = manif.id
        expr2_id = expr2.id

    res = client.post(
        "/api/v1/admin/frbr/relations/reassign",
        json={"entity_type": "manifestation", "entity_id": manif_id, "new_parent_id": expr2_id},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_manif = db.session.get(Manifestation, manif_id)
        assert updated_manif.expression_id == expr2_id


def test_reassign_rejects_cross_level(client, admin_headers, app):
    """Test that cross-level reassignment is rejected."""
    with app.app_context():
        # Create extra entities so IDs don't collide across tables
        work_a = frbr_service.create_work(title="Work A")
        work_b = frbr_service.create_work(title="Work B")
        expr_a = frbr_service.create_expression(work_id=work_a.id, content_type="text")
        manif = frbr_service.create_manifestation(expression_id=expr_a.id)
        manif_id = manif.id
        # Use a work ID that does NOT exist as an expression ID
        # work_b.id is 2, but there's no expression with id=2
        work_b_id = work_b.id

    # Try to reassign a manifestation (should go to expression) to a work
    res = client.post(
        "/api/v1/admin/frbr/relations/reassign",
        json={"entity_type": "manifestation", "entity_id": manif_id, "new_parent_id": work_b_id},
        headers=admin_headers,
    )
    # Should fail because work_b_id does not exist as an Expression
    assert res.status_code == 400
    assert res.json["success"] is False


def test_reassign_unauthorized(client, normal_user_headers, app):
    """Test that unauthenticated/unauthorized users cannot reassign."""
    res = client.post(
        "/api/v1/admin/frbr/relations/reassign",
        json={"entity_type": "expression", "entity_id": 1, "new_parent_id": 2},
        headers=normal_user_headers,
    )
    assert res.status_code in [401, 403]


def test_merge_duplicate_works(client, admin_headers, app):
    """Test merging duplicate Works — children reparented, source deleted."""
    with app.app_context():
        work1 = frbr_service.create_work(title="Duplicate Work 1")
        work2 = frbr_service.create_work(title="Duplicate Work 2")
        frbr_service.create_expression(work_id=work1.id, content_type="text")
        expr2 = frbr_service.create_expression(work_id=work2.id, content_type="text")
        frbr_service.create_manifestation(expression_id=expr2.id)
        work1_id = work1.id
        work2_id = work2.id
        expr2_id = expr2.id

    res = client.post(
        "/api/v1/admin/frbr/relations/merge",
        json={"entity_type": "work", "source_id": work1_id, "target_id": work2_id},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        # Source should be deleted
        assert db.session.get(Work, work1_id) is None
        # Expression should be reparented to target
        db.session.get(Expression, expr2_id)
        # Actually expr1 should be reparented; let's check
        from sqlalchemy import select

        exprs = db.session.execute(select(Expression).filter_by(work_id=work2_id)).scalars().all()
        assert len(exprs) == 2  # Both expressions now under work2


def test_merge_duplicate_manifestations(client, admin_headers, app):
    """Test merging duplicate Manifestations — Items reparented."""
    with app.app_context():
        from app.db.models import User

        work = frbr_service.create_work(title="Merge Manif Test")
        expr = frbr_service.create_expression(work_id=work.id)
        manif1 = frbr_service.create_manifestation(expression_id=expr.id, isbn13="9780000000001")
        manif2 = frbr_service.create_manifestation(expression_id=expr.id, isbn13="9780000000002")

        user = User.query.first()
        if not user:
            user = User(email="merge_test@iqoqo.local", display_name="Merge Test")
            db.session.add(user)
            db.session.commit()

        item1 = Item(manifestation_id=manif1.id, owner_id=user.id, status="available", meta={})
        item2 = Item(manifestation_id=manif2.id, owner_id=user.id, status="available", meta={})
        db.session.add_all([item1, item2])
        db.session.commit()
        manif1_id = manif1.id
        manif2_id = manif2.id
        item1_id = item1.id

    res = client.post(
        "/api/v1/admin/frbr/relations/merge",
        json={"entity_type": "manifestation", "source_id": manif1_id, "target_id": manif2_id},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        # Source should be deleted
        assert db.session.get(Manifestation, manif1_id) is None
        # Item should be reparented to target
        item1_updated = db.session.get(Item, item1_id)
        assert item1_updated.manifestation_id == manif2_id


def test_split_work(client, admin_headers, app):
    """Test splitting a Work — selected Expressions moved to new Work."""
    with app.app_context():
        work = frbr_service.create_work(title="Original Work")
        expr1 = frbr_service.create_expression(work_id=work.id, content_type="text", language="en")
        expr2 = frbr_service.create_expression(work_id=work.id, content_type="text", language="pl")
        work_id = work.id
        expr1_id = expr1.id
        expr2_id = expr2.id

    res = client.post(
        "/api/v1/admin/frbr/relations/split",
        json={
            "entity_type": "work",
            "source_id": work_id,
            "child_ids": [expr2_id],
            "new_entity_attrs": {"title": "Split Work"},
        },
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json["success"] is True
    new_work_id = res.json["data"]["id"]

    with app.app_context():
        # Original work should still have expr1
        db.session.get(Work, work_id)
        exprs_on_original = db.session.execute(db.select(Expression).filter_by(work_id=work_id)).scalars().all()
        assert len(exprs_on_original) == 1
        assert exprs_on_original[0].id == expr1_id

        # New work should have expr2
        new_work = db.session.get(Work, new_work_id)
        assert new_work.title == "Split Work"
        exprs_on_new = db.session.execute(db.select(Expression).filter_by(work_id=new_work_id)).scalars().all()
        assert len(exprs_on_new) == 1
        assert exprs_on_new[0].id == expr2_id


def test_roadmap_item_single_frbr_level_constraint(client, normal_user_headers, app):
    """Test that roadmap items enforce exactly one FRBR level reference."""
    from sqlalchemy import select as sa_select

    from app.db.auth import User
    from app.db.roadmap import ReadingRoadmap

    with app.app_context():
        user = db.session.execute(sa_select(User).filter_by(email="test_user@iqoqo.local")).scalar_one()
        roadmap = ReadingRoadmap(user_id=user.id, title="Constraint Test")
        db.session.add(roadmap)
        db.session.commit()
        roadmap_id = roadmap.id

    # Test: no FRBR reference should fail
    res = client.post(
        f"/api/v1/roadmaps/{roadmap_id}/items",
        json={"notes": "No FRBR ref"},
        headers=normal_user_headers,
    )
    assert res.status_code == 400

    # Test: multiple FRBR references should fail
    res = client.post(
        f"/api/v1/roadmaps/{roadmap_id}/items",
        json={"work_id": 1, "expression_id": 2},
        headers=normal_user_headers,
    )
    assert res.status_code == 400

    # Test: exactly one FRBR reference should succeed
    res = client.post(
        f"/api/v1/roadmaps/{roadmap_id}/items",
        json={"work_id": 42, "notes": "Valid"},
        headers=normal_user_headers,
    )
    assert res.status_code == 201
