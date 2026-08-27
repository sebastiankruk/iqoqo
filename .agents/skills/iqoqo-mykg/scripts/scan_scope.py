#!/usr/bin/env python3
"""Scan project and determine which scopes to index for mykg.

Respects .iqoqo-mykg-scope.yaml and auto-detects iqoqo-specific folders.
Writes scope manifests to .iqoqo-mykg/ for batch processing.

Supports --check mode for incremental updates:
  --check: Compare current files against manifest, report changes
"""

import fnmatch
import json
import os
import re
import sys
import tempfile
from pathlib import Path


DEFAULT_EXCLUDES = [
    "**/__pycache__/**",
    "**/*.pyc",
    "**/node_modules/**",
    "**/.git/**",
    "**/graphify-out/**",
    "**/mykg_sessions/**",
    "**/.mykg_sessions/**",
    "**/.venv/**",
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
    "**/data/**",  # Local data files
    "**/deploy/data/**",
    "**/.DS_Store",
    "**/Thumbs.db",
]


def should_exclude(file_path: str, exclude_patterns: list = None) -> bool:
    """Check if a file should be excluded based on patterns."""
    patterns = exclude_patterns or DEFAULT_EXCLUDES
    path = Path(file_path)

    for pattern in patterns:
        # Simple glob matching
        if fnmatch.fnmatch(str(path), pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
        # Check if any parent matches
        parts = path.parts
        for part in parts:
            if fnmatch.fnmatch(part, pattern.strip("*/")):
                return True

    return False


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


def load_scope_config(project_root: Path) -> dict:
    """Load .iqoqo-mykg-scope.yaml or return None."""
    config_file = project_root / ".iqoqo-mykg-scope.yaml"
    if config_file.exists():
        try:
            import yaml
            return yaml.safe_load(config_file.read_text())
        except ImportError:
            # Fallback: simple YAML-like parsing for scopes list
            content = config_file.read_text()
            scopes = []
            in_scopes = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped == "scopes:":
                    in_scopes = True
                    continue
                if in_scopes and stripped.startswith("-"):
                    scope = stripped.lstrip("-").strip().strip('"').strip("'")
                    if scope:
                        scopes.append(scope)
                elif in_scopes and stripped and not stripped.startswith("#"):
                    # End of scopes section
                    break
            return {"scopes": scopes} if scopes else None
    return None


def resolve_wildcards(pattern: str, project_root: Path) -> list:
    """Resolve wildcard patterns like docker* to actual paths."""
    # Check if it's a directory pattern
    if pattern.endswith("/"):
        pattern = pattern.rstrip("/")
        for item in project_root.iterdir():
            if item.is_dir() and fnmatch.fnmatch(item.name, pattern):
                return [str(item)]
        return []

    # Check for wildcard in filename
    if "*" in pattern or "?" in pattern:
        results = []
        # Search in project root
        for item in project_root.iterdir():
            if fnmatch.fnmatch(item.name, pattern):
                results.append(str(item))
        # Also search one level deep for patterns like docker-compose.*.yml
        if not results:
            for item in project_root.rglob(pattern):
                if item.is_file():
                    results.append(str(item))
        return sorted(results)

    # Exact path
    exact = project_root / pattern
    if exact.exists():
        return [str(exact)]

    return []


def auto_detect_scopes(project_root: Path) -> list:
    """Auto-detect iqoqo-specific scopes."""
    scopes = []

    # Documentation
    docs_dir = project_root / "docs"
    if docs_dir.exists():
        scopes.append("docs")

    # Context notes (select subdirectories, excluding meta dirs)
    notes_dir = project_root / ".context" / "notes"
    excluded_note_dirs = {
        ".mykg_sessions", "ai-memory", "bin", "images", "screenshots",
        "setup", "archive", "antigravity", "gemini", "opencode", "agy"
    }
    if notes_dir.exists() and notes_dir.is_dir():
        for subdir in sorted(notes_dir.iterdir()):
            if subdir.is_dir() and subdir.name not in excluded_note_dirs:
                scopes.append(f".context/notes/{subdir.name}")

    # AI memory for current version
    version = get_version(project_root)
    ai_memory_dir = project_root / ".context" / "ai-memory" / version
    if ai_memory_dir.exists():
        scopes.append(f".context/ai-memory/{version}")

    # Code
    for code_dir in ["app", "frontend", "migrations"]:
        path = project_root / code_dir
        if path.exists():
            scopes.append(code_dir)

    # Docker files
    docker_patterns = ["docker-compose*.yml", "Dockerfile*", ".dockerignore"]
    docker_files = []
    for pattern in docker_patterns:
        for item in project_root.iterdir():
            if fnmatch.fnmatch(item.name, pattern):
                docker_files.append(str(item))
    if docker_files:
        # Create a temp directory name for docker files
        scopes.append("__docker_files__")

    # Deployment
    deploy_dir = project_root / "deploy"
    if deploy_dir.exists():
        scopes.append("deploy")

    # Scripts
    scripts_dir = project_root / "scripts"
    if scripts_dir.exists():
        scopes.append("scripts")

    # Makefile
    makefile = project_root / "Makefile"
    if makefile.exists():
        scopes.append("Makefile")

    return scopes


def get_scope_paths(scopes: list, project_root: Path) -> dict:
    """Convert scope names to actual paths, handling special cases."""
    scope_paths = {}
    docker_files = []

    for scope in scopes:
        if scope == "__docker_files__":
            # Collect docker files
            docker_patterns = ["docker-compose*.yml", "Dockerfile*", ".dockerignore"]
            for pattern in docker_patterns:
                for item in project_root.iterdir():
                    if fnmatch.fnmatch(item.name, pattern):
                        docker_files.append(item)
            continue

        # Resolve wildcards
        resolved = resolve_wildcards(scope, project_root)
        if resolved:
            scope_paths[scope] = resolved
        else:
            # Try as exact path
            exact = project_root / scope
            if exact.exists():
                scope_paths[scope] = [str(exact)]

    # Handle docker files specially
    if docker_files:
        # Create a temporary directory with symlinks to docker files
        # Use /tmp to avoid being caught by exclude patterns
        temp_dir = Path(tempfile.mkdtemp(prefix="iqoqo-mykg-docker-"))
        # Create new symlinks
        for f in docker_files:
            link = temp_dir / f.name
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(f.resolve())
        scope_paths["docker_files"] = [str(temp_dir)]

    return scope_paths


def get_file_metadata(file_path: str) -> dict:
    """Get file mtime and size for change detection."""
    stat = os.stat(file_path)
    return {
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def load_manifest(project_root: Path) -> dict:
    """Load previous scan manifest."""
    manifest_file = project_root / ".iqoqo-mykg" / "manifest.json"
    if manifest_file.exists():
        return json.loads(manifest_file.read_text())
    return {}


def save_manifest(project_root: Path, manifest: dict):
    """Save scan manifest for future comparison."""
    manifest_file = project_root / ".iqoqo-mykg" / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))


