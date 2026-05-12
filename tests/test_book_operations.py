"""Tests for scanning, adding, and updating book operations."""

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

# cSpell:ignore Aldous Vlissides sess

from unittest.mock import patch

import pytest

from app.db.models import Expression, Item, Manifestation, User, Work, db

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally
# pylint: disable=unused-argument  # fixtures used for setup, not always referenced


@pytest.fixture
def sample_work_complete(app):
    """Create a complete FRBRoo structure with Work, Expression, Manifestation, and Item."""
    with app.app_context():
        test_user = User(email="frontend_test@iqoqo.local", display_name="Frontend Tester")
        db.session.add(test_user)
        db.session.commit()  # Commit to generate the UUID

        # Create Work
        work = Work(
            title="The Lord of the Rings",
            meta={"authors": ["J.R.R. Tolkien"], "categories": ["Fantasy"]},
        )
        db.session.add(work)
        db.session.flush()

        # Create Expression
        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        # Create Manifestation
        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13="9780544003415",
            meta={"Title": "The Lord of the Rings", "Authors": ["J.R.R. Tolkien"]},
        )
        db.session.add(manifestation)
        db.session.flush()

        # Create Item
        item = Item(manifestation_id=manifestation.id, owner_id=test_user.id, status="want_to_read", collection_status="available", meta={})
        db.session.add(item)
        db.session.commit()

        yield {"work": work, "expression": expression, "manifestation": manifestation, "item": item, "user": test_user}


# =============================================================================
# ISBN Scanning Tests
# =============================================================================


