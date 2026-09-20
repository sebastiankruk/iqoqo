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
"""Shared validation and normalization for F3 physical attributes.

This module provides canonical validation and normalization for promoted
Manifestation attributes: isbn13, publisher, and format_type.

Key features:
- Case-insensitive legacy-key extraction from metadata
- ISBN-10 to ISBN-13 conversion with checksum validation
- Publisher length validation
- Format type validation against shared taxonomy
"""

import re
from typing import Any

# Maximum lengths for promoted columns
MAX_PUBLISHER_LENGTH = 255
MAX_FORMAT_TYPE_LENGTH = 50
MAX_ISBN13_LENGTH = 13

# Regex for cleaning ISBN values
ISBN_CLEAN_PATTERN = re.compile(r"[^0-9X]")


class F3ValidationError(Exception):
    """Base exception for F3 validation errors."""

    pass


class ISBNValidationError(F3ValidationError):
    """Raised when an ISBN value is invalid."""

    pass


class PublisherValidationError(F3ValidationError):
    """Raised when a publisher value is invalid."""

    pass


class FormatTypeValidationError(F3ValidationError):
    """Raised when a format_type value is invalid."""

    pass


def extract_promoted_key_case_insensitive(meta: dict[str, Any] | None, key: str) -> Any | None:
    """Extract a promoted key from metadata using case-insensitive matching.

    This function handles legacy metadata keys that may have different casing
    (e.g., "publisher", "Publisher", "PUBLISHER").

    Args:
        meta: Metadata dictionary to search
        key: Key to find (case-insensitive)

    Returns:
        The value if found, None otherwise

    Examples:
        >>> extract_promoted_key_case_insensitive({"Publisher": "Test"}, "publisher")
        'Test'
        >>> extract_promoted_key_case_insensitive({"PUBLISHER": "Test"}, "publisher")
        'Test'
    """
    if not meta or not isinstance(meta, dict):
        return None

    key_lower = key.lower()
    for k, v in meta.items():
        if isinstance(k, str) and k.lower() == key_lower:
            return v
    return None


def isbn10_to_isbn13(isbn10: str) -> str | None:
    """Convert a valid 10-digit ISBN to a 13-digit ISBN-13.

    Args:
        isbn10: Raw or formatted 10-digit ISBN string

    Returns:
        Normalized 13-digit ISBN string or None if invalid

    Examples:
        >>> isbn10_to_isbn13("0-306-40615-2")
        '9780306406157'
        >>> isbn10_to_isbn13("080442957X")
        '9780804429573'
    """
    cleaned = ISBN_CLEAN_PATTERN.sub("", isbn10.upper())
    if len(cleaned) != 10:
        return None

    # Validate 10-digit checksum
    if not (cleaned[:9].isdigit() and (cleaned[9].isdigit() or cleaned[9] == "X")):
        return None

    total10 = sum((10 - idx) * (10 if char == "X" else int(char)) for idx, char in enumerate(cleaned))
    if total10 % 11 != 0:
        return None

    # Construct 13-digit prefix (978 + first 9 digits)
    core = f"978{cleaned[:9]}"
    total13 = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(core))
    check13 = (10 - (total13 % 10)) % 10
    return f"{core}{check13}"


def normalize_isbn(raw_isbn: str) -> str | None:
    """Normalize any ISBN (10-digit or 13-digit) to canonical ISBN-13.

    Accepts:
    - Valid ISBN-10 (with or without hyphens)
    - Valid ISBN-13 (with or without hyphens)

    Args:
        raw_isbn: Raw ISBN string containing possible hyphens or spaces

    Returns:
        Normalized 13-digit ISBN or None if invalid

    Raises:
        ISBNValidationError: If the ISBN is malformed or has invalid checksum

    Examples:
        >>> normalize_isbn("0-306-40615-2")
        '9780306406157'
        >>> normalize_isbn("978-0-306-40615-7")
        '9780306406157'
    """
    if not raw_isbn or not isinstance(raw_isbn, str):
        return None

    cleaned = ISBN_CLEAN_PATTERN.sub("", raw_isbn.upper())

    if len(cleaned) == 10:
        result = isbn10_to_isbn13(cleaned)
        if result is None:
            raise ISBNValidationError(f"Invalid ISBN-10 checksum: {raw_isbn}")
        return result

    if len(cleaned) == 13 and cleaned.isdigit():
        # Validate ISBN-13 checksum
        total = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(cleaned[:12]))
        expected_check = (10 - (total % 10)) % 10
        if int(cleaned[12]) != expected_check:
            raise ISBNValidationError(f"Invalid ISBN-13 checksum: {raw_isbn}")
        return cleaned

    # Invalid length
    if len(cleaned) not in (10, 13):
        raise ISBNValidationError(f"Invalid ISBN length: {len(cleaned)} (expected 10 or 13)")

    return None


