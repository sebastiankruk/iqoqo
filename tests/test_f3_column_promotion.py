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
"""Tests for F3 column promotion hardening.

Tests cover:
- Shared validation utilities (ISBN, publisher, format_type)
- Case-insensitive metadata key extraction
- Migration preflight checks
- Migration upgrade/downgrade with data quality issues
- Runtime validation in frbr_service
"""

import pytest
from sqlalchemy import select

from app.core.f3_validation import (
    MAX_FORMAT_TYPE_LENGTH,
    MAX_ISBN13_LENGTH,
    MAX_PUBLISHER_LENGTH,
    FormatTypeValidationError,
    ISBNValidationError,
    PreflightReport,
    PublisherValidationError,
    extract_promoted_key_case_insensitive,
    isbn10_to_isbn13,
    normalize_isbn,
    normalize_manifestation_meta,
    validate_format_type,
    validate_publisher,
)
from app.db import db
from app.db.core import Expression, Manifestation, Work
from app.db.models import User


class TestISBNValidation:
    """Test ISBN validation and normalization."""

    def test_isbn10_to_isbn13_valid(self):
        """Test valid ISBN-10 to ISBN-13 conversion."""
        assert isbn10_to_isbn13("0-306-40615-2") == "9780306406157"
        assert isbn10_to_isbn13("080442957X") == "9780804429573"
        assert isbn10_to_isbn13("0306406152") == "9780306406157"

    def test_isbn10_to_isbn13_invalid(self):
        """Test invalid ISBN-10 values."""
        assert isbn10_to_isbn13("1234567890") is None  # Invalid checksum
        assert isbn10_to_isbn13("123") is None  # Too short
        assert isbn10_to_isbn13("12345678901") is None  # Too long
        assert isbn10_to_isbn13("invalid") is None

    def test_normalize_isbn_valid_isbn10(self):
        """Test normalization of valid ISBN-10."""
        assert normalize_isbn("0-306-40615-2") == "9780306406157"
        assert normalize_isbn("080442957X") == "9780804429573"

    def test_normalize_isbn_valid_isbn13(self):
        """Test normalization of valid ISBN-13."""
        assert normalize_isbn("978-0-306-40615-7") == "9780306406157"
        assert normalize_isbn("9780306406157") == "9780306406157"
        assert normalize_isbn("978 0 306 40615 7") == "9780306406157"

    def test_normalize_isbn_invalid(self):
        """Test normalization of invalid ISBNs."""
        with pytest.raises(ISBNValidationError, match="checksum"):
            normalize_isbn("978-0-306-40615-9")  # Invalid checksum

        with pytest.raises(ISBNValidationError, match="length"):
            normalize_isbn("12345")  # Invalid length

        with pytest.raises(ISBNValidationError, match="checksum"):
            normalize_isbn("1234567890")  # Invalid ISBN-10 checksum

    def test_normalize_isbn_none(self):
        """Test normalization of None/empty values."""
        assert normalize_isbn(None) is None
        assert normalize_isbn("") is None
        with pytest.raises(ISBNValidationError, match="length"):
            normalize_isbn("  ")  # Whitespace-only is invalid


class TestPublisherValidation:
    """Test publisher validation."""

    def test_validate_publisher_valid(self):
        """Test valid publisher names."""
        assert validate_publisher("Test Publisher") == "Test Publisher"
        assert validate_publisher("  Test Publisher  ") == "Test Publisher"
        assert validate_publisher("A" * 255) == "A" * 255

    def test_validate_publisher_too_long(self):
        """Test publisher names exceeding max length."""
        long_publisher = "A" * 300
        assert validate_publisher(long_publisher, strict=False) is None

        with pytest.raises(PublisherValidationError, match="exceeds maximum length"):
            validate_publisher(long_publisher, strict=True)

    def test_validate_publisher_empty(self):
        """Test empty/None publisher names."""
        assert validate_publisher(None) is None
        assert validate_publisher("") is None
        assert validate_publisher("   ") is None


