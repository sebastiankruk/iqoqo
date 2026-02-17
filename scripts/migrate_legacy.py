"""
Legacy data migration script for iqoqo.

Converts legacy database exports (from iqoqo-prototype) into the new FRBR format.

Usage:
    python scripts/migrate_legacy.py <path_to_legacy_json> [--clear]

The legacy JSON format should contain:
    {
        "clients": [...],
        "manifestations": [...],
        "items": [...]
    }

This script will create Works and Expressions based on manifestation metadata,
then map everything to the new FRBR hierarchy.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add the parent directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app import create_app
from app.db import db
from app.db.models import Expression, Item, Manifestation, Work


def migrate_legacy_data(legacy_data: dict, clear_existing: bool = False) -> dict:
    """
    Migrate legacy data to FRBR format.

    Args:
        legacy_data: Dictionary containing legacy client, manifestation, and item data.
        clear_existing: If True, clears all existing data before migrating.

    Returns:
        Dictionary with migration statistics.
    """
    if clear_existing:
        print("Clearing existing data...")
        Item.query.delete()
        Manifestation.query.delete()
        Expression.query.delete()
        Work.query.delete()
        db.session.commit()

    stats = {
        "works_created": 0,
        "expressions_created": 0,
        "manifestations_created": 0,
        "items_created": 0,
        "skipped": 0,
    }

    # Track mappings: old_manifestation_id -> new Manifestation object
    manif_map = {}

    # Track works by title to avoid duplicates
    work_cache: dict[str, Any] = {}

    # Process legacy manifestations
    legacy_manifs = legacy_data.get("manifestations", [])
    print(f"Processing {len(legacy_manifs)} legacy manifestations...")

    for old_manif in legacy_manifs:
        old_id = old_manif.get("id")
        meta = old_manif.get("meta", {})

        # Get title from multiple possible sources
        # 1. Direct field from SQL export (new format)
        # 2. Meta JSON with "Title" key (legacy format)
        # 3. Meta JSON with "volumeInfo.title" key (Google Books API format)
        title = old_manif.get("title") or meta.get("Title") or meta.get("volumeInfo", {}).get("title") or "Unknown"

        # Get authors from multiple possible sources
        # 1. Direct field from SQL export (new format) - could be comma-separated string
        # 2. Meta JSON with "Authors" key (legacy format) - list
        # 3. Meta JSON with "volumeInfo.authors" key (Google Books API format) - list
        authors_field = old_manif.get("authors")
        if authors_field:
            # Parse comma-separated authors or single author
            authors = [a.strip() for a in authors_field.split(",")] if authors_field else []
        else:
            authors = meta.get("Authors") or meta.get("volumeInfo", {}).get("authors") or []

        # Check if we already have this work
        work = work_cache.get(title)
        if not work:
            work = Work(
                title=title,
                meta={
                    "authors": authors,
                    "categories": meta.get("categories") or meta.get("volumeInfo", {}).get("categories", []),
                },
            )
            db.session.add(work)
            db.session.flush()
            work_cache[title] = work
            stats["works_created"] += 1

        # Create expression (one per language/content_type)
        # Get language from multiple sources
        language = meta.get("Language") or meta.get("volumeInfo", {}).get("language") or "en"
        expression = Expression(
            work_id=work.id,
            content_type="text",  # Assuming books from legacy
            language=language,
            meta={
                "description": meta.get("description") or meta.get("volumeInfo", {}).get("description"),
            },
        )
        db.session.add(expression)
        db.session.flush()
        stats["expressions_created"] += 1

        # Create manifestation
        isbn = old_manif.get("isbn")
        if isinstance(isbn, list) and isbn:
            isbn = isbn[0]

        # Normalize ISBN to ISBN-13 if needed
        isbn13 = None
        if isbn:
            isbn_clean = "".join(c for c in str(isbn) if c.isdigit())
            if len(isbn_clean) == 13:
                isbn13 = isbn_clean
            elif len(isbn_clean) == 10:
                # Convert ISBN-10 to ISBN-13
                isbn13 = "978" + isbn_clean[:9]
                # Calculate check digit
                check = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn13))
                check_digit = (10 - (check % 10)) % 10
                isbn13 += str(check_digit)

        # Check if this ISBN already exists (handle duplicates)
        existing_manifestation = None
        if isbn13:
            existing_manifestation = Manifestation.query.filter_by(isbn13=isbn13).first()

        if existing_manifestation:
            # Use existing manifestation for this old_id
            manifestation = existing_manifestation
            manif_map[old_id] = manifestation
            print(f"  Skipping duplicate ISBN: {isbn13} (manifestation {old_id})")
            stats["skipped"] += 1
            continue

        pub_date = None
        pub_date_str = meta.get("Year") or meta.get("volumeInfo", {}).get("publishedDate")
        if pub_date_str:
            try:
                # Try to parse year-only or full date
                if len(str(pub_date_str)) == 4:  # Year only
                    pub_date = datetime(int(pub_date_str), 1, 1).date()
                else:
                    pub_date = datetime.fromisoformat(pub_date_str).date()
            except (ValueError, TypeError):
                pass

        # Get publisher from multiple sources
        publisher = meta.get("Publisher") or meta.get("volumeInfo", {}).get("publisher")

        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13=isbn13,
            publisher=publisher,
            publication_date=pub_date,
            meta={
                "imageLinks": meta.get("imageLinks") or meta.get("volumeInfo", {}).get("imageLinks", {}),
                "pageCount": meta.get("pageCount") or meta.get("volumeInfo", {}).get("pageCount"),
                "industryIdentifiers": meta.get("industryIdentifiers") or meta.get("volumeInfo", {}).get("industryIdentifiers", []),
            },
        )
        db.session.add(manifestation)
        db.session.flush()
        manif_map[old_id] = manifestation
        stats["manifestations_created"] += 1

    # Process legacy items
    legacy_items = legacy_data.get("items", [])
    print(f"Processing {len(legacy_items)} legacy items...")

    for old_item in legacy_items:
        old_manif_id = old_item.get("manifestation_id")
        mani = manif_map.get(old_manif_id)

        if mani is None:
            print(f"Warning: Item {old_item.get('id')} references unknown manifestation {old_manif_id}")
            stats["skipped"] += 1
            continue
        manifestation = mani

        # At this point, manifestation is guaranteed to be not None
        assert manifestation is not None

        added_at = None
        added_at_str = old_item.get("added_at")
        if added_at_str:
            try:
                added_at = datetime.fromisoformat(added_at_str)
            except (ValueError, TypeError):
                added_at = datetime.utcnow()

        item = Item(
            manifestation_id=manifestation.id,
            owner_id=str(old_item.get("added_by", "1")),  # Map legacy client ID
            status="available",
            added_at=added_at,
            meta=old_item.get("meta", {}),
        )
        db.session.add(item)
        stats["items_created"] += 1

    db.session.commit()
    return stats


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="Migrate legacy iqoqo data to FRBR format")
    parser.add_argument("input_file", help="Path to legacy JSON export file")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing data before migration",
    )
    args = parser.parse_args()

    # Load legacy data
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    print(f"Loading legacy data from {input_path}...")
    with open(input_path, encoding="utf-8") as f:
        legacy_data = json.load(f)

    # Create Flask app context
    app = create_app()
    with app.app_context():
        print("Starting migration...")
        stats = migrate_legacy_data(legacy_data, clear_existing=args.clear)

        print("\n=== Migration Complete ===")
        print(f"Works created: {stats['works_created']}")
        print(f"Expressions created: {stats['expressions_created']}")
        print(f"Manifestations created: {stats['manifestations_created']}")
        print(f"Items created: {stats['items_created']}")
        print(f"Skipped: {stats['skipped']}")


if __name__ == "__main__":
    main()
