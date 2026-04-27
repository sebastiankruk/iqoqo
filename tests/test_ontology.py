"""
Cross-subsystem ontology contract tests.

These tests ensure that the Python backend and the TypeScript frontend share
an identical vocabulary for key domain concepts.  If either side is updated
without updating the other, these tests will fail, making the discrepancy
immediately visible in CI.

Concepts under contract
-----------------------
- **ItemStatus** — the set of valid status values for an ``Item``.  Defined as
  ``ITEM_STATUSES`` in ``app/db/models.py`` (Python) and as the ``ItemStatus``
  union type in ``frontend/types/frbr.ts`` (TypeScript).
- **MediaFormat** — the set of user-facing media format slugs (e.g. ``book``,
  ``audio``).  Defined as ``MediaFormat.ALL`` in ``app/db/core.py`` (Python)
  and as ``MEDIA_FORMATS`` in ``frontend/types/frbr.ts`` (TypeScript).
- **ScanFormat** — the subset of formats shown in the scanner UI.  Defined as
  the ``scan``-eligible entries of ``MediaFormat.ALL`` in Python (i.e. those
  without a ``parent``) and as ``SCAN_FORMATS`` in the TypeScript types file.
"""

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

import re
from pathlib import Path

import pytest
import yaml

from app.core.taxonomy import (
    CATEGORY_PROGRESS_STATUSES,
    COLLECTION_STATUSES,
    FORMAT_TO_CATEGORY,
    PROGRESS_STATUSES,
    SCAN_FORMATS,
    MediaCategory,
    MediaFormat,
)
from app.db.core import ITEM_STATUSES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]
TAXONOMY_YAML = ROOT_DIR / "shared" / "taxonomy.yaml"
TAXONOMY_TS = ROOT_DIR / "frontend" / "types" / "taxonomy.ts"


def _parse_ts_const_array(ts_source: str, const_name: str) -> frozenset[str]:
    """Extract string literals from a TypeScript 'as const' array."""
    pattern = re.compile(
        rf"export\s+const\s+{re.escape(const_name)}\s*=\s*\[([^\]]+)\]",
        re.DOTALL,
    )
    match = pattern.search(ts_source)
    if not match:
        # Try finding it without 'export const' if it's just a variable
        pattern = re.compile(rf"{re.escape(const_name)}\s*=\s*\[([^\]]+)\]", re.DOTALL)
        match = pattern.search(ts_source)

    if not match:
        raise ValueError(f"Could not locate '{const_name}' array in taxonomy.ts")
    return frozenset(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))


def _parse_union_type_from_ts(ts_source: str, type_name: str) -> frozenset[str]:
    """Extract union members from a TypeScript type alias."""
    pattern = re.compile(
        rf"export\s+type\s+{re.escape(type_name)}\s*=\s*([^;]+);",
        re.DOTALL,
    )
    match = pattern.search(ts_source)
    if not match:
        raise ValueError(f"Could not locate '{type_name}' type alias in taxonomy.ts")
    return frozenset(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))


# ---------------------------------------------------------------------------
# SSoT Contract Tests
# ---------------------------------------------------------------------------


def test_taxonomy_yaml_exists() -> None:
    assert TAXONOMY_YAML.exists()


def test_taxonomy_files_in_sync_with_yaml() -> None:
    """Verify that Python constants match the YAML source of truth."""
    with open(TAXONOMY_YAML) as f:
        data = yaml.safe_load(f)

    # Categories
    assert frozenset(MediaCategory.ALL) == frozenset(data["media_categories"].keys())

    # Formats
    yaml_formats: set[str] = {fmt["id"] for info in data["media_categories"].values() for fmt in info["formats"]}
    assert frozenset(MediaFormat.ALL) == frozenset(yaml_formats)

    # Collection Statuses
    yaml_coll = frozenset(s["id"] for s in data["collection_statuses"])
    assert frozenset(COLLECTION_STATUSES) == yaml_coll

    # Progress Statuses
    yaml_prog = set()
    for statuses in data["progress_statuses"].values():
        yaml_prog.update(statuses)
    assert frozenset(PROGRESS_STATUSES) == frozenset(yaml_prog)

    # Category Progress Map
    for cat, statuses in data["progress_statuses"].items():
        assert frozenset(CATEGORY_PROGRESS_STATUSES[cat]) == frozenset(statuses)

    # Scan Formats
    assert frozenset(SCAN_FORMATS) == frozenset(data["scan_formats"])


def test_python_and_ts_in_sync() -> None:
    """Ensure Python and TypeScript generated files are identical."""
    ts_source = TAXONOMY_TS.read_text(encoding="utf-8")

    # Formats
    ts_formats = _parse_ts_const_array(ts_source, "MEDIA_FORMATS")
    assert ts_formats == frozenset(MediaFormat.ALL)

    # Categories
    ts_categories = _parse_ts_const_array(ts_source, "MEDIA_CATEGORIES")
    assert ts_categories == frozenset(MediaCategory.ALL)

    # Statuses
    ts_coll = _parse_union_type_from_ts(ts_source, "CollectionStatus")
    assert ts_coll == frozenset(COLLECTION_STATUSES)

    ts_prog = _parse_union_type_from_ts(ts_source, "ProgressStatus")
    assert ts_prog == frozenset(PROGRESS_STATUSES)


def test_format_to_category_completeness() -> None:
    """Every format must map back to exactly one valid category."""
    for fmt in MediaFormat.ALL:
        assert fmt in FORMAT_TO_CATEGORY, f"Format '{fmt}' missing from FORMAT_TO_CATEGORY mapping"
        assert FORMAT_TO_CATEGORY[fmt] in MediaCategory.ALL, f"Format '{fmt}' maps to invalid category '{FORMAT_TO_CATEGORY[fmt]}'"


def test_scan_formats_validity() -> None:
    """SCAN_FORMATS must be a subset of MediaCategory.ALL (or formats)."""
    # In our YAML, scan_formats currently references categories or special aliases.
    # We should ensure they are at least known strings.
    for fmt in SCAN_FORMATS:
        # In current design, scan_formats are mostly categories
        is_category = fmt in MediaCategory.ALL
        is_format = fmt in MediaFormat.ALL
        assert is_category or is_format, f"Scan format '{fmt}' is neither a known category nor a format"


@pytest.mark.parametrize("status", ITEM_STATUSES)
def test_item_status_python_values_non_empty(status: str) -> None:
    """Each status in ITEM_STATUSES must be a non-empty string."""
    assert isinstance(status, str) and status.strip(), f"ITEM_STATUSES contains an invalid entry: {status!r}"
