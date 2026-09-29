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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""MOD-OPS-13 regression tests for centralised role/permission definitions.

Role grants used to be hardcoded as Python predicates inside
``scripts/sync_db_permissions.py``, while ``app/api/admin.py`` separately
hardcoded the same protected-role set as a literal. Two independent lists of
role policy is two things to forget to update.

The Single Source of Truth is now the ``roles:`` section of
``shared/permissions.yaml``; ``scripts/sync_permissions.py`` generates
``RoleName``, ``ROLE_PERMISSION_PATTERNS`` and ``resolve_role_permissions`` into
``app/core/permissions.py`` from it.

These tests pin three things: the generated module matches the YAML, the
resolver reproduces the *original* inline predicates exactly (so the
centralisation changed no behaviour), and no role-policy literal remains in
application or script code.
"""

import ast
from pathlib import Path
from typing import cast

import pytest
import yaml

from app.core.permissions import (
    PROTECTED_ROLE_NAMES,
    ROLE_PERMISSION_PATTERNS,
    PermissionName,
    RoleName,
    resolve_role_permissions,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = REPO_ROOT / "shared" / "permissions.yaml"


@pytest.fixture(scope="module")
def yaml_data() -> dict:
    """Parsed shared/permissions.yaml.

    `cast` is needed because `yaml.safe_load` is typed as returning `Any`; this
    keeps the declared return type honest for mypy without weakening it to Any.
    """
    with open(YAML_PATH, encoding="utf-8") as f:
        return cast(dict, yaml.safe_load(f))


# ── Generated module agrees with the YAML ──────────────────────────────────


def test_role_enum_matches_yaml(yaml_data: dict) -> None:
    """Every role in the YAML must exist in the generated RoleName enum."""
    yaml_roles = {r["name"] for r in yaml_data["roles"]}
    enum_roles = {r.value for r in RoleName}
    assert yaml_roles == enum_roles, f"YAML roles {yaml_roles} != enum roles {enum_roles}"


def test_permission_patterns_match_yaml(yaml_data: dict) -> None:
    """The generated glob patterns must be exactly what the YAML declares."""
    for role in yaml_data["roles"]:
        expected = tuple(role.get("permissions", []))
        actual = ROLE_PERMISSION_PATTERNS[role["name"]]
        assert actual == expected, f"role {role['name']}: generated {actual} != yaml {expected}"


def test_protected_role_names_match_yaml(yaml_data: dict) -> None:
    expected = {r["name"] for r in yaml_data["roles"] if r.get("protected", False)}
    assert set(PROTECTED_ROLE_NAMES) == expected


def test_generated_module_is_reproducible_from_yaml(yaml_data: dict) -> None:
    """`sync_permissions.py --verify` must pass: the checked-in module is what
    the YAML currently generates, so nobody hand-edited the generated file."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/sync_permissions.py", "--verify"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"generated permissions module is stale:\n{result.stdout}\n{result.stderr}"