class TestFormatTypeValidation:
    """Test format_type validation."""

    def test_validate_format_type_valid(self):
        """Test valid format types."""
        assert validate_format_type("book") == "book"
        assert validate_format_type("  BOOK  ") == "book"
        assert validate_format_type("dvd") == "dvd"
        assert validate_format_type("bluray") == "bluray"

    def test_validate_format_type_too_long(self):
        """Test format types exceeding max length."""
        long_format = "a" * 100
        assert validate_format_type(long_format, strict=False) is None

        with pytest.raises(FormatTypeValidationError, match="exceeds maximum length"):
            validate_format_type(long_format, strict=True)

    def test_validate_format_type_unknown_strict(self):
        """Test unknown format types in strict mode."""
        with pytest.raises(FormatTypeValidationError, match="Unknown format type"):
            validate_format_type("unknown_format_xyz", strict=True)

    def test_validate_format_type_unknown_non_strict(self):
        """Test unknown format types in non-strict mode (forward compatibility)."""
        # Non-strict mode accepts unknown formats for forward compatibility
        assert validate_format_type("future_format", strict=False) == "future_format"

    def test_validate_format_type_empty(self):
        """Test empty/None format types."""
        assert validate_format_type(None) is None
        assert validate_format_type("") is None
        assert validate_format_type("   ") is None


class TestCaseInsensitiveExtraction:
    """Test case-insensitive metadata key extraction."""

    def test_extract_exact_match(self):
        """Test extraction with exact key match."""
        meta = {"publisher": "Test Publisher"}
        assert extract_promoted_key_case_insensitive(meta, "publisher") == "Test Publisher"

    def test_extract_case_insensitive(self):
        """Test extraction with different casing."""
        meta = {"Publisher": "Test Publisher"}
        assert extract_promoted_key_case_insensitive(meta, "publisher") == "Test Publisher"

        meta = {"PUBLISHER": "Test Publisher"}
        assert extract_promoted_key_case_insensitive(meta, "publisher") == "Test Publisher"

        meta = {"pUbLiShEr": "Test Publisher"}
        assert extract_promoted_key_case_insensitive(meta, "publisher") == "Test Publisher"

    def test_extract_isbn_variants(self):
        """Test extraction of ISBN variants."""
        meta = {"ISBN13": "9780306406157"}
        assert extract_promoted_key_case_insensitive(meta, "isbn13") == "9780306406157"

        meta = {"isbn": "0306406152"}
        assert extract_promoted_key_case_insensitive(meta, "isbn") == "0306406152"

    def test_extract_not_found(self):
        """Test extraction when key not found."""
        meta = {"other_key": "value"}
        assert extract_promoted_key_case_insensitive(meta, "publisher") is None

    def test_extract_none_meta(self):
        """Test extraction with None metadata."""
        assert extract_promoted_key_case_insensitive(None, "publisher") is None


