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

from app.db.core import MediaFormat
from app.db.models import ITEM_STATUSES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: Absolute path to the TypeScript FRBR types file.
FRBR_TS = Path(__file__).resolve().parents[1] / "frontend" / "types" / "frbr.ts"


def _parse_ts_const_array(ts_source: str, const_name: str) -> frozenset[str]:
    """
    Extract the string literals from a TypeScript ``as const`` array.

    Parses a declaration of the form::

        export const MY_LIST = ["a", "b", "c"] as const;

    and returns ``frozenset({"a", "b", "c"})``.

    Args:
        ts_source: Full source text of the TypeScript file.
        const_name: Name of the const to extract.

    Returns:
        A frozenset of string literals found in the array.

    Raises:
        ValueError: If the declaration cannot be found.
    """
    pattern = re.compile(
        rf"export\s+const\s+{re.escape(const_name)}\s*=\s*\[([^\]]+)\]",
        re.DOTALL,
    )
    match = pattern.search(ts_source)
    if not match:
        raise ValueError(f"Could not locate '{const_name}' const array in frbr.ts")
    return frozenset(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))


def _parse_union_type_from_ts(ts_source: str, type_name: str) -> frozenset[str]:
    """Extract union members from a TypeScript type alias."""
    pattern = re.compile(
        rf"export\s+type\s+{re.escape(type_name)}\s*=\s*([^;]+);",
        re.DOTALL,
    )
    match = pattern.search(ts_source)
    if not match:
        raise ValueError(f"Could not locate '{type_name}' type alias in frbr.ts")
    return frozenset(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_frbr_ts_exists() -> None:
    """Verify that the TypeScript types file is present on disk."""
    assert FRBR_TS.exists(), f"Expected TypeScript types file at {FRBR_TS}. Has the frontend directory been moved?"


def test_item_status_ontology_in_sync() -> None:
    """Ensure that ITEM_STATUSES (Python) and the union of statuses (TypeScript) are identical."""
    ts_source = FRBR_TS.read_text(encoding="utf-8")

    # ProgressStatus and CollectionStatus should equal ITEM_STATUSES
    ts_progress = _parse_union_type_from_ts(ts_source, "ProgressStatus")
    ts_collection = _parse_union_type_from_ts(ts_source, "CollectionStatus")
    ts_statuses = ts_progress | ts_collection

    py_statuses = frozenset(ITEM_STATUSES)

    only_in_python = py_statuses - ts_statuses
    only_in_ts = ts_statuses - py_statuses

    messages: list[str] = []
    if only_in_python:
        messages.append(f"Statuses in ITEM_STATUSES (Python) but missing from TS: {sorted(only_in_python)}")
    if only_in_ts:
        messages.append(f"Statuses in TS but missing from ITEM_STATUSES (Python): {sorted(only_in_ts)}")

    assert not messages, "\n".join(messages)


@pytest.mark.parametrize("status", ITEM_STATUSES)
def test_item_status_python_values_non_empty(status: str) -> None:
    """Each status in ITEM_STATUSES must be a non-empty string."""
    assert isinstance(status, str) and status.strip(), f"ITEM_STATUSES contains an invalid entry: {status!r}"


# ---------------------------------------------------------------------------
# MediaFormat contract tests
# ---------------------------------------------------------------------------


def test_media_format_all_in_sync() -> None:
    """
    Ensure MediaFormat.ALL (Python) and MEDIA_FORMATS (TypeScript) are identical.

    This will fail if a format is added, removed, or renamed on one side
    without a corresponding change on the other.
    """
    ts_source = FRBR_TS.read_text(encoding="utf-8")
    ts_formats = _parse_ts_const_array(ts_source, "MEDIA_FORMATS")
    py_formats = frozenset(MediaFormat.ALL)

    only_in_python = py_formats - ts_formats
    only_in_ts = ts_formats - py_formats

    messages: list[str] = []
    if only_in_python:
        messages.append(f"Formats in MediaFormat.ALL (Python) but missing from MEDIA_FORMATS (TypeScript): {sorted(only_in_python)}")
    if only_in_ts:
        messages.append(f"Formats in MEDIA_FORMATS (TypeScript) but missing from MediaFormat.ALL (Python): {sorted(only_in_ts)}")

    assert not messages, "\n".join(messages)


def test_scan_formats_subset_of_media_formats() -> None:
    """
    Ensure SCAN_FORMATS (TypeScript) is a proper subset of MEDIA_FORMATS (TypeScript).

    ScanFormat represents only the top-level groupings shown in the scanner UI,
    not every leaf format (e.g. 'cd' and 'vinyl' are sub-formats of 'audio').
    """
    ts_source = FRBR_TS.read_text(encoding="utf-8")
    scan_formats = _parse_ts_const_array(ts_source, "SCAN_FORMATS")
    all_formats = _parse_ts_const_array(ts_source, "MEDIA_FORMATS")

    extras = scan_formats - all_formats
    assert not extras, f"SCAN_FORMATS contains values not present in MEDIA_FORMATS: {sorted(extras)}"


@pytest.mark.parametrize("fmt", MediaFormat.ALL)
def test_media_format_python_values_non_empty(fmt: str) -> None:
    """Each value in MediaFormat.ALL must be a non-empty string."""
    assert isinstance(fmt, str) and fmt.strip(), f"MediaFormat.ALL contains an invalid entry: {fmt!r}"
