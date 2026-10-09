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
Synchronise runtime files from a source checkout into a deployment directory.

Replaces symlinks with real files, records content hashes in a manifest,
removes stale files, and provides drift verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_FILENAME = ".deploy_manifest.json"

SYNC_ITEMS = [
    "docker-compose.yml",
    "docker-compose.prebuilt.yml",
    "docker-compose.monitoring.yml",
    "Makefile",
    "scripts",
    "shared",
    "deploy/nginx.conf",
    "docs/ontology",
]


def sha256_file(path: Path) -> str:
    """Compute sha256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_is_descendant(target: Path, base: Path) -> bool:
    """Return True if target resolves within base."""
    resolved_target = target.resolve()
    resolved_base = base.resolve()
    return resolved_target == resolved_base or resolved_base in resolved_target.parents


def collect_source_files(src_dir: Path) -> dict[str, Path]:
    """Collect all eligible files from src_dir according to SYNC_ITEMS."""
    src_dir = src_dir.resolve()
    files: dict[str, Path] = {}

    for item_str in SYNC_ITEMS:
        item_path = src_dir / item_str
        if not item_path.exists():
            continue

        if item_path.is_file():
            if item_path.is_symlink() and not check_is_descendant(item_path.resolve(), src_dir):
                raise ValueError(f"Refusing to sync: symlink '{item_str}' resolves outside source tree to '{item_path.resolve()}'")
            files[item_str] = item_path
        elif item_path.is_dir():
            for root, dirs, filenames in os.walk(item_path):
                root_path = Path(root)
                for d in list(dirs):
                    d_path = root_path / d
                    if d_path.is_symlink() and not check_is_descendant(d_path.resolve(), src_dir):
                        raise ValueError(f"Refusing to sync: directory symlink '{d_path}' resolves outside source tree")
                for fname in filenames:
                    f_path = root_path / fname
                    if f_path.is_symlink() and not check_is_descendant(f_path.resolve(), src_dir):
                        raise ValueError(f"Refusing to sync: file symlink '{f_path}' resolves outside source tree")
                    rel_name = str(f_path.relative_to(src_dir))
                    files[rel_name] = f_path

    return files


def sync_deploy_directory(src_dir: Path, deploy_dir: Path) -> tuple[int, int, int]:
    """Sync runtime files into deploy_dir.

    Returns (created_count, updated_count, removed_count).
    """
    src_dir = src_dir.resolve()
    deploy_dir = deploy_dir.resolve()
    deploy_dir.mkdir(parents=True, exist_ok=True)

    src_files = collect_source_files(src_dir)

    manifest_path = deploy_dir / MANIFEST_FILENAME
    old_manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                old_manifest = json.load(f)
        except Exception:
            old_manifest = {}

    old_files = old_manifest.get("files", {})

    created: list[str] = []
    updated: list[str] = []
    removed: list[str] = []

    new_manifest_files: dict[str, dict[str, str]] = {}

    for rel_path, src_path in sorted(src_files.items()):
        dest_path = deploy_dir / rel_path
        src_hash = sha256_file(src_path)
        src_mode = oct(stat.S_IMODE(src_path.stat().st_mode))

        new_manifest_files[rel_path] = {
            "sha256": src_hash,
            "mode": src_mode,
        }

        # If any parent directory in deploy_dir is a symlink, replace it with a real directory
        rel_parts = Path(rel_path).parts
        current = deploy_dir
        for part in rel_parts[:-1]:
            current = current / part
            if current.is_symlink():
                current.unlink()
                current.mkdir(parents=True, exist_ok=True)

        # If dest is a symlink, remove it so it becomes a real file
        if dest_path.is_symlink():
            dest_path.unlink()

        dest_needs_copy = False
        if not dest_path.exists():
            created.append(rel_path)
            dest_needs_copy = True
        else:
            dest_hash = sha256_file(dest_path)
            dest_mode = oct(stat.S_IMODE(dest_path.stat().st_mode))
            if dest_hash != src_hash or dest_mode != src_mode:
                updated.append(rel_path)
                dest_needs_copy = True

        if dest_needs_copy:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            # Ensure permissions match source exactly
            shutil.copymode(src_path, dest_path)

    # Remove files previously synced that no longer exist in source
    for old_rel in list(old_files.keys()):
        if old_rel not in src_files:
            target_to_remove = deploy_dir / old_rel
            if target_to_remove.exists() or target_to_remove.is_symlink():
                if target_to_remove.is_file() or target_to_remove.is_symlink():
                    target_to_remove.unlink()
                    removed.append(old_rel)

    # Save manifest
    new_manifest = {
        "version": "1.0",
        "synced_at": datetime.now(UTC).isoformat(),
        "source_dir": str(src_dir),
        "files": new_manifest_files,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(new_manifest, f, indent=2)

    total_changes = len(created) + len(updated) + len(removed)
    if total_changes == 0:
        print(f"📋 Manifest: {len(new_manifest_files)} files tracked at {deploy_dir}")
        print("✅ Deployment directory is in sync (no changes).")
    else:
        print(f"📦 Synced {len(new_manifest_files)} files to {deploy_dir}:")
        if created:
            print(f"  + Created ({len(created)}):")
            for p in created:
                print(f"    + {p} (sha256: {new_manifest_files[p]['sha256'][:12]}...)")
        if updated:
            print(f"  ~ Updated ({len(updated)}):")
            for p in updated:
                print(f"    ~ {p} (sha256: {new_manifest_files[p]['sha256'][:12]}...)")
        if removed:
            print(f"  - Removed ({len(removed)}):")
            for p in removed:
                print(f"    - {p}")
        print(f"Manifest written to {manifest_path}")

    return len(created), len(updated), len(removed)


def verify_deploy_directory(deploy_dir: Path) -> int:
    """Verify manifest against actual files on disk in deploy_dir."""
    deploy_dir = deploy_dir.resolve()
    manifest_path = deploy_dir / MANIFEST_FILENAME

    if not manifest_path.exists():
        print(f"❌ Error: No deployment manifest found at {manifest_path}. Run sync first.", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as exc:
        print(f"❌ Error: Could not read manifest {manifest_path}: {exc}", file=sys.stderr)
        return 1

    files = manifest.get("files", {})
    drifts: list[str] = []

    for rel_path, meta in sorted(files.items()):
        dest_path = deploy_dir / rel_path
        if not dest_path.exists():
            drifts.append(f"Missing file: {rel_path}")
            continue

        if dest_path.is_symlink():
            drifts.append(f"File became symlink: {rel_path} -> {dest_path.resolve()}")
            continue

        actual_hash = sha256_file(dest_path)
        expected_hash = meta.get("sha256")
        if actual_hash != expected_hash:
            drifts.append(f"Content drift: {rel_path} (expected sha256:{expected_hash[:12]}, actual:{actual_hash[:12]})")

        actual_mode = oct(stat.S_IMODE(dest_path.stat().st_mode))
        expected_mode = meta.get("mode")
        if expected_mode and actual_mode != expected_mode:
            drifts.append(f"Permission drift: {rel_path} (expected {expected_mode}, actual {actual_mode})")

    if drifts:
        print(f"❌ Deployment directory drift detected ({len(drifts)} issues):", file=sys.stderr)
        for d in drifts:
            print(f"  • {d}", file=sys.stderr)
        return 1

    print(f"✅ Deployment directory verified: all {len(files)} files match manifest without drift.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync runtime files into an iQoQo deployment directory or verify manifest.")
    parser.add_argument("src_or_deploy", type=Path, help="Source checkout dir (for sync) or deployment dir (for --verify)")
    parser.add_argument("deploy_dir", type=Path, nargs="?", help="Target deployment directory (for sync)")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify deployment directory against existing manifest instead of syncing.",
    )

    args = parser.parse_args(argv)

    if args.verify:
        target_dir = args.src_or_deploy
        return verify_deploy_directory(target_dir)

    if not args.deploy_dir:
        parser.error("deploy_dir is required when syncing. Usage: sync_deploy_dir.py SRC_DIR DEPLOY_DIR")

    sync_deploy_directory(args.src_or_deploy, args.deploy_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
