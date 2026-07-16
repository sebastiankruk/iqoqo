"""Tests for the DataManager class."""

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

# pylint: disable=redefined-outer-name  # pytest fixtures

import json

import pytest

from app.core.data_manager import DataManager
from app.db import db
from app.db.models import ITEM_STATUSES, Expression, Item, Manifestation, User, Work


@pytest.fixture
def sample_data():
    """Create sample FRBR data for testing."""
    return {
        "version": "1.0",
        "exported_at": "2026-01-30T12:00:00",
        "works": [{"id": 1, "title": "The Hobbit", "form": "novel", "date": "1937"}],
        "expressions": [{"id": 1, "work_id": 1, "language": "en", "expression_type": "text"}],
        "manifestations": [
            {
                "id": 1,
                "expression_id": 1,
                "isbn10": "0048230707",
                "isbn13": "9780048230706",
                "title": "The Hobbit",
                "publisher": "Allen & Unwin",
                "year": 1937,
            }
        ],
        "items": [{"id": 1, "manifestation_id": 1, "condition": "good", "location": "shelf-a", "notes": "First edition copy"}],
    }


def test_get_stats_empty(app):
    """Test getting stats from an empty database."""
    with app.app_context():
        stats = DataManager.get_stats()
        assert stats["works"] == 0
        assert stats["expressions"] == 0
        assert stats["manifestations"] == 0
        assert stats["items"] == 0
        assert stats["total_items"] == 0
        assert stats["lent_items"] == 0
        assert stats["to_read"] == 0
        # Every ITEM_STATUS value must appear as a per-status key
        for status in ITEM_STATUSES:
            assert f"items_{status}" in stats, f"Missing key 'items_{status}' in get_stats() result"
            assert stats[f"items_{status}"] == 0


def test_export_all_empty(app):
    """Test exporting from an empty database."""
    with app.app_context():
        data = DataManager.export_all()
        assert data["version"] == "1.0"
        assert "exported_at" in data
        assert not data["works"]
        assert not data["expressions"]
        assert not data["manifestations"]
        assert not data["items"]


def test_import_data(app, sample_data):
    """Test importing data into the database."""
    with app.app_context():
        result = DataManager.import_data(sample_data, clear_existing=False)

        assert result["works"] == 1
        assert result["expressions"] == 1
        assert result["manifestations"] == 1
        assert result["items"] == 1
        assert Work.query.count() == 1
        assert Expression.query.count() == 1
        assert Manifestation.query.count() == 1
        assert Item.query.count() == 1

        # Check the actual content
        work = Work.query.first()
        assert work.title == "The Hobbit"


def test_import_with_clear(app, sample_data):
    """Test importing with clear_existing=True."""
    with app.app_context():
        # First import
        DataManager.import_data(sample_data, clear_existing=False)
        assert Work.query.count() == 1

        # Second import with clear
        result = DataManager.import_data(sample_data, clear_existing=True)
        assert Work.query.count() == 1  # Should still be 1, not 2
        assert result["works"] == 1


def test_export_and_reimport(app, sample_data):
    """Test that exported data can be reimported."""
    with app.app_context():
        # Import original data
        DataManager.import_data(sample_data, clear_existing=False)

        # Export it
        exported = DataManager.export_all()

        # Clear and reimport
        DataManager.clear_all_data()
        assert Work.query.count() == 0

        result = DataManager.import_data(exported, clear_existing=False)

        # Verify counts match
        assert result["works"] == 1
        assert result["expressions"] == 1
        assert result["manifestations"] == 1
        assert result["items"] == 1


def test_export_to_file(app, sample_data, tmp_path):
    """Test exporting to a file."""
    with app.app_context():
        DataManager.import_data(sample_data, clear_existing=False)

        # Use a real file path
        filepath = tmp_path / "export.json"
        DataManager.export_to_file(str(filepath))

        # Verify the file contains valid JSON
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert len(data["works"]) == 1
        assert data["works"][0]["title"] == "The Hobbit"


def test_import_from_file(app, sample_data, tmp_path):
    """Test importing from a file."""
    with app.app_context():
        # Write sample data to a file
        filepath = tmp_path / "import.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        result = DataManager.import_from_file(str(filepath), clear_existing=False)

        assert result["works"] == 1
        assert Work.query.first().title == "The Hobbit"


def test_clear_all_data(app, sample_data):
    """Test clearing all data from the database."""
    with app.app_context():
        DataManager.import_data(sample_data, clear_existing=False)

        assert Work.query.count() == 1
        assert Expression.query.count() == 1

        DataManager.clear_all_data()

        assert Work.query.count() == 0
        assert Expression.query.count() == 0
        assert Manifestation.query.count() == 0
        assert Item.query.count() == 0


