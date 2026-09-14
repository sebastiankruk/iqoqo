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
"""Migrate existing API secrets and credentials from .env to the encrypted DB registry.

Reads credentials from an environment file (default: .env), saves them
into the InstanceSettings database table with Fernet encryption at rest,
and comments them out in the .env file with a migration marker.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # pylint: disable=wrong-import-position
from app import create_app  # pylint: disable=wrong-import-position
from app.api.admin import API_KEYS  # pylint: disable=wrong-import-position
from app.core.config_service import CONFIG_KEY_BLOCKLIST  # pylint: disable=wrong-import-position
from app.db.models import InstanceSettings  # pylint: disable=wrong-import-position
from app.db.settings import SENSITIVE_SETTING_KEYS  # pylint: disable=wrong-import-position

# Secrets and credentials eligible for DB migration
MIGRATABLE_KEYS: frozenset[str] = frozenset((set(API_KEYS) | set(SENSITIVE_SETTING_KEYS)) - set(CONFIG_KEY_BLOCKLIST))

ENV_VAR_PATTERN = re.compile(r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_env_line(line: str) -> tuple[str, str, str] | None:
    """Parse a single line from a .env file into prefix, key, and value.

    Returns:
        Tuple of (prefix, key, unquoted_value) or None if not a variable assignment.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    match = ENV_VAR_PATTERN.match(line)
    if not match:
        return None

    prefix = match.group(1)
    key = match.group(2)
    raw_val = match.group(3).strip()

    val = raw_val
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        if len(val) >= 2:
            val = val[1:-1]
    elif " #" in val:
        val = val.split(" #", 1)[0].strip()

    return prefix, key, val


def migrate_env_secrets(
    env_file_path: Path,
    dry_run: bool = False,
    overwrite: bool = False,
    backup: bool = True,
) -> dict[str, Any]:
    """Migrate sensitive API credentials from .env file into InstanceSettings table.

    Args:
        env_file_path: Path to the .env file to process.
        dry_run: If True, do not persist to database or modify file.
        overwrite: If True, overwrite existing DB values with .env values.
        backup: If True, create a .bak copy before modifying .env.

    Returns:
        Dictionary containing lists of migrated, updated, and skipped keys.
    """
    results: dict[str, Any] = {
        "migrated": [],
        "updated": [],
        "already_synced": [],
        "skipped_conflict": [],
        "skipped_empty": [],
        "backup_path": None,
    }

    if not env_file_path.exists():
        print(f"[!] Target file does not exist: {env_file_path}")
        return results

    lines = env_file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    modified_lines: list[str] = []
    has_modifications = False

    for line in lines:
        parsed = parse_env_line(line)
        if not parsed:
            modified_lines.append(line)
            continue

        _, key, value = parsed
        if key not in MIGRATABLE_KEYS:
            modified_lines.append(line)
            continue

        if not value:
            results["skipped_empty"].append(key)
            modified_lines.append(line)
            continue

        existing_val = InstanceSettings.get_value(key)

        if existing_val == value:
            results["already_synced"].append(key)
            commented = f"# [MIGRATED TO DB] {line.lstrip()}"
            modified_lines.append(commented)
            has_modifications = True
            continue

        if existing_val is not None and not overwrite:
            results["skipped_conflict"].append(key)
            modified_lines.append(line)
            continue

        # Key is new or overwrite is requested
        if not dry_run:
            InstanceSettings.set_value(key, value)

        if existing_val is not None:
            results["updated"].append(key)
        else:
            results["migrated"].append(key)

        commented = f"# [MIGRATED TO DB] {line.lstrip()}"
        modified_lines.append(commented)
        has_modifications = True

    if has_modifications and not dry_run:
        if backup:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_path = env_file_path.with_name(f"{env_file_path.name}.bak.{timestamp}")
            shutil.copy2(env_file_path, backup_path)
            results["backup_path"] = str(backup_path)

        env_file_path.write_text("".join(modified_lines), encoding="utf-8")

    return results


def main() -> int:
    """CLI entrypoint for environment secret migration."""
    parser = argparse.ArgumentParser(description="Migrate API secrets from .env into encrypted database settings.")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=PROJECT_ROOT / ".env",
        help="Path to .env file (default: .env in project root)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without modifying database or .env file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing database settings with values from .env",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a backup of .env file before editing",
    )

    args = parser.parse_args()

    if args.env_file.exists():
        load_dotenv(args.env_file, override=True)

    app = create_app()
    with app.app_context():
        print(f"[*] Scanning {args.env_file} for migratable secrets...")
        if args.dry_run:
            print("[*] Mode: DRY RUN (no changes will be applied)")

        stats = migrate_env_secrets(
            env_file_path=args.env_file,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            backup=not args.no_backup,
        )

        for key in stats["migrated"]:
            print(f"  [+] Migrated to DB: {key}")
        for key in stats["updated"]:
            print(f"  [~] Updated in DB (overwrite): {key}")
        for key in stats["already_synced"]:
            print(f"  [=] Already in DB, commented out: {key}")
        for key in stats["skipped_conflict"]:
            print(f"  [!] Skipped conflict (exists in DB, use --overwrite): {key}")
        for key in stats["skipped_empty"]:
            print(f"  [-] Skipped empty value: {key}")

        total_touched = len(stats["migrated"]) + len(stats["updated"]) + len(stats["already_synced"])

        if stats["backup_path"]:
            print(f"[*] Backup created at: {stats['backup_path']}")

        print(f"[*] Done! Total secrets moved or synced: {total_touched}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