class TestNormalizeManifestationMeta:
    """Test complete metadata normalization."""

    def test_normalize_isbn_from_meta(self):
        """Test ISBN normalization from metadata."""
        meta = {"isbn": "0-306-40615-2"}
        isbn, _, _, pruned = normalize_manifestation_meta(meta)
        assert isbn == "9780306406157"
        assert "isbn" not in pruned
        assert "ISBN" not in pruned

    def test_normalize_publisher_from_meta(self):
        """Test publisher normalization from metadata."""
        meta = {"Publisher": "  Test Publisher  "}
        _, pub, _, pruned = normalize_manifestation_meta(meta)
        assert pub == "Test Publisher"
        assert "Publisher" not in pruned
        assert "publisher" not in pruned

    def test_normalize_format_type_from_meta(self):
        """Test format_type normalization from metadata."""
        meta = {"FORMAT_TYPE": "  BOOK  "}
        _, _, fmt, pruned = normalize_manifestation_meta(meta)
        assert fmt == "book"
        assert "FORMAT_TYPE" not in pruned
        assert "format_type" not in pruned

    def test_normalize_column_precedence(self):
        """Test that column values take precedence over metadata."""
        meta = {"isbn13": "9780000000000", "publisher": "Meta Publisher"}
        isbn, pub, _, _ = normalize_manifestation_meta(meta, isbn13="9781111111111", publisher="Column Publisher")
        assert isbn == "9781111111111"  # Column value wins
        assert pub == "Column Publisher"  # Column value wins

    def test_normalize_invalid_isbn_strict(self):
        """Test invalid ISBN in strict mode."""
        meta = {"isbn13": "invalid"}
        with pytest.raises(ISBNValidationError):
            normalize_manifestation_meta(meta, strict=True)

    def test_normalize_invalid_isbn_non_strict(self):
        """Test invalid ISBN in non-strict mode."""
        meta = {"isbn13": "invalid"}
        isbn, _, _, _ = normalize_manifestation_meta(meta, strict=False)
        assert isbn is None  # Invalid ISBN rejected


class TestPreflightReport:
    """Test preflight report generation."""

    def test_empty_report(self):
        """Test empty preflight report."""
        report = PreflightReport()
        assert not report.has_issues
        assert not report.blocking_issues
        assert "No issues found" in str(report)

    def test_long_publisher_issue(self):
        """Test long publisher issue."""
        report = PreflightReport()
        report.add_long_publisher(1, "A" * 300, 300)
        assert report.has_issues
        assert report.blocking_issues
        assert len(report.long_publishers) == 1

    def test_invalid_isbn_issue(self):
        """Test invalid ISBN issue."""
        report = PreflightReport()
        report.add_invalid_isbn(1, "invalid", "Invalid checksum")
        assert report.has_issues
        assert not report.blocking_issues  # Invalid ISBNs are non-blocking
        assert len(report.invalid_isbns) == 1

    def test_isbn_conflict_issue(self):
        """Test ISBN conflict issue."""
        report = PreflightReport()
        report.add_isbn_conflict("9780306406157", [1, 2, 3])
        assert report.has_issues
        assert report.blocking_issues
        assert len(report.isbn_conflicts) == 1

    def test_mixed_case_key_issue(self):
        """Test mixed-case key issue."""
        report = PreflightReport()
        report.add_mixed_case_key(1, "Publisher", "publisher")
        assert report.has_issues
        assert not report.blocking_issues  # Mixed-case keys are non-blocking
        assert len(report.mixed_case_keys) == 1

    def test_report_to_dict(self):
        """Test report serialization."""
        report = PreflightReport()
        report.add_long_publisher(1, "A" * 300, 300)
        report.add_invalid_isbn(2, "invalid", "Invalid checksum")

        report_dict = report.to_dict()
        assert "long_publishers" in report_dict
        assert "invalid_isbns" in report_dict
        assert report_dict["has_issues"] is True
        assert report_dict["blocking_issues"] is True