class TestISBNScanning:
    """Test suite for ISBN scanning and lookup functionality."""

    def test_scan_existing_book_in_database(self, client, sample_work_complete):
        """Test scanning an ISBN that already exists in the database."""
        response = client.get("/api/isbn/9780544003415")
        assert response.status_code == 200
        data = response.json
        assert data["Title"] == "The Lord of the Rings"
        assert data["Authors"] == ["J.R.R. Tolkien"]

    def test_scan_isbn_with_metadata_in_manifestation(self, client, app):
        """Test scanning when metadata is stored in manifestation.meta."""
        with app.app_context():
            work = Work(title="Test Book", meta={"authors": ["Test Author"]})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
            db.session.add(expression)
            db.session.flush()

            manifestation = Manifestation(
                expression_id=expression.id,
                isbn13="9781234567890",
                meta={"Title": "Test Book", "Authors": ["Test Author"]},
            )
            db.session.add(manifestation)
            db.session.commit()

        response = client.get("/api/isbn/9781234567890")
        assert response.status_code == 200
        assert response.json["Title"] == "Test Book"

    def test_scan_isbn_without_metadata_builds_from_work(self, client, app):
        """Test scanning when metadata needs to be built from Work/Expression."""
        with app.app_context():
            work = Work(title="Minimal Book", meta={"authors": ["Minimal Author"]})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
            db.session.add(expression)
            db.session.flush()

            # Create manifestation WITHOUT metadata in meta field
            manifestation = Manifestation(expression_id=expression.id, isbn13="9789876543210", meta={})
            db.session.add(manifestation)
            db.session.commit()

        response = client.get("/api/isbn/9789876543210")
        assert response.status_code == 200
        data = response.json
        assert data["Title"] == "Minimal Book"
        assert data["Authors"] == ["Minimal Author"]

        # Verify manifestation.meta was updated
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9789876543210").first()
            assert manifestation.meta["Title"] == "Minimal Book"
            assert manifestation.meta["Authors"] == ["Minimal Author"]

    @patch("app.utils.isbn.fetch_isbn_metadata")
    def test_scan_new_isbn_from_open_library(self, mock_fetch, client):
        """Test scanning a new ISBN fetches from external sources and creates FRBR structure."""
        mock_fetch.return_value = {"Title": "Brave New World", "Authors": ["Aldous Huxley"]}

        response = client.get("/api/isbn/9780060850524")
        assert response.status_code == 200
        data = response.json
        assert data["Title"] == "Brave New World"
        assert data["Authors"] == ["Aldous Huxley"]

        # Verify complete FRBR structure was created
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780060850524").first()
            assert manifestation is not None
            assert manifestation.meta["Title"] == "Brave New World"

            expression = manifestation.expression
            assert expression is not None
            assert expression.content_type == "text"
            assert expression.language == "en"

            work = expression.work
            assert work is not None
            assert work.title == "Brave New World"
            assert work.meta["authors"] == ["Aldous Huxley"]

    @patch("app.utils.isbn.fetch_isbn_metadata")
    def test_scan_isbn_fetches_from_external_source(self, mock_fetch, client):
        """Test scanning a new ISBN fetches metadata from external sources (Google Books / Open Library)."""
        mock_fetch.return_value = {
            "Title": "The Catcher in the Rye",
            "Authors": ["J.D. Salinger"],
        }

        response = client.get("/api/isbn/9780316769488")
        assert response.status_code == 200
        data = response.json
        assert data["Title"] == "The Catcher in the Rye"
        assert data["Authors"] == ["J.D. Salinger"]

        # Verify fetch_isbn_metadata was called with the canonical ISBN
        mock_fetch.assert_called_once_with("9780316769488")

        # Verify data was saved to database
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780316769488").first()
            assert manifestation is not None
            assert manifestation.expression.work.title == "The Catcher in the Rye"

    @patch("app.utils.isbn.fetch_isbn_metadata", return_value=None)
    def test_scan_nonexistent_isbn(self, mock_fetch, client):
        """Test scanning an ISBN not found in any upstream source returns 404."""
        # 9780000000002 is a valid ISBN-13 that is not present in the database.
        response = client.get("/api/isbn/9780000000002")
        assert response.status_code == 404
        assert response.json.get("error", None) == "Metadata not found for ISBN = 9780000000002"

    def test_scan_invalid_isbn(self, client):
        """Test scanning with invalid ISBN format."""
        response = client.get("/api/isbn/invalid-isbn")
        # The actual behavior depends on the validation logic
        # Current implementation passes it through, so it will return 404
        assert response.status_code in [400, 404]

    @patch("app.utils.isbn.fetch_isbn_metadata")
    def test_scan_creates_proper_frbr_hierarchy(self, mock_fetch, client):
        """Test that scanning creates proper Work -> Expression -> Manifestation hierarchy."""
        mock_fetch.return_value = {"Title": "Pride and Prejudice", "Authors": ["Jane Austen"]}

        response = client.get("/api/isbn/9780141439518")
        assert response.status_code == 200

        with client.application.app_context():
            # Check Manifestation
            manifestation = Manifestation.query.filter_by(isbn13="9780141439518").first()
            assert manifestation is not None

            # Check Expression exists and links correctly
            expression = Expression.query.filter_by(id=manifestation.expression_id).first()
            assert expression is not None
            assert expression.id == manifestation.expression_id

            # Check Work exists and links correctly
            work = Work.query.filter_by(id=expression.work_id).first()
            assert work is not None
            assert work.id == expression.work_id
            assert work.title == "Pride and Prejudice"

    @patch("app.utils.isbn.fetch_isbn_metadata")
    def test_scan_multiple_authors(self, mock_fetch, client):
        """Test scanning a book with multiple authors."""
        mock_fetch.return_value = {
            "Title": "Design Patterns",
            "Authors": ["Erich Gamma", "Richard Helm", "Ralph Johnson", "John Vlissides"],
        }

        response = client.get("/api/isbn/9780201633610")
        assert response.status_code == 200
        data = response.json
        assert len(data["Authors"]) == 4
        assert "Erich Gamma" in data["Authors"]
        assert "John Vlissides" in data["Authors"]


# =============================================================================
# Adding Books Tests
# =============================================================================