def collect_files_in_scope(scope_path: str, exclude_patterns: list = None) -> list:
    """Collect all files in a scope path, respecting exclude patterns."""
    path = Path(scope_path)
    if not path.exists():
        return []
    if path.is_file():
        if should_exclude(str(path), exclude_patterns):
            return []
        return [str(path)]
    # Directory
    files = []
    for item in path.rglob("*"):
        if item.is_file() and not should_exclude(str(item), exclude_patterns):
            files.append(str(item))
    return files


def check_changes(scope_paths: dict, manifest: dict) -> dict:
    """Compare current scopes against manifest. Returns changed scopes."""
    changed_scopes = {}

    for scope_name, paths in scope_paths.items():
        scope_changed = False
        current_files = []
        for path in paths:
            current_files.extend(collect_files_in_scope(path))

        scope_manifest = manifest.get(scope_name, {})

        for file_path in current_files:
            current_meta = get_file_metadata(file_path)
            prev_meta = scope_manifest.get(file_path)

            if not prev_meta:
                scope_changed = True
                break
            elif (current_meta["mtime"] != prev_meta["mtime"] or
                  current_meta["size"] != prev_meta["size"]):
                scope_changed = True
                break

        # Check for deleted files
        current_set = set(current_files)
        for prev_file in scope_manifest:
            if prev_file not in current_set:
                scope_changed = True
                break

        if scope_changed:
            changed_scopes[scope_name] = paths

    return changed_scopes