def test_import_foreign_key_remapping(app):
    """Test that foreign keys are correctly remapped during import."""
    with app.app_context():
        data = {
            "version": "1.0",
            "exported_at": "2026-01-30T12:00:00",
            "works": [{"id": 999, "title": "Test Work", "form": "novel"}],
            "expressions": [{"id": 888, "work_id": 999, "language": "en", "expression_type": "text"}],
            "manifestations": [{"id": 777, "expression_id": 888, "isbn13": "9781234567890", "title": "Test"}],
            "items": [{"id": 666, "manifestation_id": 777, "condition": "good"}],
        }

        DataManager.import_data(data, clear_existing=False)

        # The IDs should be reassigned, but relationships should be preserved
        work = Work.query.first()
        expression = Expression.query.first()
        manifestation = Manifestation.query.first()
        item = Item.query.first()

        assert expression.work_id == work.id
        assert manifestation.expression_id == expression.id
        assert item.manifestation_id == manifestation.id


def test_import_handles_missing_optional_fields(app):
    """Test that import handles missing optional fields gracefully."""
    with app.app_context():
        data = {
            "version": "1.0",
            "exported_at": "2026-01-30T12:00:00",
            "works": [
                {"id": 1, "title": "Minimal Work"}
                # form and date are optional
            ],
            "expressions": [
                {"id": 1, "work_id": 1}
                # language and expression_type are optional
            ],
            "manifestations": [
                {"id": 1, "expression_id": 1, "title": "Minimal Manifestation"}
                # Most fields are optional
            ],
            "items": [
                {"id": 1, "manifestation_id": 1}
                # All fields except manifestation_id are optional
            ],
        }

        result = DataManager.import_data(data, clear_existing=False)

        assert result["works"] == 1
        assert result["expressions"] == 1
        assert result["manifestations"] == 1
        assert result["items"] == 1


def test_stats_accuracy(app, sample_data):
    """Test that stats accurately reflect database state."""
    with app.app_context():
        # Add multiple records
        for i in range(3):
            sample_copy = json.loads(json.dumps(sample_data))
            sample_copy["works"][0]["id"] = i + 1
            sample_copy["works"][0]["title"] = f"Book {i + 1}"
            sample_copy["expressions"][0]["id"] = i + 1
            sample_copy["expressions"][0]["work_id"] = i + 1
            sample_copy["manifestations"][0]["id"] = i + 1
            sample_copy["manifestations"][0]["expression_id"] = i + 1
            sample_copy["manifestations"][0]["isbn13"] = f"978000000000{i}"
            sample_copy["items"][0]["id"] = i + 1
            sample_copy["items"][0]["manifestation_id"] = i + 1

            DataManager.import_data(sample_copy, clear_existing=False)

        stats = DataManager.get_stats()
        assert stats["works"] == 3
        assert stats["expressions"] == 3
        assert stats["manifestations"] == 3
        assert stats["items"] == 3


