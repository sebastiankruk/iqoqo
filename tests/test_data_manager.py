"""Tests for the DataManager class."""

# pylint: disable=redefined-outer-name  # pytest fixtures

import json

import pytest

from app.core.data_manager import DataManager
from app.db.models import Expression, Item, Manifestation, Work


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
        "items": [
            {"id": 1, "manifestation_id": 1, "condition": "good", "location": "shelf-a", "notes": "First edition copy"}
        ],
    }


def test_get_stats_empty(app):
    """Test getting stats from an empty database."""
    with app.app_context():
        stats = DataManager.get_stats()
        assert stats["works"] == 0
        assert stats["expressions"] == 0
        assert stats["manifestations"] == 0
        assert stats["items"] == 0


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
        with open(filepath, encoding="utf-8") as f:
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
            sample_copy["works"][0]["title"] = f"Book {i+1}"
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
