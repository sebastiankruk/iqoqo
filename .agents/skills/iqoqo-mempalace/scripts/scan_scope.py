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
"""Scan project and determine which scopes to index for MemPalace.

Respects .iqoqo-mempalace-scope.yaml (or .iqoqo-mykg-scope.yaml).
Categorizes scopes into 'projects' (code and notes) and 'convos' (AI session transcripts).
Strictly excludes .mykg_sessions/, static covers/images, and deprecated versions.
"""

import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

DEFAULT_EXCLUDES = [
    "**/__pycache__/**",
    "**/*.pyc",
    "**/node_modules/**",
    "**/.git/**",
    "**/graphify-out/**",
    "**/mykg_sessions/**",
    "**/.mykg_sessions/**",
    "**/.venv/**",
    "**/.iqoqo-mempalace/**",
    "**/.iqoqo-mykg/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.next/**",
    "**/dist/**",
    "**/build/**",
    "**/*.egg-info/**",
    "**/coverage/**",
    "**/.coverage",
    "**/.tox/**",
    "**/instance/**",
    "**/data/**",
    "**/app/static/covers/**",
    "**/app/static/gallery/**",
    "**/screenshots/**",
    "**/images/**",
    "**/.DS_Store",
    "**/Thumbs.db",
]


def should_exclude(file_path: str, exclude_patterns: Optional[List[str]] = None) -> bool:
    """Check if a file should be excluded based on patterns."""
    patterns = exclude_patterns or DEFAULT_EXCLUDES
    path = Path(file_path)
    path_str = str(path).replace("\\", "/")

    for pattern in patterns:
        norm_pattern = pattern.replace("\\", "/")
        # Match glob via PurePath
        if path.match(norm_pattern) or path.match(norm_pattern.lstrip("*/")):
            return True

        # Match fnmatch on full path or filename
        if fnmatch.fnmatch(path_str, norm_pattern) or fnmatch.fnmatch(path.name, norm_pattern):
            return True

        # Match directory substring (e.g., "app/static/covers" in "app/static/covers/foo.jpg")
        clean_target = norm_pattern.strip("*/")
        if clean_target and clean_target in path_str:
            return True

        for part in path.parts:
            if fnmatch.fnmatch(part, clean_target):
                return True

    return False


def get_version(project_root: Path) -> str:
    """Read version from package.json or pyproject.toml."""
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            if "version" in data:
                return str(data["version"])
        except Exception:
            pass

    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
        except Exception:
            pass

    return "0.7.17"


def load_scope_config(project_root: Path) -> Optional[Dict[str, Any]]:
    """Load .iqoqo-mempalace-scope.yaml or fallback to .iqoqo-mykg-scope.yaml."""
    for config_name in [".iqoqo-mempalace-scope.yaml", ".iqoqo-mykg-scope.yaml"]:
        config_file = project_root / config_name
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not parse {config_name}: {e}", file=sys.stderr)
    return None


def resolve_scopes(
    project_root: Path,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Resolve project and conversation scopes with file lists."""
    config = load_scope_config(project_root) or {}
    version = get_version(project_root)

    raw_project_scopes = config.get("scopes", [
        "docs",
        "openspec/specs",
        ".context/notes/sre",
        ".context/notes/bugs",
        ".context/notes/code",
        ".context/notes/design",
        ".context/notes/dev",
        ".context/notes/marketing",
        ".context/notes/openspec",
        ".context/notes/plan",
        ".context/notes/review",
        ".context/notes/security",
        ".context/notes/tests",
        ".context/notes/tools",
        ".context/notes/notes",
        "app",
        "frontend",
        "migrations",
        "deploy",
        "scripts",
        "shared",
        "tests",
        "Makefile",
        "docker-compose.yml",
        "docker-compose.prod.yml",
    ])

    raw_convos_scopes = config.get("convos_scopes", [".context/ai-memory"])
    exclude_patterns = config.get("exclude", DEFAULT_EXCLUDES)

    project_scopes: List[Dict[str, Any]] = []
    convos_scopes: List[Dict[str, Any]] = []

    # Resolve project scopes
    for scope_str in raw_project_scopes:
        scope_path = project_root / scope_str
        if not scope_path.exists():
            continue

        if scope_path.is_file():
            if not should_exclude(str(scope_path), exclude_patterns):
                project_scopes.append({
                    "path": str(scope_path.relative_to(project_root)),
                    "type": "file",
                    "mode": "projects",
                    "files": [str(scope_path.relative_to(project_root))],
                })
        elif scope_path.is_dir():
            files = []
            for item in scope_path.rglob("*"):
                if item.is_file() and not should_exclude(str(item), exclude_patterns):
                    # Skip common binary formats
                    if item.suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".svg", ".pyc", ".bin", ".tar", ".gz", ".zip"]:
                        files.append(str(item.relative_to(project_root)))
            if files:
                project_scopes.append({
                    "path": str(scope_path.relative_to(project_root)),
                    "type": "dir",
                    "mode": "projects",
                    "count": len(files),
                    "files": files,
                })

    # Resolve conversation scopes (version-scoped)
    for scope_str in raw_convos_scopes:
        base_path = project_root / scope_str
        target_path = base_path / version if (base_path / version).exists() else base_path
        if not target_path.exists():
            continue

        conv_files = []
        for item in target_path.rglob("*.md"):
            if item.is_file() and not should_exclude(str(item), exclude_patterns):
                conv_files.append(str(item.relative_to(project_root)))

        if conv_files:
            convos_scopes.append({
                "path": str(target_path.relative_to(project_root)),
                "type": "dir",
                "mode": "convos",
                "version": version,
                "count": len(conv_files),
                "files": conv_files,
            })

    return project_scopes, convos_scopes, exclude_patterns


def main() -> None:
    """CLI Entry point for scope scanner."""
    project_root = Path.cwd()
    project_scopes, convos_scopes, _ = resolve_scopes(project_root)

    state_dir = project_root / ".iqoqo-mempalace"
    state_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = state_dir / "scope_manifest.json"

    manifest_data = {
        "version": get_version(project_root),
        "wing": "iqoqo",
        "project_scopes": project_scopes,
        "convos_scopes": convos_scopes,
    }

    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    if "--json" in sys.argv:
        print(json.dumps(manifest_data, indent=2))
        return

    total_project_files = sum(s.get("count", len(s.get("files", []))) for s in project_scopes)
    total_convos_files = sum(s.get("count", len(s.get("files", []))) for s in convos_scopes)

    print("=" * 60)
    print("  iQoQo MemPalace Scopes Discovered")
    print("=" * 60)
    print(f"  Target Wing: iqoqo (version: {manifest_data['version']})")
    print("-" * 60)
    print("  Project Scopes (Codebase & Selected Notes):")
    for s in project_scopes:
        count = s.get("count", 1)
        print(f"    - {s['path']:35} ({count} files)")
    print(f"  Total Project Files: {total_project_files}")
    print("-" * 60)
    print("  Conversation Scopes (AI Memory):")
    for s in convos_scopes:
        count = s.get("count", 1)
        print(f"    - {s['path']:35} ({count} files, mode=convos)")
    print(f"  Total Conversation Files: {total_convos_files}")
    print("=" * 60)
    print(f"Manifest written to: {manifest_file.relative_to(project_root)}")


if __name__ == "__main__":
    main()
