#!/usr/bin/env python3
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
import os
import sys

import psycopg2
from dotenv import load_dotenv


def fix_alembic_version():
    """
    Increases the alembic_version.version_num column size to 255 characters.
    This is required for iqoqo 0.2.0 which uses longer migration IDs.
    """
    # Load .env if it exists in current or parent directory
    load_dotenv()

    # Try different env files if DATABASE_URL is not set
    if not os.getenv("DATABASE_URL"):
        for env_file in [".env.preview", ".env.local", ".env.dev"]:
            if os.path.exists(env_file):
                print(f"  Loading environment from {env_file}...")
                load_dotenv(env_file, override=True)
                if os.getenv("DATABASE_URL"):
                    break

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL not found in environment or .env files.")
        sys.exit(1)

    print("🚀 Ensuring alembic_version table can handle long version IDs...")

    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        # Check if table exists
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version');")
        if not cur.fetchone()[0]:
            print("  Table 'alembic_version' does not exist yet. Skipping fix.")
            return

        # Execute the fix
        print("  Executing: ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(255);")
        cur.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(255);")

        # Reconcile renamed migration revision identifiers
        migration_rename_map = {
            "20260814_add_comments_column_to_feedback": "20260814_feedback_comments",
        }
        for old_rev, new_rev in migration_rename_map.items():
            cur.execute(
                "UPDATE alembic_version SET version_num = %s WHERE version_num = %s;",
                (new_rev, old_rev),
            )
            if cur.rowcount > 0:
                print(f"  Reconciled legacy migration identifier: {old_rev} -> {new_rev}")

        print("✅ Fix applied successfully!")

        cur.close()
        conn.close()
    except (psycopg2.Error, OSError, ValueError, RuntimeError) as e:
        print(f"❌ Error applying fix: {e}")
        # We don't exit with error here because if the DB is not reachable,
        # the main startup script will fail anyway with a better error message.
        # But we do exit if it's a real SQL error that isn't just "connection refused".
        if "connection refused" not in str(e).lower():
            sys.exit(1)


if __name__ == "__main__":
    fix_alembic_version()