def test_get_stats_per_status_counts(app):
    """Test that get_stats() returns correct per-status counts for all ITEM_STATUSES."""
    with app.app_context():
        test_user = User(email="frontend_test@iqoqo.local", display_name="Frontend Tester")
        db.session.add(test_user)
        db.session.commit()  # Commit to generate the UUID

        # Build the minimum FRBR chain required to attach Items
        work = Work(title="Status Test Work", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        # Create two items for each status so we can assert counts > 0
        for status in ITEM_STATUSES:
            for _ in range(2):
                db.session.add(Item(manifestation_id=manif.id, owner_id=test_user.id, status=status, collection_status="dummy", meta={}))
        db.session.commit()

        stats = DataManager.get_stats()

        total_items = len(ITEM_STATUSES) * 2
        assert stats["items"] == total_items
        assert stats["total_items"] == total_items
        assert stats["lent_items"] == 2
        assert stats["to_read"] == 2  # wish_list

        for status in ITEM_STATUSES:
            key = f"items_{status}"
            assert key in stats, f"Missing key {key!r} in get_stats() result"
            assert stats[key] == 2, f"Expected 2 items with status {status!r}, got {stats[key]}"


def test_get_stats_owner_scopes_frbr_counts(app):
    """FRBR entity counts must be user-scoped when owner_id is supplied.

    Two users each own items from a *different* FRBR chain.  Calling
    get_stats(owner_id=user_a.id) must return FRBR counts of 1 for that user
    even though the global database totals are 2.
    """
    with app.app_context():
        user_a = User(email="user_a@iqoqo.local", display_name="User A")
        user_b = User(email="user_b@iqoqo.local", display_name="User B")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        def _make_frbr_chain(title: str, isbn: str):
            work = Work(title=title, meta={})
            db.session.add(work)
            db.session.flush()
            expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
            db.session.add(expr)
            db.session.flush()
            manif = Manifestation(expression_id=expr.id, isbn13=isbn, meta={})
            db.session.add(manif)
            db.session.flush()
            return manif

        manif_a = _make_frbr_chain("Book A", "9780000000001")
        manif_b = _make_frbr_chain("Book B", "9780000000002")

        db.session.add(Item(manifestation_id=manif_a.id, owner_id=user_a.id, status="available", meta={}))
        db.session.add(Item(manifestation_id=manif_b.id, owner_id=user_b.id, status="available", meta={}))
        db.session.commit()

        # Global (no owner_id) — should see both chains
        global_stats = DataManager.get_stats()
        assert global_stats["works"] == 2
        assert global_stats["expressions"] == 2
        assert global_stats["manifestations"] == 2
        assert global_stats["items"] == 2

        # Scoped to user_a — should only see chain A
        stats_a = DataManager.get_stats(owner_id=user_a.id)
        assert stats_a["works"] == 1, f"Expected 1 work for user_a, got {stats_a['works']}"
        assert stats_a["expressions"] == 1, f"Expected 1 expression for user_a, got {stats_a['expressions']}"
        assert stats_a["manifestations"] == 1, f"Expected 1 manifestation for user_a, got {stats_a['manifestations']}"
        assert stats_a["items"] == 1
        assert stats_a["total_items"] == 1

        # Scoped to user_b — should only see chain B
        stats_b = DataManager.get_stats(owner_id=user_b.id)
        assert stats_b["works"] == 1, f"Expected 1 work for user_b, got {stats_b['works']}"
        assert stats_b["expressions"] == 1
        assert stats_b["manifestations"] == 1
        assert stats_b["items"] == 1


def test_get_stats_owner_shared_manifestation(app):
    """When two users own items from the *same* manifestation, user-scoped counts
    must still be 1 (not 2) for manifestations/expressions/works — i.e. DISTINCT
    is applied correctly.
    """
    with app.app_context():
        user_a = User(email="shared_a@iqoqo.local", display_name="Shared A")
        user_b = User(email="shared_b@iqoqo.local", display_name="Shared B")
        db.session.add_all([user_a, user_b])
        db.session.commit()

        work = Work(title="Shared Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780000000099", meta={})
        db.session.add(manif)
        db.session.flush()

        # Both users own a copy of *the same* manifestation
        db.session.add(Item(manifestation_id=manif.id, owner_id=user_a.id, status="available", meta={}))
        db.session.add(Item(manifestation_id=manif.id, owner_id=user_a.id, status="lent", meta={}))
        db.session.add(Item(manifestation_id=manif.id, owner_id=user_b.id, status="available", meta={}))
        db.session.commit()

        stats_a = DataManager.get_stats(owner_id=user_a.id)
        # user_a has 2 items but they all point to the same manifestation/expression/work
        assert stats_a["items"] == 2
        assert stats_a["manifestations"] == 1, f"Expected 1 distinct manifestation, got {stats_a['manifestations']}"
        assert stats_a["expressions"] == 1
        assert stats_a["works"] == 1


# ---------------------------------------------------------------------------
# DataManager.get_faceted_stats() tests
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_faceted_data(app):
    """Seed DB with items across categories, formats, tags, collections for faceted stats testing."""
    with app.app_context():
        user = User(email="facet_test@iqoqo.local", display_name="Facet Tester")
        db.session.add(user)
        db.session.flush()

        # Text book — available
        w1 = Work(title="Test Book", meta={"genres": ["Fantasy", "Science Fiction"]})
        db.session.add(w1)
        db.session.flush()
        e1 = Expression(work_id=w1.id, content_type="text")
        db.session.add(e1)
        db.session.flush()
        m1 = Manifestation(expression_id=e1.id, meta={"format": "book"}, publisher="Penguin")
        db.session.add(m1)
        db.session.flush()
        i1 = Item(manifestation_id=m1.id, owner_id=user.id, status="unread", collection_status="available")
        db.session.add(i1)
        db.session.flush()

        # Text book — lent
        i2 = Item(manifestation_id=m1.id, owner_id=user.id, status="read", collection_status="lent")
        db.session.add(i2)
        db.session.flush()

        # Music CD
        w2 = Work(title="Test Album", meta={"genres": ["Rock"]})
        db.session.add(w2)
        db.session.flush()
        e2 = Expression(work_id=w2.id, content_type="music")
        db.session.add(e2)
        db.session.flush()
        m2 = Manifestation(expression_id=e2.id, meta={"format": "cd"}, publisher="Columbia")
        db.session.add(m2)
        db.session.flush()
        i3 = Item(manifestation_id=m2.id, owner_id=user.id, status="want_to_listen", collection_status="available")
        db.session.add(i3)
        db.session.flush()

        # Tags
        from app.db.models import ItemTag, Tag

        tag = Tag(name="english")
        db.session.add(tag)
        db.session.flush()
        db.session.add(ItemTag(item_id=i1.id, tag_id=tag.id, added_by_id=user.id))

        # Collection
        from app.db.models import UserCollection, UserCollectionItem

        col = UserCollection(owner_id=user.id, name="Favorites")
        db.session.add(col)
        db.session.flush()
        db.session.add(UserCollectionItem(collection_id=col.id, item_id=i1.id))

        db.session.commit()
        return user.id


def test_get_faceted_stats_unfiltered(app_with_faceted_data, app):
    """get_faceted_stats without filters returns all counts."""
    with app.app_context():
        stats = DataManager.get_faceted_stats(owner_id=app_with_faceted_data)

    assert stats["category_counts"].get("text") == 2
    assert stats["category_counts"].get("music") == 1
    assert stats["format_counts"].get("book") == 2
    assert stats["format_counts"].get("cd") == 1
    assert stats["status_counts"].get("available") == 2
    assert stats["status_counts"].get("lent") == 1
    assert stats["tag_counts"].get("english") == 1
    assert stats["genre_counts"].get("Fantasy") == 1
    assert stats["genre_counts"].get("Rock") == 1
    assert stats["collection_counts"].get("Favorites") == 1
    assert stats["publisher_counts"].get("Penguin") == 2


def test_get_faceted_stats_filtered_by_category(app_with_faceted_data, app):
    """get_faceted_stats with category filter narrows all facet counts."""
    with app.app_context():
        stats = DataManager.get_faceted_stats(owner_id=app_with_faceted_data, category="text")

    assert stats["category_counts"].get("text") == 2
    assert stats["category_counts"].get("music") == 1
    assert stats["format_counts"].get("book") == 2
    assert stats["format_counts"].get("cd", 0) == 0
    assert stats["genre_counts"].get("Fantasy") == 1
    assert stats["genre_counts"].get("Rock", 0) == 0


def test_get_faceted_stats_filtered_by_genre(app_with_faceted_data, app):
    """get_faceted_stats with genre filter narrows category/format counts."""
    with app.app_context():
        stats = DataManager.get_faceted_stats(owner_id=app_with_faceted_data, genres=["Rock"])

    assert stats["category_counts"].get("music") == 1
    assert stats["category_counts"].get("text", 0) == 0
    assert stats["format_counts"].get("cd") == 1
    assert stats["format_counts"].get("book", 0) == 0


def test_get_faceted_stats_multiselect_same_facet(app_with_faceted_data, app):
    """Selecting one genre does not zero out other genres' counts."""
    with app.app_context():
        stats = DataManager.get_faceted_stats(owner_id=app_with_faceted_data, genres=["Fantasy"])

    assert stats["genre_counts"].get("Fantasy") == 1
    assert stats["genre_counts"].get("Science Fiction") == 1
    assert stats["genre_counts"].get("Rock") == 1
    assert stats["category_counts"].get("text") == 2
    assert stats["category_counts"].get("music", 0) == 0
    assert stats["format_counts"].get("book") == 2
    assert stats["format_counts"].get("cd", 0) == 0


def test_get_faceted_stats_filtered_by_tag(app_with_faceted_data, app):
    """get_faceted_stats with tag filter narrows all counts."""
    with app.app_context():
        stats = DataManager.get_faceted_stats(owner_id=app_with_faceted_data, tags=["english"])

    assert stats["category_counts"].get("text") == 1
    assert stats["category_counts"].get("music", 0) == 0
    assert stats["tag_counts"].get("english") == 1


def test_get_faceted_stats_empty_filters(app):
    """get_faceted_stats with valid user_id but no items returns zeros/empty."""
    with app.app_context():
        user = User(email="empty_test@iqoqo.local", display_name="Empty")
        db.session.add(user)
        db.session.flush()
        stats = DataManager.get_faceted_stats(owner_id=user.id)

    assert not stats["category_counts"]
    assert not stats["format_counts"]
    assert all(v == 0 for v in stats["status_counts"].values())
    assert not stats["tag_counts"]
    assert not stats["genre_counts"]