def test_generated_module_survives_black_without_rewriting() -> None:
    """The generator must emit output `black` will not rewrite.

    Regression: the generator originally emitted every role's pattern tuple on a
    single line. `black --check` runs in CI and exploded the longer ones, so the
    next generator run produced different bytes and `--verify` failed against a
    permissions.yaml that had not changed at all. The failure looked like a
    permissions drift when it was purely a formatter disagreement.

    A single-element tuple must keep its comma (it is a 1-tuple), while a
    multi-element tuple must NOT gain a trailing comma (that is black's "magic
    trailing comma", which forces an explosion even when the line would fit).
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "black", "--check", "app/core/permissions.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "regenerating the permissions module leaves black-unstable output;\n" f"{result.stdout}\n{result.stderr}"


# ── Behaviour is identical to the pre-refactor inline predicates ───────────


def test_admin_receives_every_permission() -> None:
    names = [p.value for p in PermissionName]
    assert resolve_role_permissions(RoleName.ADMIN, names) == set(names)


def test_contributor_grants_match_the_original_predicate() -> None:
    """Reproduces the predicate that used to live in sync_db_permissions.py."""
    names = [p.value for p in PermissionName]
    expected = {
        p
        for p in names
        if p.endswith(":metadata")
        or p == PermissionName.EDIT_COVER.value
        or p.startswith("llm_generate:")
        or p == PermissionName.DELETE_ITEM.value
        or p == PermissionName.ESCALATE_RESOLVE.value
    }
    assert resolve_role_permissions(RoleName.CONTRIBUTOR, names) == expected


def test_user_grants_match_the_original_set() -> None:
    names = [p.value for p in PermissionName]
    expected = {
        PermissionName.WRITE_ITEM.value,
        PermissionName.UPDATE_ITEM.value,
        PermissionName.DELETE_ITEM.value,
        PermissionName.READ_METADATA.value,
        PermissionName.UPLOAD_COVER.value,
        PermissionName.REGENERATE_COVER.value,
        PermissionName.LLM_GENERATE_METADATA.value,
        PermissionName.LLM_GENERATE_COVER.value,
        PermissionName.ESCALATE_REQUEST.value,
        PermissionName.TICKETS_CREATOR.value,
    }
    granted = resolve_role_permissions(RoleName.USER, names)
    assert granted == expected, f"missing: {sorted(expected - granted)}; extra: {sorted(granted - expected)}"


# ── Resolver behaviour ────────────────────────────────────────────────────


def test_resolver_is_case_insensitive() -> None:
    """A role name arriving as 'Admin' must resolve the same as 'admin'."""
    assert resolve_role_permissions("Admin", ["write:item"]) == resolve_role_permissions("admin", ["write:item"])


def test_resolver_returns_empty_for_an_unknown_role() -> None:
    """Fail closed: a role with no definition must not be granted anything."""
    assert resolve_role_permissions("superuser", [p.value for p in PermissionName]) == set()


def test_resolver_matches_hand_added_permissions_by_pattern_not_enum() -> None:
    """A permission an admin created outside the enum must still be granted.

    This is why patterns are resolved against the database contents instead of
    against PermissionName: enumerating the enum would silently skip custom
    permissions.
    """
    custom = ["custom:metadata", "custom:privileged"]
    granted = resolve_role_permissions(RoleName.CONTRIBUTOR, custom)
    assert granted == {"custom:metadata"}
    # admin takes everything, custom or not
    assert resolve_role_permissions(RoleName.ADMIN, custom) == set(custom)


def test_resolver_never_reports_an_unrequested_permission() -> None:
    """Grants are always a subset of the input: no phantom permissions."""
    names = [p.value for p in PermissionName]
    for role in RoleName:
        assert resolve_role_permissions(role, names) <= set(names)


# ── No duplicated role policy left behind ────────────────────────────────


def _string_constants(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def test_admin_api_does_not_redefine_the_protected_role_set() -> None:
    """app/api/admin.py must import the set, not re-spell it."""
    source = (REPO_ROOT / "app" / "api" / "admin.py").read_text(encoding="utf-8")
    assert "PROTECTED_ROLE_NAMES" in source
    assert 'protected_roles = {"admin", "user", "contributor"}' not in source


def test_sync_script_does_not_hardcode_role_permission_predicates() -> None:
    """sync_db_permissions.py must delegate to the generated resolver."""
    source = (REPO_ROOT / "scripts" / "sync_db_permissions.py").read_text(encoding="utf-8")
    assert "resolve_role_permissions" in source
    # The original contributor predicate, in any of its spellings, is gone.
    assert 'endswith(":metadata")' not in source
    assert 'startswith("llm_generate:")' not in source


def test_role_names_are_not_spread_as_bare_literals_across_the_app() -> None:
    """Guards against the definitions drifting back out of the SSoT.

    A bare set literal naming all three built-in roles is the shape that
    duplicated policy in the first place. Single comparisons (``role.name ==
    "admin"``) are legitimate business logic and are not flagged.

    app/core/permissions.py is excluded: it is the generated home of these
    names and is the one place a set literal is correct.
    """
    offenders: list[str] = []
    for py_file in sorted((REPO_ROOT / "app").rglob("*.py")):
        if py_file.name == "permissions.py" and py_file.parent.name == "core":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Set):
                continue
            values = {elt.value for elt in node.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)}
            if values >= {"admin", "user", "contributor"}:
                offenders.append(f"{py_file.relative_to(REPO_ROOT)}:{node.lineno}")
    assert not offenders, f"role-set literals duplicate app.core.permissions: {offenders}"
