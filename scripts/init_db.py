#!/usr/bin/env python3
"""
Initialize iqoqo database with seed data.

This script checks if the database is empty and optionally loads initial data.

Usage:
    python scripts/init_db.py [--seed-file path/to/data.json]
"""

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

import argparse
import sys
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy.exc import ProgrammingError

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app import create_app
from app.core.data_manager import DataManager
from app.db import db


def init_database(seed_file: Path | None = None, reset: bool = False):
    """
    Initialize the database.

    Args:
        seed_file: Optional path to a JSON file containing seed data.
        reset: If True, drops all tables before creating them.
    """
    app = create_app()

    with app.app_context():
        if reset:
            print("Dropping all tables...")
            try:
                db.drop_all()
            except ProgrammingError as e:
                if "must be owner of table" in str(e):
                    print("\nError: Insufficient privileges to drop tables.", file=sys.stderr)
                    print("The configured database user does not own the tables.", file=sys.stderr)
                    print("Please drop the tables manually using a database tool.", file=sys.stderr)
                    sys.exit(1)
                raise

        # Create all tables
        print("Creating database tables...")
        db.create_all()

        # Stamp the Alembic migration version to 'head' after a fresh create_all().
        # create_all() builds the schema from ORM model definitions (always reflecting
        # the latest structure), so there is nothing left for Alembic to migrate.
        # Without this stamp, running `flask db upgrade head` afterwards would try to
        # re-apply schema-separation steps (e.g. ALTER TABLE public.works SET SCHEMA
        # catalog) on tables that already exist in the correct schema, causing errors.
        alembic_cfg = AlembicConfig("migrations/alembic.ini")
        alembic_cfg.set_main_option("script_location", "migrations")
        alembic_command.stamp(alembic_cfg, "head")

        # Check if database is empty
        try:
            stats = DataManager.get_stats()
        except ProgrammingError:
            print("\nError: Database schema mismatch detected.", file=sys.stderr)
            print("The existing tables might be outdated or incompatible with the current models.", file=sys.stderr)
            print("Use --reset to drop and recreate the database tables (WARNING: Data will be lost).", file=sys.stderr)
            sys.exit(1)

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
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables before initialization",
    )
    args = parser.parse_args()

    init_database(seed_file=args.seed_file, reset=args.reset)


if __name__ == "__main__":
    main()