class TestAddingBooks:
    """Test suite for adding books and items."""

    def test_add_item_to_existing_manifestation(self, client, sample_work_complete, normal_user_headers):
        """Test adding an item to an existing manifestation."""
        metadata = {"Title": "The Lord of the Rings", "Authors": ["J.R.R. Tolkien"]}
        response = client.post("/api/item/9780544003415", json=metadata, headers=normal_user_headers, content_type="application/json")
        assert response.status_code == 200
        data = response.json
        assert "item_id" in data["data"]

        # Verify new item was created (should be 2 total now)
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            items = Item.query.filter_by(manifestation_id=manifestation.id).all()
            assert len(items) == 2

    def test_add_item_creates_manifestation_if_not_exists(self, client, normal_user_headers):
        """Test adding item creates manifestation structure if ISBN doesn't exist."""
        with patch("app.utils.isbn.fetch_isbn_metadata") as mock_fetch:
            mock_fetch.return_value = {"Title": "The Catcher in the Rye", "Authors": ["J.D. Salinger"]}

            metadata = {"Title": "The Catcher in the Rye", "Authors": ["J.D. Salinger"]}
            response = client.post("/api/item/9780316769174", json=metadata, headers=normal_user_headers, content_type="application/json")
            assert response.status_code == 200

        # Verify complete FRBR structure was created
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780316769174").first()
            assert manifestation is not None

            items = Item.query.filter_by(manifestation_id=manifestation.id).all()
            assert len(items) == 1

            work = manifestation.expression.work
            assert work.title == "The Catcher in the Rye"

    def test_add_item_with_metadata_update(self, client, sample_work_complete, normal_user_headers):
        """Test adding item with metadata updates the manifestation."""
        new_metadata = {"Title": "Updated Title", "Authors": ["Updated Author"]}
        response = client.post("/api/item/9780544003415", json=new_metadata, headers=normal_user_headers, content_type="application/json")
        assert response.status_code == 200

        # Verify metadata was updated
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            # The metadata should be updated
            assert manifestation.meta["Title"] == "Updated Title"
            assert manifestation.meta["Authors"] == ["Updated Author"]
            # Work should also be updated
            assert manifestation.expression.work.title == "Updated Title"
            assert manifestation.expression.work.meta["authors"] == ["Updated Author"]

    def test_add_item_without_metadata(self, client, sample_work_complete, normal_user_headers):
        """Test adding item without providing metadata."""
        response = client.post("/api/item/9780544003415", json={}, headers=normal_user_headers, content_type="application/json")
        assert response.status_code == 200
        assert "item_id" in response.json["data"]

    def test_add_item_creates_correct_owner(self, client, sample_work_complete, normal_user_headers):
        """Test that adding an item associates it with correct owner."""
        response = client.post("/api/item/9780544003415", json={}, headers=normal_user_headers, content_type="application/json")
        assert response.status_code == 200

        with client.application.app_context():
            item = db.session.get(Item, response.json["data"]["item_id"])
            user = User.query.filter_by(email="test_user@iqoqo.local").first()
            assert item.owner_id == user.id

    def test_add_multiple_items_same_manifestation(self, client, sample_work_complete, normal_user_headers):
        """Test adding multiple items for the same manifestation."""
        # Add first item
        response1 = client.post("/api/item/9780544003415", json={}, headers=normal_user_headers, content_type="application/json")
        assert response1.status_code == 200
        item_id_1 = response1.json["data"]["item_id"]

        # Add second item
        response2 = client.post("/api/item/9780544003415", json={}, headers=normal_user_headers, content_type="application/json")
        assert response2.status_code == 200
        item_id_2 = response2.json["data"]["item_id"]

        # Verify both items exist and are different
        assert item_id_1 != item_id_2

        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            items = Item.query.filter_by(manifestation_id=manifestation.id).all()
            assert len(items) == 3  # Original + 2 new ones

    @patch("app.utils.isbn.fetch_isbn_metadata", return_value=None)
    def test_add_item_nonexistent_isbn_fails(self, mock_fetch, client, normal_user_headers):
        """Test adding item for a valid ISBN not found in any upstream source fails."""
        response = client.post("/api/item/9780000000002", json={}, headers=normal_user_headers, content_type="application/json")
        assert response.status_code == 404

    def test_add_item_sets_default_status(self, client, sample_work_complete, normal_user_headers):
        """Test that adding an item sets default status to 'available'."""
        response = client.post("/api/item/9780544003415", json={}, headers=normal_user_headers, content_type="application/json")
        assert response.status_code == 200

        with client.application.app_context():
            item = db.session.get(Item, response.json["data"]["item_id"])
            assert item.status == "want_to_read"
            assert item.collection_status == "available"

    def test_add_manual_item(self, client, normal_user_headers):
        """Test adding an item manually."""
        metadata = {"Title": "Manual Book", "Authors": ["Manual Author"], "Format": "text"}
        response = client.post("/api/items/manual", json=metadata, headers=normal_user_headers, content_type="application/json")
        assert response.status_code == 200
        assert response.json["success"] is True
        assert "item_id" in response.json["data"]

        with client.application.app_context():
            item = db.session.get(Item, response.json["data"]["item_id"])
            assert item is not None
            assert item.manifestation.expression.work.title == "Manual Book"

    @pytest.mark.parametrize(
        ("payload", "content_type"),
        [
            ('{"Title": "Invalid JSON"', "application/json"),
            (None, "application/json"),
        ],
    )
    def test_add_manual_item_invalid_json(self, client, payload, content_type, normal_user_headers):
        """Test adding manual item with invalid JSON payload fails."""
        request_kwargs = {"content_type": content_type, "headers": normal_user_headers}
        if payload is not None:
            request_kwargs["data"] = payload

        response = client.post("/api/items/manual", **request_kwargs)
        assert response.status_code == 400
        assert response.json["success"] is False
        assert response.json["error"] == "Invalid or missing JSON payload"


