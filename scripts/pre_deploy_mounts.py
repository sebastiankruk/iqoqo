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
"""
Pre-deploy Mount and Permission Guards.

Ensures that:
  - Secrets file (.env) has 0600 permissions.
  - File-target mount sources (.allegro_token.json, deploy/nginx.conf) are regular files.
    If .allegro_token.json is an empty directory created by Docker, replaces it with a regular file.
    If a file-target source is a non-empty directory, aborts immediately.
  - Directory-target mount sources (app/static/covers, gallery, uploads, data, exports, shared, scripts, docs/ontology)
    are created with current user ownership and 0755 mode if absent, preventing root-owned directory creation by Docker.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DIRECTORY_MOUNTS = [
    "app/static/covers",
    "app/static/gallery",
    "app/static/uploads/raw_covers",
    "data",
    "exports",
    "scripts",
    "shared",
    "docs/ontology",
]


def prepare_deploy_mounts(deploy_dir_path: Path) -> int:
    deploy_dir = deploy_dir_path.resolve()
    deploy_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

    # 1. Tighten .env permissions (0600)
    env_file = deploy_dir / ".env"
    if env_file.exists() and env_file.is_file():
        try:
            os.chmod(env_file, 0o600)
        except OSError as e:
            print(f"⚠️ Warning: Could not set 0600 on {env_file}: {e}", file=sys.stderr)

    # 2. File-target mount: .allegro_token.json
    allegro_token = deploy_dir / ".allegro_token.json"
    if allegro_token.exists():
        if allegro_token.is_dir():
            # Check if directory is empty
            try:
                entries = list(allegro_token.iterdir())
                if not entries:
                    # Empty directory created by Docker: remove and replace with file
                    allegro_token.rmdir()
                    allegro_token.write_text("{}\n", encoding="utf-8")
                    os.chmod(allegro_token, 0o600)
                    print(f"🔧 Repaired {allegro_token}: replaced empty root directory with regular file.")
                else:
                    errors.append(
                        f"Mount source '{allegro_token}' is a non-empty directory ({len(entries)} items). "
                        "A regular file is required. Preserve contents and replace with regular file manually."
                    )
            except OSError as exc:
                errors.append(f"Cannot inspect or repair directory '{allegro_token}': {exc}")
        elif allegro_token.is_file():
            try:
                os.chmod(allegro_token, 0o600)
            except OSError:
                pass
    else:
        # Create missing .allegro_token.json as file with 0600
        try:
            allegro_token.write_text("{}\n", encoding="utf-8")
            os.chmod(allegro_token, 0o600)
        except OSError as exc:
            errors.append(f"Cannot create required token file '{allegro_token}': {exc}")

    # 3. File-target mount: deploy/nginx.conf
    nginx_conf = deploy_dir / "deploy" / "nginx.conf"
    if nginx_conf.exists() and nginx_conf.is_dir():
        errors.append(f"File-target mount source '{nginx_conf}' is a directory instead of a regular file.")

    # 4. Directory-target mounts: create with app user ownership and 0755 mode if absent
    for rel_dir in DIRECTORY_MOUNTS:
        target_dir = deploy_dir / rel_dir
        if target_dir.exists():
            if not target_dir.is_dir() and not target_dir.is_symlink():
                errors.append(f"Expected directory mount source '{target_dir}' is a regular file.")
        else:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                os.chmod(target_dir, 0o755)
            except OSError as exc:
                errors.append(f"Cannot create mount directory '{target_dir}': {exc}")

    if errors:
        print("❌ Pre-deploy mount validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)
        return 1

    print(f"✅ Pre-deploy mount validation passed for {deploy_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify and prepare bind-mount sources before docker compose up.")
    parser.add_argument(
        "deploy_dir",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Target deployment directory (default: current directory)",
    )
    args = parser.parse_args(argv)
    return prepare_deploy_mounts(args.deploy_dir)


if __name__ == "__main__":
    sys.exit(main())
