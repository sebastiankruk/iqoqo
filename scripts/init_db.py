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
import os
import re
import sys
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app import create_app
from app.core.data_manager import DataManager
from app.db import db


def _validated_seed_admin(app):
    """Require explicit, usable bootstrap credentials before importing seed Items."""
    from scripts.init_auth import validate_admin_password

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    if not admin_email or admin_email != app.config.get("ADMIN_EMAIL"):
        raise ValueError("Set an explicit ADMIN_EMAIL before importing seed data.")
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", admin_email):
        raise ValueError("ADMIN_EMAIL must be a valid email address for the bootstrap administrator.")
    domain = admin_email.rsplit("@", 1)[1].lower()
    placeholder_domains = {"example.com", "example.org", "example.net", "localhost", "iqoqo.local"}
    non_routable_suffixes = (".local", ".localhost", ".test", ".example", ".invalid")
    if domain in placeholder_domains or domain.endswith(non_routable_suffixes):
        raise ValueError("ADMIN_EMAIL must not use a placeholder or non-routable example domain.")
    admin_password = validate_admin_password(app.config.get("ADMIN_PASSWORD"))
    return admin_email, admin_password


def init_database(seed_file: Path | None = None, reset: bool = False, force: bool = False):
    """
    Initialize the database.

    Args:
        seed_file: Optional path to a JSON file containing seed data.
        reset: If True, drops all tables before creating them.
        force: If True, bypasses interactive confirmation prompts.
    """
    app = create_app()

    with app.app_context():
        if reset:
            # 1. Production environment safeguard
            if os.environ.get("FLASK_ENV") == "production" and os.environ.get("ALLOW_PROD_RESET") != "1":
                print(
                    "\nError: Refusing to reset database in production environment without ALLOW_PROD_RESET=1.",
                    file=sys.stderr,
                )
                sys.exit(1)

            # 2. Interactive typed confirmation prompt
            is_test = "pytest" in sys.modules
            if not force and not is_test:
                db_name = db.engine.url.database or "iqoqo"
                print(f"\n⚠️ WARNING: This will drop all tables in database '{db_name}'.")
                try:
                    confirm = input(f"Type '{db_name}' to confirm table drop: ")
                except (EOFError, KeyboardInterrupt):
                    confirm = ""
                if confirm.strip() != db_name:
                    print("Operation cancelled: Typed confirmation did not match database name.", file=sys.stderr)
                    sys.exit(1)

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

        # Pre-create schemas if running against PostgreSQL
        if db.engine.dialect.name == "postgresql":
            from sqlalchemy import text

            for schema_name in ("auth", "catalog", "inventory", "social", "config"):
                db.session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            db.session.commit()

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
                # Do not import seed Items until a configured, validated
                # bootstrap account exists. This account is the explicit
                # owner fallback for legacy Items without a resolvable UUID.
                admin_email, admin_password = _validated_seed_admin(app)
                from scripts.init_auth import run_init_auth

                run_init_auth(app)
                from app.db.models import User

                bootstrap_admin = db.session.execute(db.select(User).filter_by(email=admin_email)).scalar_one_or_none()
                if bootstrap_admin is None or not bootstrap_admin.password_hash or not admin_password:
                    raise ValueError("Could not initialize the configured bootstrap administrator.")
                counts = DataManager.import_from_file(str(seed_file), default_owner_id=bootstrap_admin.id)
                print("\nSeed data imported successfully:")
                print(f"  Works: {counts['works']}")
                print(f"  Expressions: {counts['expressions']}")
                print(f"  Manifestations: {counts['manifestations']}")
                print(f"  Items: {counts['items']}")
            except (OSError, ValueError, SQLAlchemyError) as e:
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass interactive confirmation prompt",
    )
    args = parser.parse_args()

    init_database(seed_file=args.seed_file, reset=args.reset, force=args.force)


if __name__ == "__main__":
    main()