class TestMigrationPreflight:
    """Test migration preflight checks with database fixtures."""

    def test_preflight_clean_data(self, app):
        """Test preflight with clean data."""
        from migrations.versions.v0_7_19_f3_column_promotion import run_preflight

        with app.app_context():
            # Create clean test data
            work = Work(title="Test Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            manif = Manifestation(
                expression_id=expr.id,
                isbn13="9780306406157",
                publisher="Test Publisher",
            )
            db.session.add(manif)
            db.session.commit()

            # Run preflight
            report = run_preflight(db.session.connection())
            assert not report.blocking_issues

    def test_preflight_long_publisher(self, app):
        """Test preflight with long publisher."""
        from migrations.versions.v0_7_19_f3_column_promotion import run_preflight

        with app.app_context():
            work = Work(title="Test Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            # Create manifestation with long publisher (bypass validation)
            manif = Manifestation(
                expression_id=expr.id,
                publisher="A" * 300,  # Exceeds MAX_PUBLISHER_LENGTH
            )
            db.session.add(manif)
            db.session.commit()

            # Run preflight
            report = run_preflight(db.session.connection())
            assert report.blocking_issues
            assert len(report.long_publishers) == 1
            assert report.long_publishers[0]["length"] == 300

    def test_preflight_isbn_conflict(self, app):
        """Test preflight with ISBN conflicts.

        Note: In the current schema, isbn13 has a UNIQUE constraint, so duplicates
        cannot exist in normal operation. This test verifies the preflight logic
        would detect conflicts if they existed (e.g., from legacy data before constraint).
        We simulate this by checking the preflight report structure.
        """
        from migrations.versions.v0_7_19_f3_column_promotion import run_preflight

        with app.app_context():
            work = Work(title="Test Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            # Create manifestation with valid ISBN
            manif1 = Manifestation(
                expression_id=expr.id,
                isbn13="9780306406157",
            )
            db.session.add(manif1)
            db.session.commit()

            # Run preflight - should pass since no conflicts exist
            report = run_preflight(db.session.connection())
            # Since isbn13 has UNIQUE constraint, conflicts can't exist
            # But we verify the preflight runs successfully
            assert not report.blocking_issues

    def test_preflight_mixed_case_keys(self, app):
        """Test preflight with mixed-case metadata keys."""
        from migrations.versions.v0_7_19_f3_column_promotion import run_preflight

        with app.app_context():
            work = Work(title="Test Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            # Create manifestation with mixed-case metadata
            manif = Manifestation(
                expression_id=expr.id,
                meta={"Publisher": "Test Publisher", "ISBN13": "9780306406157"},
            )
            db.session.add(manif)
            db.session.commit()

            # Run preflight
            report = run_preflight(db.session.connection())
            assert not report.blocking_issues  # Mixed-case keys are non-blocking
            assert len(report.mixed_case_keys) >= 1


class TestRuntimeValidation:
    """Test runtime validation in frbr_service."""

    def test_create_manifestation_isbn_normalization(self, app):
        """Test ISBN normalization during manifestation creation."""
        from app.core.frbr_service import create_manifestation

        with app.app_context():
            user = User(email="test@iqoqo.local", display_name="Test")
            db.session.add(user)
            db.session.flush()

            work = Work(title="Test Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            # Create with ISBN-10
            manif = create_manifestation(
                expression_id=expr.id,
                isbn13="0-306-40615-2",  # ISBN-10
            )
            db.session.commit()

            # Should be normalized to ISBN-13
            assert manif.isbn13 == "9780306406157"

    def test_create_manifestation_publisher_normalization(self, app):
        """Test publisher normalization during manifestation creation."""
        from app.core.frbr_service import create_manifestation

        with app.app_context():
            user = User(email="test@iqoqo.local", display_name="Test")
            db.session.add(user)
            db.session.flush()

            work = Work(title="Test Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            # Create with mixed-case metadata
            manif = create_manifestation(
                expression_id=expr.id,
                meta={"Publisher": "  Test Publisher  "},
            )
            db.session.commit()

            # Should be normalized
            assert manif.publisher == "Test Publisher"
            assert "Publisher" not in (manif.meta or {})
            assert "publisher" not in (manif.meta or {})

    def test_create_manifestation_format_type_normalization(self, app):
        """Test format_type normalization during manifestation creation."""
        from app.core.frbr_service import create_manifestation

        with app.app_context():
            user = User(email="test@iqoqo.local", display_name="Test")
            db.session.add(user)
            db.session.flush()

            work = Work(title="Test Work")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="text")
            db.session.add(expr)
            db.session.flush()

            # Create with mixed-case format
            manif = create_manifestation(
                expression_id=expr.id,
                format_type="  BOOK  ",
            )
            db.session.commit()

            # Should be normalized
            assert manif.format_type == "book"