# =============================================================================
# Updating Books Tests
# =============================================================================


class TestUpdatingBooks:
    """Test suite for updating book metadata."""

    def test_update_manifestation_title(self, client, sample_work_complete, admin_headers):
        """Test updating only the title of a manifestation."""
        new_data = {"Title": "The Lord of the Rings: Updated Edition"}
        response = client.post("/api/isbn/9780544003415", json=new_data, headers=admin_headers, content_type="application/json")
        assert response.status_code == 200
        assert response.json["status"] == "ok"

        # Verify update in database
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            assert manifestation.meta["Title"] == "The Lord of the Rings: Updated Edition"
            assert manifestation.expression.work.title == "The Lord of the Rings: Updated Edition"

    def test_update_manifestation_authors(self, client, sample_work_complete, admin_headers):
        """Test updating only the authors of a manifestation."""
        new_data = {"Authors": ["J.R.R. Tolkien", "Christopher Tolkien"]}
        response = client.post("/api/isbn/9780544003415", json=new_data, headers=admin_headers, content_type="application/json")
        assert response.status_code == 200

        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            assert manifestation.meta["Authors"] == ["J.R.R. Tolkien", "Christopher Tolkien"]
            assert manifestation.expression.work.meta["authors"] == ["J.R.R. Tolkien", "Christopher Tolkien"]

    def test_update_manifestation_complete_metadata(self, client, sample_work_complete, admin_headers):
        """Test updating complete metadata of a manifestation."""
        new_data = {
            "Title": "Completely New Title",
            "Authors": ["New Author 1", "New Author 2"],
            "Publisher": "New Publisher",
            "Year": "2025",
        }
        response = client.post("/api/isbn/9780544003415", json=new_data, headers=admin_headers, content_type="application/json")
        assert response.status_code == 200

        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            assert manifestation.meta["Title"] == "Completely New Title"
            assert manifestation.meta["Authors"] == ["New Author 1", "New Author 2"]
            assert manifestation.meta["Publisher"] == "New Publisher"
            assert manifestation.meta["Year"] == "2025"

    def test_update_nonexistent_manifestation(self, client, admin_headers):
        """Test updating a non-existent manifestation returns 404."""
        new_data = {"Title": "This Should Fail"}
        response = client.post("/api/isbn/9999999999999", json=new_data, headers=admin_headers, content_type="application/json")
        assert response.status_code == 404
        assert "error" in response.json

    def test_update_without_metadata(self, client, sample_work_complete, admin_headers):
        """Test updating without providing metadata returns 400."""
        # When no JSON data is provided
        response = client.post("/api/isbn/9780544003415", json={}, headers=admin_headers, content_type="application/json")
        assert response.status_code == 400
        # Empty dict should also trigger error
        if response.json:
            assert "error" in response.json

    def test_update_with_empty_metadata(self, client, sample_work_complete, admin_headers):
        """Test updating with empty metadata returns 400."""
        response = client.post("/api/isbn/9780544003415", json={}, headers=admin_headers, content_type="application/json")
        assert response.status_code == 400

    def test_update_preserves_existing_metadata(self, client, app, admin_headers):
        """Test that updating preserves other metadata fields."""
        with app.app_context():
            work = Work(title="Original Title", meta={"authors": ["Original Author"]})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
            db.session.add(expression)
            db.session.flush()

            manifestation = Manifestation(
                expression_id=expression.id,
                isbn13="9781111111111",
                meta={"Title": "Original Title", "Authors": ["Original Author"], "Publisher": "Original Publisher"},
            )
            db.session.add(manifestation)
            db.session.commit()

        # Update only the title
        new_data = {"Title": "Updated Title"}
        response = client.post("/api/isbn/9781111111111", json=new_data, headers=admin_headers, content_type="application/json")
        assert response.status_code == 200

        # Verify Publisher is still there
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9781111111111").first()
            assert manifestation.meta["Title"] == "Updated Title"
            assert manifestation.meta["Publisher"] == "Original Publisher"
            assert manifestation.meta["Authors"] == ["Original Author"]

    def test_update_work_metadata_syncs_with_manifestation(self, client, sample_work_complete, admin_headers):
        """Test that updating work metadata is reflected in manifestation."""
        new_data = {"Title": "Synced Title", "Authors": ["Synced Author"]}
        response = client.post("/api/isbn/9780544003415", json=new_data, headers=admin_headers, content_type="application/json")
        assert response.status_code == 200

        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            work = manifestation.expression.work

            # Both should be updated
            assert manifestation.meta["Title"] == "Synced Title"
            assert work.title == "Synced Title"
            assert manifestation.meta["Authors"] == ["Synced Author"]
            assert work.meta["authors"] == ["Synced Author"]

    def test_update_creates_meta_if_not_exists(self, client, app, admin_headers):
        """Test updating a manifestation that has no meta creates it."""
        with app.app_context():
            work = Work(title="No Meta", meta={"authors": []})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
            db.session.add(expression)
            db.session.flush()

            # Create manifestation with NULL meta
            manifestation = Manifestation(expression_id=expression.id, isbn13="9782222222222", meta=None)
            db.session.add(manifestation)
            db.session.commit()

        new_data = {"Title": "Now Has Meta"}
        response = client.post("/api/isbn/9782222222222", json=new_data, headers=admin_headers, content_type="application/json")
        assert response.status_code == 200

        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9782222222222").first()
            assert manifestation.meta is not None
            assert manifestation.meta["Title"] == "Now Has Meta"


