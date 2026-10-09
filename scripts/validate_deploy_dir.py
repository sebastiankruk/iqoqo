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
Validate a source-free iQoQo deployment directory against the deployment contract.

Checks:
  - Required compose files present (docker-compose.yml or docker-compose.prebuilt.yml)
  - Required env file present (.env)
  - Runtime files (scripts/, shared/, deploy/nginx.conf, docs/ontology/) must not be
    symlinks resolving outside the deployment directory. (Symlinks resolving within
    the deployment directory are permitted).
  - File-target mount sources (.allegro_token.json, deploy/nginx.conf) must not be directories.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    kind: str
    path: str
    message: str
    remedy: str


RUNTIME_PATHS = [
    "scripts",
    "shared",
    "deploy/nginx.conf",
    "deploy/otel-collector-local.yaml",
    "deploy/otel-collector-prod.yaml",
    "docs/ontology",
]

FILE_TARGET_MOUNTS = [
    ".allegro_token.json",
    "deploy/nginx.conf",
    "deploy/otel-collector-local.yaml",
    "deploy/otel-collector-prod.yaml",
]


def check_is_descendant(target: Path, base: Path) -> bool:
    """Return True if target resolves within base."""
    resolved_target = target.resolve()
    resolved_base = base.resolve()
    return resolved_target == resolved_base or resolved_base in resolved_target.parents


def validate_deployment_dir(deploy_dir_path: Path) -> list[Violation]:
    """Inspect deploy_dir_path and return all contract violations."""
    deploy_dir = deploy_dir_path.resolve()
    violations: list[Violation] = []

    if not deploy_dir.exists() or not deploy_dir.is_dir():
        violations.append(
            Violation(
                kind="Deployment Directory Existence",
                path=str(deploy_dir_path),
                message=f"Deployment directory does not exist or is not a directory: {deploy_dir_path}",
                remedy=f"Create deployment directory: mkdir -p '{deploy_dir_path}'",
            )
        )
        return violations

    # 1. Required env file
    env_file = deploy_dir / ".env"
    if not env_file.exists():
        violations.append(
            Violation(
                kind="Required Environment Configuration",
                path=str(deploy_dir / ".env"),
                message="Required env file '.env' is absent.",
                remedy=f"Create env configuration at '{deploy_dir}/.env'.",
            )
        )

    # 2. Required compose files
    has_compose = (deploy_dir / "docker-compose.yml").exists() or (deploy_dir / "docker-compose.prebuilt.yml").exists()
    if not has_compose:
        violations.append(
            Violation(
                kind="Required Compose Specification",
                path=str(deploy_dir / "docker-compose.yml"),
                message="Required compose file ('docker-compose.yml' or 'docker-compose.prebuilt.yml') is absent.",
                remedy=f"Sync or copy compose files into '{deploy_dir}'.",
            )
        )

    # 3. File-target mounts that are directories
    for rel_mount in FILE_TARGET_MOUNTS:
        mount_path = deploy_dir / rel_mount
        if mount_path.exists() and mount_path.is_dir():
            violations.append(
                Violation(
                    kind="Invalid File-Target Mount Type",
                    path=str(mount_path),
                    message=f"File-target mount source '{rel_mount}' is a directory instead of a regular file.",
                    remedy=(
                        f"If empty, remove directory '{mount_path}' and create as regular file; "
                        "if non-empty, inspect and preserve contents before recreating."
                    ),
                )
            )

    # 4. Runtime files resolving outside deployment directory
    for rel_runtime in RUNTIME_PATHS:
        runtime_path = deploy_dir / rel_runtime
        if runtime_path.is_symlink():
            try:
                target = runtime_path.resolve()
            except RuntimeError:
                violations.append(
                    Violation(
                        kind="Broken Symlink",
                        path=str(runtime_path),
                        message=f"Runtime path '{rel_runtime}' is a broken symlink.",
                        remedy=f"Replace symlink at '{runtime_path}' with real files.",
                    )
                )
                continue

            if not check_is_descendant(target, deploy_dir):
                violations.append(
                    Violation(
                        kind="External Symlink Escaping Deployment Directory",
                        path=str(runtime_path),
                        message=(
                            f"Runtime file '{rel_runtime}' is a symlink resolving outside deployment directory: "
                            f"{runtime_path} -> {target}"
                        ),
                        remedy="Replace symlink with real files using `scripts/sync_deploy_dir.py`.",
                    )
                )

    return violations


def format_report(violations: list[Violation]) -> str:
    """Format violations grouped by kind with actionable remedies."""
    if not violations:
        return "✅ Deployment directory contract verified: 0 violations found."

    lines: list[str] = [
        "❌ Deployment directory contract violations detected:",
        "",
    ]

    by_kind: dict[str, list[Violation]] = {}
    for v in violations:
        by_kind.setdefault(v.kind, []).append(v)

    for kind, items in by_kind.items():
        lines.append(f"── {kind} ({len(items)}) ──")
        for item in items:
            lines.append(f"  • Path:   {item.path}")
            lines.append(f"    Issue:  {item.message}")
            lines.append(f"    Remedy: {item.remedy}")
            lines.append("")

    lines.append(f"Total violations: {len(violations)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an iQoQo deployment directory layout against the self-contained contract.")
    parser.add_argument("deploy_dir", type=Path, help="Target deployment directory to validate")
    args = parser.parse_args(argv)

    violations = validate_deployment_dir(args.deploy_dir)
    report = format_report(violations)
    if violations:
        print(report, file=sys.stderr)
        return 1

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