def validate_publisher(publisher: str | None, strict: bool = False) -> str | None:
    """Validate and normalize a publisher name.

    Args:
        publisher: Publisher name to validate
        strict: If True, raise error on invalid values; if False, return None

    Returns:
        Normalized publisher name or None

    Raises:
        PublisherValidationError: If strict=True and publisher is invalid

    Examples:
        >>> validate_publisher("  Test Publisher  ")
        'Test Publisher'
        >>> validate_publisher("A" * 300, strict=False)
        None
    """
    if not publisher or not isinstance(publisher, str):
        return None

    cleaned = publisher.strip()
    if not cleaned:
        return None

    if len(cleaned) > MAX_PUBLISHER_LENGTH:
        if strict:
            raise PublisherValidationError(
                f"Publisher name exceeds maximum length of {MAX_PUBLISHER_LENGTH}: " f"{len(cleaned)} characters"
            )
        return None

    return cleaned


def validate_format_type(format_type: str | None, strict: bool = False) -> str | None:
    """Validate and normalize a format type against the shared taxonomy.

    Args:
        format_type: Format type to validate
        strict: If True, raise error on invalid values; if False, return None

    Returns:
        Normalized format type or None

    Raises:
        FormatTypeValidationError: If strict=True and format_type is invalid

    Examples:
        >>> validate_format_type("  HARDCOVER  ")
        'hardcover'
        >>> validate_format_type("invalid_format", strict=False)
        None
    """
    if not format_type or not isinstance(format_type, str):
        return None

    cleaned = format_type.strip().lower()
    if not cleaned:
        return None

    if len(cleaned) > MAX_FORMAT_TYPE_LENGTH:
        if strict:
            raise FormatTypeValidationError(
                f"Format type exceeds maximum length of {MAX_FORMAT_TYPE_LENGTH}: " f"{len(cleaned)} characters"
            )
        return None

    # Import taxonomy here to avoid circular imports
    from app.core.taxonomy import MediaFormat

    # Check if format is in the known taxonomy
    known_formats = {attr.lower() for attr in dir(MediaFormat) if not attr.startswith("_") and isinstance(getattr(MediaFormat, attr), str)}

    if cleaned not in known_formats:
        if strict:
            raise FormatTypeValidationError(f"Unknown format type: {format_type}. " f"Known formats: {sorted(known_formats)}")
        # In non-strict mode, accept the value but log a warning
        # This allows forward compatibility with new formats
        return cleaned

    return cleaned


def normalize_manifestation_meta(
    meta: dict[str, Any] | None,
    isbn13: str | None = None,
    publisher: str | None = None,
    format_type: str | None = None,
    format: str | None = None,
    strict: bool = False,
) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    """Normalize and validate F3 physical attributes from metadata.

    This function implements the canonical extraction and validation logic
    for promoted Manifestation attributes.

    Args:
        meta: Metadata dictionary
        isbn13: Current isbn13 column value
        publisher: Current publisher column value
        format_type: Current format_type column value
        format: Current format column value
        strict: If True, raise errors on invalid values

    Returns:
        Tuple of (normalized_isbn13, normalized_publisher, normalized_format_type, pruned_meta)

    Raises:
        F3ValidationError: If strict=True and any value is invalid
    """
    if meta is None:
        meta = {}
    elif not isinstance(meta, dict):
        meta = {}

    # Work with a copy to avoid mutating the original
    meta_copy = dict(meta)

    # Extract and normalize ISBN
    normalized_isbn = isbn13
    if not normalized_isbn:
        # Try case-insensitive extraction from metadata
        raw_isbn = extract_promoted_key_case_insensitive(meta_copy, "isbn13")
        if not raw_isbn:
            raw_isbn = extract_promoted_key_case_insensitive(meta_copy, "isbn")
        if raw_isbn and isinstance(raw_isbn, str):
            try:
                normalized_isbn = normalize_isbn(raw_isbn)
            except ISBNValidationError:
                if strict:
                    raise
                normalized_isbn = None

    # Extract and normalize publisher
    normalized_publisher = publisher
    if not normalized_publisher:
        raw_publisher = extract_promoted_key_case_insensitive(meta_copy, "publisher")
        if raw_publisher and isinstance(raw_publisher, str):
            try:
                normalized_publisher = validate_publisher(raw_publisher, strict=strict)
            except PublisherValidationError:
                if strict:
                    raise
                normalized_publisher = None

    # Extract and normalize format_type
    normalized_format_type = format_type
    if not normalized_format_type:
        # Try multiple possible keys
        raw_format = (
            extract_promoted_key_case_insensitive(meta_copy, "format_type")
            or format
            or extract_promoted_key_case_insensitive(meta_copy, "format")
            or extract_promoted_key_case_insensitive(meta_copy, "video_format")
        )
        if raw_format and isinstance(raw_format, str):
            try:
                normalized_format_type = validate_format_type(raw_format, strict=strict)
            except FormatTypeValidationError:
                if strict:
                    raise
                normalized_format_type = None

    # Prune promoted keys from metadata
    promoted_keys = ["isbn13", "isbn", "publisher", "format_type"]
    for key in promoted_keys:
        # Case-insensitive removal
        keys_to_remove = [k for k in meta_copy.keys() if isinstance(k, str) and k.lower() == key.lower()]
        for k in keys_to_remove:
            del meta_copy[k]

    return normalized_isbn, normalized_publisher, normalized_format_type, meta_copy


