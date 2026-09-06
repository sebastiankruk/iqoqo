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
"""Scan .context/ directories and return markdown files to index.

Respects .graphifyignore and auto-detects current version from package.json.
Writes chunk manifests to graphify-out/.iqoqo_chunks/ for batch processing.

Supports --check mode for incremental updates:
  --check: Compare current files against manifest, report changes
"""

import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path


def get_version(project_root: Path) -> str:
    """Read version from package.json or pyproject.toml."""
    package_json = project_root / "package.json"
    if package_json.exists():
        data = json.loads(package_json.read_text())
        return data.get("version", "unknown")

    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            return match.group(1)

    return "unknown"


def load_graphifyignore(project_root: Path) -> list:
    """Load .graphifyignore patterns."""
    ignore_file = project_root / ".graphifyignore"
    if not ignore_file.exists():
        return []

    patterns = []
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def is_ignored(file_path: Path, patterns: list, project_root: Path) -> bool:
    """Check if a file matches any ignore pattern."""
    rel_path = file_path.relative_to(project_root)
    rel_str = str(rel_path)

    for pattern in patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith("/"):
            dir_pattern = pattern.rstrip("/")
            if fnmatch(rel_str, dir_pattern + "/*") or fnmatch(rel_str, dir_pattern):
                return True
        # Handle wildcard patterns
        elif "*" in pattern or "?" in pattern:
            if fnmatch(rel_str, pattern) or fnmatch(rel_str, pattern + "/*"):
                return True
        # Handle exact path or prefix
        else:
            if rel_str.startswith(pattern) or rel_str == pattern:
                return True

    return False


def scan_directory(directory: Path, patterns: list, project_root: Path) -> list:
    """Recursively scan directory for .md files, respecting ignore patterns."""
    files = []
    for item in directory.rglob("*.md"):
        if not is_ignored(item, patterns, project_root):
            files.append(str(item))
    return sorted(files)


def create_chunks(files: list, chunk_size: int = 20) -> list:
    """Split files into chunks of specified size."""
    return [files[i : i + chunk_size] for i in range(0, len(files), chunk_size)]


def get_file_metadata(file_path: str) -> dict:
    """Get file mtime and size for change detection."""
    stat = os.stat(file_path)
    return {
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def load_manifest(project_root: Path) -> dict:
    """Load previous scan manifest."""
    manifest_file = project_root / "graphify-out" / ".iqoqo_chunks" / "manifest.json"
    if manifest_file.exists():
        return json.loads(manifest_file.read_text())
    return {}


def save_manifest(project_root: Path, manifest: dict):
    """Save scan manifest for future comparison."""
    manifest_file = project_root / "graphify-out" / ".iqoqo_chunks" / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))


def check_changes(current_files: list, manifest: dict) -> tuple:
    """Compare current files against manifest. Returns (changed_files, is_first_run)."""
    if not manifest:
        return current_files, True

    changed = []
    for file_path in current_files:
        current_meta = get_file_metadata(file_path)
        prev_meta = manifest.get(file_path)

        if not prev_meta:
            # New file
            changed.append(file_path)
        elif current_meta["mtime"] != prev_meta["mtime"] or current_meta["size"] != prev_meta["size"]:
            # Modified file
            changed.append(file_path)

    # Check for deleted files (optional - could be used for cleanup)
    # current_set = set(current_files)
    # for prev_file in manifest:
    #     if prev_file not in current_set:
    #         pass  # File deleted

    return changed, False


def scan_context(project_root: Path) -> tuple:
    """Scan .context/ and return (all_files, version, chunks)."""
    version = get_version(project_root)
    patterns = load_graphifyignore(project_root)

    # Scan .context/notes/
    notes_dir = project_root / ".context" / "notes"
    notes_files = []
    if notes_dir.exists():
        notes_files = scan_directory(notes_dir, patterns, project_root)

    # Scan .context/ai-memory/<version>/
    ai_memory_dir = project_root / ".context" / "ai-memory" / version
    ai_memory_files = []
    if ai_memory_dir.exists():
        ai_memory_files = scan_directory(ai_memory_dir, patterns, project_root)

    all_files = notes_files + ai_memory_files
    chunks = create_chunks(all_files)

    return all_files, version, chunks, notes_files, ai_memory_files


def main():
    project_root = Path.cwd()
    check_mode = "--check" in sys.argv

    version = get_version(project_root)

    if check_mode:
        # Check mode: compare against manifest
        manifest = load_manifest(project_root)

        all_files, version, chunks, notes_files, ai_memory_files = scan_context(project_root)

        changed_files, is_first_run = check_changes(all_files, manifest)

        if is_first_run:
            print(f"first_run: true")
            print(f"changed_files: {len(all_files)}")
            print(f"changed_chunks: {len(chunks)}")
            print(f"total_files: {len(all_files)}")
            # Write manifest for future comparisons
            new_manifest = {f: get_file_metadata(f) for f in all_files}
            save_manifest(project_root, new_manifest)
            sys.exit(0)

        if not changed_files:
            print("unchanged")
            print("changed_files: 0")
            print("changed_chunks: 0")
            print(f"total_files: {len(all_files)}")
            sys.exit(0)

        # Find which chunks contain changed files
        changed_set = set(changed_files)
        changed_chunk_indices = set()
        for i, chunk in enumerate(chunks):
            for file_path in chunk:
                if file_path in changed_set:
                    changed_chunk_indices.add(i)
                    break

        print(f"first_run: false")
        print(f"changed_files: {len(changed_files)}")
        print(f"changed_chunks: {len(changed_chunk_indices)}")
        print(f"total_files: {len(all_files)}")
        print(f"version: {version}")

        # Update manifest
        new_manifest = {f: get_file_metadata(f) for f in all_files}
        save_manifest(project_root, new_manifest)

        # Write changed chunk indices for incremental extraction
        chunks_dir = project_root / "graphify-out" / ".iqoqo_chunks"
        changed_chunks_file = chunks_dir / "changed_chunks.json"
        changed_chunks_file.write_text(json.dumps(sorted(changed_chunk_indices)))

        sys.exit(0)

    # Full scan mode
    all_files, version, chunks, notes_files, ai_memory_files = scan_context(project_root)

    print(f"Detected version: {version}")
    print(f"Loaded {len(load_graphifyignore(project_root))} ignore patterns")
    print(f"Found {len(notes_files)} markdown files in .context/notes/")
    print(f"Found {len(ai_memory_files)} markdown files in .context/ai-memory/{version}/")
    print(f"Total files to index: {len(all_files)}")
    print(f"Split into {len(chunks)} chunks of ~20 files each")

    # Write chunk manifests
    chunks_dir = project_root / "graphify-out" / ".iqoqo_chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    for i, chunk in enumerate(chunks):
        chunk_file = chunks_dir / f"chunk_{i:03d}.json"
        chunk_file.write_text(json.dumps(chunk, indent=2))

    print(f"Wrote {len(chunks)} chunk manifests to {chunks_dir}")

    # Write summary
    summary = {
        "version": version,
        "total_files": len(all_files),
        "notes_files": len(notes_files),
        "ai_memory_files": len(ai_memory_files),
        "chunks": len(chunks),
        "chunk_dir": str(chunks_dir),
    }
    summary_file = chunks_dir / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2))
    print(f"Wrote summary to {summary_file}")

    # Write manifest for future comparison
    manifest = {f: get_file_metadata(f) for f in all_files}
    save_manifest(project_root, manifest)
    print(f"Wrote manifest for future change detection")


if __name__ == "__main__":
    main()
