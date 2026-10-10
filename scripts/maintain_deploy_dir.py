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
Deployment Directory Maintenance Script.

Attributes and reports debris and manages secret snapshot retention:
  - Reports debris (files not created by any deploy step, e.g. stray redirects).
  - Recognises application data directories (covers, gallery, exports, data) and protects them.
  - Inspects .env.bak.* snapshots containing secrets, warns, and prunes beyond retention threshold.
  - Safe by default: removes nothing without --prune.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_DIRECTORIES = {
    "app",
    "data",
    "exports",
    "frontend",
    ".opencode",
}

KNOWN_ROOT_ITEMS = {
    ".env",
    ".env.preview",
    ".allegro_token.json",
    ".deploy_manifest.json",
    "docker-compose.yml",
    "docker-compose.prebuilt.yml",
    "docker-compose.monitoring.yml",
    "Makefile",
    "scripts",
    "shared",
    "deploy",
    "docs",
}


def inspect_deploy_directory(
    deploy_dir_path: Path,
    retention: int = 5,
    prune: bool = False,
    prune_debris: bool = False,
) -> int:
    deploy_dir = deploy_dir_path.resolve()
    if not deploy_dir.exists() or not deploy_dir.is_dir():
        print(f"❌ Error: Deployment directory does not exist: {deploy_dir}", file=sys.stderr)
        return 1

    manifest_path = deploy_dir / ".deploy_manifest.json"
    manifest_files: set[str] = set()
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
                manifest_files = set(data.get("files", {}).keys())
        except Exception:
            pass

    debris_files: list[Path] = []
    env_backups: list[Path] = []

    for item in deploy_dir.iterdir():
        name = item.name
        if name.startswith(".env.bak."):
            env_backups.append(item)
            continue

        if name in KNOWN_ROOT_ITEMS or name in DATA_DIRECTORIES:
            continue

        # Check if tracked in manifest
        rel = str(item.relative_to(deploy_dir))
        if rel in manifest_files:
            continue

        debris_files.append(item)

    print("=" * 60)
    print(f"DEPLOYMENT DIRECTORY MAINTENANCE: {deploy_dir}")
    print("=" * 60)
    print()

    # 1. Debris reporting
    if debris_files:
        print(f"⚠️  Debris / Unrecognized items ({len(debris_files)}):")
        for d in sorted(debris_files):
            size = d.stat().st_size if d.is_file() else "dir"
            print(f"  • {d.name} (size: {size} bytes)")
        print()
        if prune_debris:
            print("🧹 Pruning recognized debris files...")
            for d in debris_files:
                if d.is_file() or d.is_symlink():
                    d.unlink()
                    print(f"  - Removed file {d.name}")
        else:
            print("  ℹ️  No debris removed by default. Pass --prune-debris to delete.")
    else:
        print("✅ No unrecognized debris files found.")
    print()

    # 2. Environment backup retention
    env_backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"🔐 Environment snapshot retention: {len(env_backups)} snapshots found (retention: {retention})")
    if env_backups:
        print("  ⚠️  WARNING: .env.bak.* snapshots contain plaintext and encrypted secrets.")
        for i, b in enumerate(env_backups):
            status = "KEEP" if i < retention else "ELIGIBLE FOR PRUNING"
            print(f"  [{i+1}/{len(env_backups)}] {b.name} -> {status}")

    excess = env_backups[retention:]
    if excess:
        print()
        if prune:
            print(f"🧹 Pruning {len(excess)} old .env snapshots beyond retention limit...")
            for old_bak in excess:
                old_bak.unlink()
                print(f"  - Pruned {old_bak.name}")
        else:
            print(f"  ℹ️  {len(excess)} snapshot(s) exceed retention limit. Run with --prune to delete them.")
    print()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect and maintain deployment directory debris and secret snapshots.")
    parser.add_argument("deploy_dir", type=Path, help="Target deployment directory")
    parser.add_argument(
        "--retention",
        type=int,
        default=5,
        help="Number of .env.bak.* snapshots to retain (default: 5)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Prune .env.bak.* snapshots exceeding retention limit",
    )
    parser.add_argument(
        "--prune-debris",
        action="store_true",
        help="Remove unrecognized non-data debris files",
    )

    args = parser.parse_args(argv)
    return inspect_deploy_directory(
        args.deploy_dir,
        retention=args.retention,
        prune=args.prune,
        prune_debris=args.prune_debris,
    )


if __name__ == "__main__":
    sys.exit(main())
