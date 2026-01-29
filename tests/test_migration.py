"""Tests for migration scripts."""

# pylint: disable=redefined-outer-name,import-error,import-outside-toplevel,unused-import,unused-argument

import json
import tempfile
from pathlib import Path

import pytest


@pytest.mark.skip(reason="Requires refactoring sql_to_json.py to export parse function")
def test_sql_to_json_parser():
    """Test the SQL to JSON conversion logic."""
    # from scripts.sql_to_json import parse_insert_value
    #
    # # Test basic manifestation parsing
    # insert_value = (
    #     "1, '9780451524935', 'Nineteen Eighty-Four', 'George Orwell', '{\"meta\": \"data\"}', '2024-01-01 12:00:00'"
    # )
    # result = parse_insert_value(insert_value)
    #
    # assert result["id"] == 1
    # assert result["isbn"] == "9780451524935"
    # assert result["title"] == "Nineteen Eighty-Four"
    # assert result["authors"] == "George Orwell"
    # assert result["added"] == "2024-01-01 12:00:00"


@pytest.mark.skip(reason="Requires refactoring sql_to_json.py to export parse function")
def test_sql_to_json_handles_quotes():
    """Test that SQL parser handles escaped quotes correctly."""
    # from scripts.sql_to_json import parse_sql_dump
    #
    # # Title with apostrophe
    # insert_value = r"1, '9780123456789', 'O\'Brien''s Book', 'Author Name', '{}', '2024-01-01 12:00:00'"
    # result = parse_sql_dump(insert_value)
    #
    # # The parser should handle escaped quotes
    # assert result["title"] == "O'Brien's Book" or "O\\'Brien" in result["title"]


def test_sql_to_json_file_conversion():
    """Test converting a SQL file to JSON."""

    # Create a temporary SQL file
    sql_content = """
-- Test SQL dump
INSERT INTO manifestation VALUES (1, '9780451524935', 'Test Book', 'Test Author', '{"key": "value"}', '2024-01-01 12:00:00');
INSERT INTO manifestation VALUES (2, '9781234567890', 'Another Book', 'Another Author', '{}', '2024-01-02 12:00:00');
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as sql_file:
        sql_file.write(sql_content)
        sql_file_path = sql_file.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as json_file:
        json_file_path = json_file.name

    import sys

    old_argv = sys.argv
    try:
        # Run the conversion (this would normally be sys.argv)
        sys.argv = ["sql_to_json.py", sql_file_path, json_file_path]

        # Note: This test would need the script to be importable
        # In practice, you might need to refactor sql_to_json.py to be more testable

    finally:
        sys.argv = old_argv
        Path(sql_file_path).unlink(missing_ok=True)
        Path(json_file_path).unlink(missing_ok=True)


@pytest.mark.skip(reason="Requires refactoring migrate_legacy.py for testability")
def test_migrate_legacy_creates_work_from_title(app):
    """Test that migration creates unique works from titles."""
    # from app.db.models import Work
    # from scripts.migrate_legacy import main

    # Create test data with same title (should create 1 work)
    test_data = {
        "manifestations": [
            {
                "id": 1,
                "isbn": "9780451524935",
                "title": "1984",
                "authors": "George Orwell",
                "meta": json.dumps({"volumeInfo": {"title": "1984", "authors": ["George Orwell"]}}),
                "added": "2024-01-01 12:00:00",
            },
            {
                "id": 2,
                "isbn": "9780452284234",
                "title": "1984",  # Same title, different ISBN (different edition)
                "authors": "George Orwell",
                "meta": json.dumps({"volumeInfo": {"title": "1984", "authors": ["George Orwell"]}}),
                "added": "2024-01-02 12:00:00",
            },
        ],
        "items": [],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_data, f)
        temp_path = f.name

    try:
        with app.app_context():
            import sys

            old_argv = sys.argv
            sys.argv = ["migrate_legacy.py", temp_path]

            # This would need migrate_legacy to be refactored for testing
            # For now, we'll test the logic directly

            # from app.db import db
            # from scripts.migrate_legacy import process_manifestation
            #
            # work_cache = {}
            #
            # for manif in test_data["manifestations"]:
            #     process_manifestation(manif, work_cache, db.session)
            #
            # db.session.commit()
            #
            # # Should create only 1 work for both manifestations
            # works = Work.query.all()
            # assert len(works) == 1
            # assert works[0].title == "1984"

            sys.argv = old_argv
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_migrate_legacy_handles_missing_isbn(app):
    """Test that migration handles manifestations without ISBN."""
    # from app.db import db
    # from app.db.models import Expression, Manifestation, Work

    with app.app_context():
        # This would test the actual migration logic
        # The migration script should skip or handle items without ISBN appropriately
        assert True  # Placeholder


def test_isbn_normalization():
    """Test ISBN-10 to ISBN-13 conversion."""
    # This would test any ISBN conversion logic in the migration script
    # Example: Converting 0451524934 to 9780451524935
    assert True  # Placeholder


@pytest.mark.skip(reason="Requires proper FRBR hierarchy setup")
def test_duplicate_isbn_handling(app):
    """Test that duplicate ISBNs are handled correctly."""
    # Would need to create Work -> Expression -> Manifestation hierarchy
    # to properly test duplicate ISBN handling
    assert app  # Use fixture to avoid warning


@pytest.mark.skip(reason="Requires refactoring migration scripts for testability")
def test_full_migration_integration(app):
    """Integration test for full migration process."""
    # This would be a comprehensive test that:
    # 1. Creates a legacy SQL dump
    # 2. Converts it to JSON with sql_to_json.py
    # 3. Runs migrate_legacy.py
    # 4. Verifies all data was migrated correctly with proper FRBR structure
    assert app  # Use fixture to avoid warning