def get_latest_session(project_root: Path) -> str:
    """Find the most recent mykg session."""
    sessions_dir = project_root / "mykg_sessions"
    if not sessions_dir.exists() or not sessions_dir.is_symlink():
        sessions_dir = project_root / ".mykg_sessions"

    if not sessions_dir.exists():
        return None

    sessions = []
    for item in sessions_dir.iterdir():
        if item.is_dir():
            try:
                # Parse timestamp from directory name
                sessions.append((item.name, item.stat().st_mtime))
            except (ValueError, OSError):
                continue

    if not sessions:
        return None

    # Sort by mtime descending
    sessions.sort(key=lambda x: x[1], reverse=True)
    return sessions[0][0]


def main():
    project_root = Path.cwd()
    check_mode = "--check" in sys.argv

    # Ensure .iqoqo-mykg directory exists
    state_dir = project_root / ".iqoqo-mykg"
    state_dir.mkdir(parents=True, exist_ok=True)

    # Load or auto-detect scopes
    config = load_scope_config(project_root)
    if config and "scopes" in config:
        scopes = config["scopes"]
        print(f"Loaded {len(scopes)} scopes from .iqoqo-mykg-scope.yaml")
    else:
        scopes = auto_detect_scopes(project_root)
        print(f"Auto-detected {len(scopes)} scopes")

    # Resolve scope paths
    scope_paths = get_scope_paths(scopes, project_root)

    if check_mode:
        manifest = load_manifest(project_root)

        if not manifest:
            print("first_run: true")
            print(f"changed_scopes: {len(scope_paths)}")
            print(f"total_scopes: {len(scope_paths)}")
            # Write manifest
            new_manifest = {}
            for scope_name, paths in scope_paths.items():
                scope_files = {}
                for path in paths:
                    for f in collect_files_in_scope(path):
                        scope_files[f] = get_file_metadata(f)
                new_manifest[scope_name] = scope_files
            save_manifest(project_root, new_manifest)
            sys.exit(0)

        changed_scopes = check_changes(scope_paths, manifest)

        if not changed_scopes:
            print("unchanged")
            print("changed_scopes: 0")
            print(f"total_scopes: {len(scope_paths)}")
            sys.exit(0)

        print(f"first_run: false")
        print(f"changed_scopes: {len(changed_scopes)}")
        print(f"total_scopes: {len(scope_paths)}")
        print(f"latest_session: {get_latest_session(project_root) or 'none'}")
        for scope_name in changed_scopes:
            print(f"  changed: {scope_name}")

        # Write changed scopes for update script
        changed_file = state_dir / "changed_scopes.json"
        changed_file.write_text(json.dumps(changed_scopes, indent=2))

        # Update manifest
        new_manifest = {}
        for scope_name, paths in scope_paths.items():
            scope_files = {}
            for path in paths:
                for f in collect_files_in_scope(path):
                    scope_files[f] = get_file_metadata(f)
            new_manifest[scope_name] = scope_files
        save_manifest(project_root, new_manifest)

        sys.exit(0)

    # Full scan mode
    version = get_version(project_root)
    latest_session = get_latest_session(project_root)

    print(f"Detected version: {version}")
    print(f"Latest session: {latest_session or 'none'}")
    print(f"Scopes to index: {len(scope_paths)}")
    for scope_name, paths in scope_paths.items():
        file_count = sum(len(collect_files_in_scope(p)) for p in paths)
        print(f"  {scope_name}: {file_count} files")

    # Write scope manifest
    scope_manifest = {
        "version": version,
        "scopes": {k: v for k, v in scope_paths.items()},
        "latest_session": latest_session,
    }
    manifest_file = state_dir / "scope_manifest.json"
    manifest_file.write_text(json.dumps(scope_manifest, indent=2))
    print(f"Wrote scope manifest to {manifest_file}")

    # Write initial manifest for change detection
    new_manifest = {}
    for scope_name, paths in scope_paths.items():
        scope_files = {}
        for path in paths:
            for f in collect_files_in_scope(path):
                scope_files[f] = get_file_metadata(f)
        new_manifest[scope_name] = scope_files
    save_manifest(project_root, new_manifest)
    print(f"Wrote file manifest for future change detection")


if __name__ == "__main__":
    main()