# =============================================================================
# Getting Items Tests
# =============================================================================


class TestGettingItems:
    """Test suite for retrieving items by ISBN."""

    def test_get_items_by_isbn(self, client, sample_work_complete):
        """Test getting items for an existing ISBN."""
        response = client.get("/api/item/9780544003415")
        assert response.status_code == 200
        data = response.json
        assert "ids" in data
        assert len(data["ids"]) == 1

    def test_get_items_multiple_items(self, client, sample_work_complete):
        """Test getting multiple items for the same ISBN."""
        # Add more items
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            item2 = Item(manifestation_id=manifestation.id, owner_id=sample_work_complete["user"].id)
            item3 = Item(manifestation_id=manifestation.id, owner_id=sample_work_complete["user"].id)
            db.session.add_all([item2, item3])
            db.session.commit()

        response = client.get("/api/item/9780544003415")
        assert response.status_code == 200
        assert len(response.json["ids"]) == 3

    def test_get_items_no_items_exists(self, client, app):
        """Test getting items when manifestation exists but has no items."""
        with app.app_context():
            work = Work(title="No Items", meta={"authors": []})
            db.session.add(work)
            db.session.flush()

            expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
            db.session.add(expression)
            db.session.flush()

            manifestation = Manifestation(expression_id=expression.id, isbn13="9783333333333", meta={})
            db.session.add(manifestation)
            db.session.commit()

        response = client.get("/api/item/9783333333333")
        assert response.status_code == 404
        assert "error" in response.json

    def test_get_items_no_manifestation(self, client):
        """Test getting items for non-existent manifestation returns 404."""
        response = client.get("/api/item/9999999999999")
        assert response.status_code == 404

    def test_get_items_returns_correct_ids(self, client, sample_work_complete):
        """Test that get_items returns the actual item IDs."""
        # Get the original item ID
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            original_item = Item.query.filter_by(manifestation_id=manifestation.id).first()
            original_id = original_item.id

        response = client.get("/api/item/9780544003415")
        assert response.status_code == 200
        assert original_id in response.json["ids"]