class PreflightReport:
    """Report of preflight checks before migration.

    This class collects issues that must be resolved before running
    the F3 column promotion migration.
    """

    def __init__(self):
        self.long_publishers: list[dict[str, Any]] = []
        self.invalid_isbns: list[dict[str, Any]] = []
        self.isbn_conflicts: list[dict[str, Any]] = []
        self.mixed_case_keys: list[dict[str, Any]] = []
        self.other_issues: list[dict[str, Any]] = []

    def add_long_publisher(self, manifestation_id: int, publisher: str, length: int):
        """Record a publisher that exceeds the target column length."""
        self.long_publishers.append(
            {
                "manifestation_id": manifestation_id,
                "publisher": publisher,
                "length": length,
                "max_length": MAX_PUBLISHER_LENGTH,
            }
        )

    def add_invalid_isbn(self, manifestation_id: int, isbn: str, reason: str):
        """Record an invalid ISBN value."""
        self.invalid_isbns.append(
            {
                "manifestation_id": manifestation_id,
                "isbn": isbn,
                "reason": reason,
            }
        )

    def add_isbn_conflict(self, isbn: str, manifestation_ids: list[int]):
        """Record duplicate ISBN values."""
        self.isbn_conflicts.append(
            {
                "isbn": isbn,
                "manifestation_ids": manifestation_ids,
            }
        )

    def add_mixed_case_key(self, manifestation_id: int, key: str, expected: str):
        """Record a mixed-case promoted key."""
        self.mixed_case_keys.append(
            {
                "manifestation_id": manifestation_id,
                "key": key,
                "expected": expected,
            }
        )

    def add_other_issue(self, issue_type: str, details: dict[str, Any]):
        """Record any other preflight issue."""
        self.other_issues.append(
            {
                "type": issue_type,
                "details": details,
            }
        )

    @property
    def has_issues(self) -> bool:
        """Check if there are any preflight issues."""
        return bool(self.long_publishers or self.invalid_isbns or self.isbn_conflicts or self.mixed_case_keys or self.other_issues)

    @property
    def blocking_issues(self) -> bool:
        """Check if there are blocking issues that prevent migration."""
        return bool(self.long_publishers or self.isbn_conflicts)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "long_publishers": self.long_publishers,
            "invalid_isbns": self.invalid_isbns,
            "isbn_conflicts": self.isbn_conflicts,
            "mixed_case_keys": self.mixed_case_keys,
            "other_issues": self.other_issues,
            "has_issues": self.has_issues,
            "blocking_issues": self.blocking_issues,
        }

    def __str__(self) -> str:
        """Generate human-readable report."""
        lines = ["F3 Column Promotion Preflight Report", "=" * 50]

        if not self.has_issues:
            lines.append("✓ No issues found. Migration can proceed.")
            return "\n".join(lines)

        if self.long_publishers:
            lines.append(f"\n⚠ Long Publishers ({len(self.long_publishers)}):")
            for item in self.long_publishers[:10]:  # Show first 10
                lines.append(f"  - Manifestation {item['manifestation_id']}: " f"{item['length']} chars (max {item['max_length']})")
            if len(self.long_publishers) > 10:
                lines.append(f"  ... and {len(self.long_publishers) - 10} more")

        if self.invalid_isbns:
            lines.append(f"\n⚠ Invalid ISBNs ({len(self.invalid_isbns)}):")
            for item in self.invalid_isbns[:10]:
                lines.append(f"  - Manifestation {item['manifestation_id']}: " f"{item['isbn']} ({item['reason']})")
            if len(self.invalid_isbns) > 10:
                lines.append(f"  ... and {len(self.invalid_isbns) - 10} more")

        if self.isbn_conflicts:
            lines.append(f"\n✗ ISBN Conflicts ({len(self.isbn_conflicts)}):")
            for item in self.isbn_conflicts[:10]:
                lines.append(f"  - ISBN {item['isbn']}: " f"manifestations {item['manifestation_ids']}")
            if len(self.isbn_conflicts) > 10:
                lines.append(f"  ... and {len(self.isbn_conflicts) - 10} more")

        if self.mixed_case_keys:
            lines.append(f"\nℹ Mixed-Case Keys ({len(self.mixed_case_keys)}):")
            for item in self.mixed_case_keys[:10]:
                lines.append(f"  - Manifestation {item['manifestation_id']}: " f"'{item['key']}' (expected '{item['expected']}')")
            if len(self.mixed_case_keys) > 10:
                lines.append(f"  ... and {len(self.mixed_case_keys) - 10} more")

        if self.other_issues:
            lines.append(f"\n⚠ Other Issues ({len(self.other_issues)}):")
            for item in self.other_issues[:10]:
                lines.append(f"  - {item['type']}: {item['details']}")

        if self.blocking_issues:
            lines.append("\n✗ BLOCKING: Migration cannot proceed until issues are resolved.")
        else:
            lines.append("\n⚠ WARNING: Non-blocking issues found. Review recommended.")

        return "\n".join(lines)
