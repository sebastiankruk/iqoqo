#!/usr/bin/env python3
"""
Initialize iqoqo database with seed data.

This script checks if the database is empty and optionally loads initial data.

Usage:
    python scripts/init_db.py [--seed-file path/to/data.json]
"""

import argparse
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app import create_app
from app.core.data_manager import DataManager
from app.db import db


def init_database(seed_file: Path | None = None):
    """
    Initialize the database.

    Args:
        seed_file: Optional path to a JSON file containing seed data.
    """
    app = create_app()

    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()

        # Check if database is empty
        stats = DataManager.get_stats()
        total_records = sum(stats.values())

        print("Current database statistics:")
        print(f"  Works: {stats['works']}")
        print(f"  Expressions: {stats['expressions']}")
        print(f"  Manifestations: {stats['manifestations']}")
        print(f"  Items: {stats['items']}")

        if total_records > 0:
            print("\nDatabase is not empty. Skipping seed data import.")
            print("Use --force flag to import anyway (will not clear existing data).")
            return

        if seed_file and seed_file.exists():
            print(f"\nLoading seed data from {seed_file}...")
            try:
                counts = DataManager.import_from_file(str(seed_file))
                print("\nSeed data imported successfully:")
                print(f"  Works: {counts['works']}")
                print(f"  Expressions: {counts['expressions']}")
                print(f"  Manifestations: {counts['manifestations']}")
                print(f"  Items: {counts['items']}")
            except (OSError, ValueError) as e:
                print(f"Error importing seed data: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            if seed_file:
                print(f"Warning: Seed file not found: {seed_file}")
            print("\nDatabase initialized with no seed data.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize iqoqo database with optional seed data")
    parser.add_argument(
        "--seed-file",
        type=Path,
        help="Path to JSON file containing seed data",
    )
    args = parser.parse_args()

    init_database(seed_file=args.seed_file)


if __name__ == "__main__":
    main()