# =============================================================================
# Integration Tests
# =============================================================================


class TestBookOperationsIntegration:
    """Integration tests for complete workflows."""

    @patch("app.utils.isbn.fetch_isbn_metadata")
    def test_complete_workflow_scan_add_update(self, mock_fetch, client, normal_user_headers, admin_headers):
        """Test complete workflow: scan new book, add item, then update metadata."""
        mock_fetch.return_value = {"Title": "The Hobbit", "Authors": ["J.R.R. Tolkien"]}

        # Step 1: Scan new ISBN (creates FRBR structure)
        scan_response = client.get("/api/isbn/9780547928227")
        assert scan_response.status_code == 200
        assert scan_response.json["Title"] == "The Hobbit"

        # Step 2: Add an item
        add_response = client.post("/api/item/9780547928227", json={}, headers=normal_user_headers, content_type="application/json")
        assert add_response.status_code == 200
        item_id = add_response.json["data"]["item_id"]

        # Step 3: Update metadata
        update_data = {"Title": "The Hobbit: Annotated Edition", "Authors": ["J.R.R. Tolkien"]}
        update_response = client.post("/api/isbn/9780547928227", json=update_data, headers=admin_headers, content_type="application/json")
        assert update_response.status_code == 200

        # Step 4: Verify everything is consistent
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780547928227").first()
            assert manifestation.meta["Title"] == "The Hobbit: Annotated Edition"

            item = db.session.get(Item, item_id)
            assert item.manifestation_id == manifestation.id

            work = manifestation.expression.work
            assert work.title == "The Hobbit: Annotated Edition"

    def test_scan_same_book_twice_reuses_structure(self, client):
        """Test scanning the same ISBN twice doesn't create duplicates."""
        with patch("app.utils.isbn.fetch_isbn_metadata") as mock_fetch:
            mock_fetch.return_value = {"Title": "Harry Potter", "Authors": ["J.K. Rowling"]}

            # First scan
            response1 = client.get("/api/isbn/9780439708180")
            assert response1.status_code == 200

            # Second scan (served from DB; fetch_isbn_metadata not called again)
            response2 = client.get("/api/isbn/9780439708180")
            assert response2.status_code == 200

        # Verify only one manifestation exists
        with client.application.app_context():
            manifestations = Manifestation.query.filter_by(isbn13="9780439708180").all()
            assert len(manifestations) == 1

            works = Work.query.filter_by(title="Harry Potter").all()
            assert len(works) == 1

    def test_add_items_different_owners(self, client, sample_work_complete, normal_user_headers, admin_headers):
        """Test adding items for different owners to the same manifestation."""
        # Add item for first owner
        response1 = client.post("/api/item/9780544003415", json={}, headers=normal_user_headers, content_type="application/json")
        assert response1.status_code == 200
        assert "item_id" in response1.json["data"]

        # Add item for second owner (in real app, would be different session)
        response2 = client.post("/api/item/9780544003415", json={}, headers=admin_headers, content_type="application/json")
        assert response2.status_code == 200
        assert "item_id" in response2.json["data"]

        # Verify both items exist
        with client.application.app_context():
            manifestation = Manifestation.query.filter_by(isbn13="9780544003415").first()
            items = Item.query.filter_by(manifestation_id=manifestation.id).all()
            assert len(items) == 3  # Original + 2 new

    @patch("app.utils.isbn.fetch_isbn_metadata")
    def test_frbr_structure_integrity(self, mock_fetch, client, normal_user_headers):
        """Test that FRBR structure maintains referential integrity."""
        mock_fetch.return_value = {"Title": "Animal Farm", "Authors": ["George Orwell"]}

        # Create structure through API
        client.get("/api/isbn/9780141182605")
        client.post("/api/item/9780141182605", json={}, headers=normal_user_headers, content_type="application/json")

        # Verify complete chain
        with client.application.app_context():
            item = Item.query.first()
            assert item.manifestation is not None
            assert item.manifestation.expression is not None
            assert item.manifestation.expression.work is not None

            # Verify reverse relationships
            work = Work.query.filter_by(title="Animal Farm").first()
            assert len(work.expressions) > 0
            expression = work.expressions[0]
            assert len(expression.manifestations) > 0
            manifestation = expression.manifestations[0]
            assert len(manifestation.items) > 0
