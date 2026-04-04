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

from app.db.models import ITEM_STATUSES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: Absolute path to the TypeScript FRBR types file.
FRBR_TS = Path(__file__).resolve().parents[1] / "frontend" / "types" / "frbr.ts"


def _parse_item_status_from_ts(ts_source: str) -> frozenset[str]:
    """
    Extract the union members from the ``ItemStatus`` type alias.

    Parses a declaration of the form::

        export type ItemStatus = "a" | "b" | "c";

    and returns ``frozenset({"a", "b", "c"})``.

    Args:
        ts_source: Full source text of the TypeScript file.

    Returns:
        A frozenset of status string literals extracted from the union.

    Raises:
        ValueError: If the ``ItemStatus`` declaration cannot be found.
    """
    pattern = re.compile(
        r"export\s+type\s+ItemStatus\s*=\s*([^;]+);",
        re.DOTALL,
    )
    match = pattern.search(ts_source)
    if not match:
        raise ValueError("Could not locate 'ItemStatus' type alias in frbr.ts")

    union_body = match.group(1)
    # Extract all string literals from the union body (single or double quotes)
    return frozenset(re.findall(r"['\"]([^'\"]+)['\"]", union_body))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_frbr_ts_exists() -> None:
    """Verify that the TypeScript types file is present on disk."""
    assert FRBR_TS.exists(), f"Expected TypeScript types file at {FRBR_TS}. Has the frontend directory been moved?"


def test_item_status_ontology_in_sync() -> None:
    """
    Ensure that ITEM_STATUSES (Python) and ItemStatus (TypeScript) are identical.

    This is the primary cross-subsystem contract test.  It will fail whenever
    a status value is added, removed, or renamed in one subsystem without a
    corresponding change in the other.
    """
    ts_source = FRBR_TS.read_text(encoding="utf-8")
    ts_statuses = _parse_item_status_from_ts(ts_source)
    py_statuses = frozenset(ITEM_STATUSES)

    only_in_python = py_statuses - ts_statuses
    only_in_ts = ts_statuses - py_statuses

    messages: list[str] = []
    if only_in_python:
        messages.append(f"Statuses present in ITEM_STATUSES (Python) but missing from ItemStatus (TypeScript): {sorted(only_in_python)}")
    if only_in_ts:
        messages.append(f"Statuses present in ItemStatus (TypeScript) but missing from ITEM_STATUSES (Python): {sorted(only_in_ts)}")

    assert not messages, "\n".join(messages)


@pytest.mark.parametrize("status", ITEM_STATUSES)
def test_item_status_python_values_non_empty(status: str) -> None:
    """Each status in ITEM_STATUSES must be a non-empty string."""
    assert isinstance(status, str) and status.strip(), f"ITEM_STATUSES contains an invalid entry: {status!r}"
