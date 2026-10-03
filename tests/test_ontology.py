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


def _balanced_array_after(source: str, name: str) -> str | None:
    """Return the contents of a bracketed literal, honouring nesting and quotes.

    Replaces a `\\[([^\\]]+)\\]` regex, which is blind in two ways that matter
    here:

    - a nested array element truncated the match at the first `]`, silently
      dropping every later value;
    - an escaped quote inside a value (`"a\\"b"`) desynchronised the quote
      pattern and produced junk such as `{", ", "a\\"}`.

    Neither can occur in `taxonomy.ts` today, which is exactly why the weakness
    was invisible: the guard would have kept passing while being unable to
    detect the drift it exists to detect.

    @param source: The TypeScript source.
    @param name: The identifier whose bracket follows.
    @returns: The literal's contents, or None when the identifier is absent.
    """
    # Built outside the f-string: a bracketed character class inside an f-string
    # expression is a syntax error before Python 3.12's nesting rules, and this
    # file must stay readable rather than clever.
    gap = r"[^\[{]*\["
    anchor = re.search(r"\b" + re.escape(name) + r"\b" + gap, source)
    if not anchor:
        return None

    # `anchor.end()` is *past* the opening bracket, so the scan starts at depth 0
    # and the matching close arrives at depth -1. Starting at 1 and testing for 0
    # is the easier pair to reason about; getting this wrong makes the scanner
    # run on into the next declaration instead of stopping.
    start = anchor.end()
    depth = 1
    in_string: str | None = None
    escaped = False
    index = start

    while index < len(source):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
        elif char in "\"'`":
            in_string = char
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
            if depth == 0:
                return source[start:index]
        index += 1
    return None


def _parse_ts_const_array(ts_source: str, const_name: str) -> frozenset[str]:
    """Extract string literals from a TypeScript 'as const' array."""
    body = _balanced_array_after(ts_source, const_name)
    if body is None:
        raise ValueError(f"Could not locate '{const_name}' array in taxonomy.ts")
    return _top_level_string_literals(body)


def _unescape(value: str) -> str:
    """Resolve the escapes a TypeScript string literal may contain.

    The scanner has to know where a literal ends, so it already tracks escapes;
    reusing that knowledge here keeps the parsed value faithful instead of
    leaving a backslash in place.

    @param value: The literal's raw contents.
    @returns: The value with backslash escapes resolved.
    """
    return value.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")


def _top_level_string_literals(body: str) -> frozenset[str]:
    r"""Collect the string literals that are direct elements of an array.

    Only strings at nesting depth zero count. `MEDIA_FORMATS` holds bare strings,
    but other arrays in the same file hold objects carrying `label:` values, and
    those labels are not array elements. The previous `[^\]]+` regex
    excluded them by accident -- it stopped at the first `]`, which happened to
    fall before the nested object closed -- so a correctly balanced parse with
    no depth filter would start comparing labels against the taxonomy and fail.

    @param body: The array's contents, without the enclosing brackets.
    @returns: The direct string-element values.
    """
    values: set[str] = set()
    depth = 0
    in_string: str | None = None
    escaped = False
    start = 0
    index = 0

    while index < len(body):
        char = body[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                # A completed literal counts only when it sits at depth zero.
                if depth == 0:
                    values.add(_unescape(body[start:index]))
                in_string = None
        elif char in "\"'`":
            in_string = char
            start = index + 1
        elif char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
        index += 1
    return frozenset(values)


def _parse_union_type_from_ts(ts_source: str, type_name: str) -> frozenset[str]:
    """Extract union members from a TypeScript type alias."""
    match = re.search(rf"export\s+type\s+{re.escape(type_name)}\s*=\s*([^;]+);", ts_source, re.DOTALL)
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
    with open(TAXONOMY_YAML, encoding="utf-8") as f:
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


def test_model_check_constraints_defined() -> None:
    """Verify that domain models define DB check constraints on status and visibility."""
    from sqlalchemy import CheckConstraint

    from app.db.auth import User
    from app.db.core import Item, UserWorkIntent
    from app.db.lending import LoanRequest

    item_ck_names = {c.name for c in Item.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_items_status" in item_ck_names
    assert "ck_items_collection_status" in item_ck_names

    intent_ck_names = {c.name for c in UserWorkIntent.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_user_work_intents_status" in intent_ck_names

    user_ck_names = {c.name for c in User.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "check_user_visibility" in user_ck_names

    loan_ck_names = {c.name for c in LoanRequest.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_loan_requests_status" in loan_ck_names


def test_optional_foreign_keys_ondelete_set_null() -> None:
    """Verify that optional foreign keys declare ondelete='SET NULL'."""
    from app.db.core import Item, ItemCustodyEvent, ItemTag, UserCollection
    from app.db.roadmap import RoadmapItem
    from app.db.settings import ScanTelemetry

    # Item.lent_to_user_id
    lent_fk = next(fk for fk in Item.__table__.foreign_keys if fk.parent.name == "lent_to_user_id")
    assert lent_fk.ondelete == "SET NULL"

    # UserCollection.parent_id
    parent_fk = next(fk for fk in UserCollection.__table__.foreign_keys if fk.parent.name == "parent_id")
    assert parent_fk.ondelete == "SET NULL"

    # ItemTag.added_by_id
    tag_fk = next(fk for fk in ItemTag.__table__.foreign_keys if fk.parent.name == "added_by_id")
    assert tag_fk.ondelete == "SET NULL"

    # ItemCustodyEvent.actor_id
    custody_fk = next(fk for fk in ItemCustodyEvent.__table__.foreign_keys if fk.parent.name == "actor_id")
    assert custody_fk.ondelete == "SET NULL"

    # EntityAuditLog.actor_id
    from app.db.core import EntityAuditLog

    audit_fk = next(fk for fk in EntityAuditLog.__table__.foreign_keys if fk.parent.name == "actor_id")
    assert audit_fk.ondelete == "SET NULL"

    # ScanTelemetry.manifestation_id
    scan_fk = next(fk for fk in ScanTelemetry.__table__.foreign_keys if fk.parent.name == "manifestation_id")
    assert scan_fk.ondelete == "SET NULL"

    # RoadmapItem.work_id & manifestation_id
    roadmap_work_fk = next(fk for fk in RoadmapItem.__table__.foreign_keys if fk.parent.name == "work_id")
    assert roadmap_work_fk.ondelete == "SET NULL"
    roadmap_manif_fk = next(fk for fk in RoadmapItem.__table__.foreign_keys if fk.parent.name == "manifestation_id")
    assert roadmap_manif_fk.ondelete == "SET NULL"


# ---------------------------------------------------------------------------
# FRBR Linked Open Data Canonical IRI Tests
# ---------------------------------------------------------------------------


def test_frbr_entity_iri_default_base() -> None:
    """Verify default canonical IRI formatting across all four FRBR levels."""
    import os
    from unittest.mock import patch

    from app.db.core import Expression, Item, Manifestation, Work

    with patch.dict(os.environ, {}, clear=True):
        work = Work(id=42, title="Test Work")
        expression = Expression(id=10, work_id=42)
        manifestation = Manifestation(id=20, expression_id=10)
        item = Item(id=30, manifestation_id=20)

        assert work.iri == "https://iqoqo.cc/works/42"
        assert expression.iri == "https://iqoqo.cc/expressions/10"
        assert manifestation.iri == "https://iqoqo.cc/manifestations/20"
        assert item.iri == "https://iqoqo.cc/items/30"


def test_frbr_entity_iri_custom_base_url() -> None:
    """Verify canonical IRI formatting respects BASE_URL and strips trailing slashes."""
    import os
    from unittest.mock import patch

    from app.db.core import Expression, Item, Manifestation, Work

    custom_url = "https://custom.library.org/"
    with patch.dict(os.environ, {"BASE_URL": custom_url}):
        work = Work(id=1, title="Test Work")
        expression = Expression(id=2, work_id=1)
        manifestation = Manifestation(id=3, expression_id=2)
        item = Item(id=4, manifestation_id=3)

        assert work.iri == "https://custom.library.org/works/1"
        assert expression.iri == "https://custom.library.org/expressions/2"
        assert manifestation.iri == "https://custom.library.org/manifestations/3"
        assert item.iri == "https://custom.library.org/items/4"


def test_frbr_entity_iri_frontend_url_fallback() -> None:
    """Verify canonical IRI falls back to NEXT_PUBLIC_FRONTEND_URL when BASE_URL is unset."""
    import os
    from unittest.mock import patch

    from app.db.core import Work

    frontend_url = "https://frontend.example.com"
    with patch.dict(os.environ, {"NEXT_PUBLIC_FRONTEND_URL": frontend_url}, clear=True):
        work = Work(id=77, title="Sample")
        assert work.iri == "https://frontend.example.com/works/77"


# ---------------------------------------------------------------------------
# Parser robustness (C18 4.5)
# ---------------------------------------------------------------------------


def test_array_parser_handles_nested_structures() -> None:
    """A nested array element must not truncate the match.

    The previous `\\[([^\\]]+)\\]` regex stopped at the first `]`, so every value
    after a nested element was silently dropped -- and the guard would have
    kept passing while unable to detect the drift it exists to detect.

    @returns: Nothing; a truncated parse fails the test.
    """
    source = 'export const X = [["a", "b"], "c", "d"] as const;'
    assert _parse_ts_const_array(source, "X") == frozenset({"c", "d"})


def test_array_parser_handles_escaped_quotes() -> None:
    """A value containing a quote must not desynchronise the string scanner.

    @returns: Nothing; a garbled parse fails the test.
    """
    source = 'export const X = ["a\\"b", "c"] as const;'
    assert _parse_ts_const_array(source, "X") == frozenset({'a"b', "c"})


def test_array_parser_excludes_nested_object_labels() -> None:
    """Labels inside nested objects are not array elements.

    The old regex excluded them by accident -- it stopped before the nested
    object closed. A correctly balanced parse must exclude them deliberately,
    or `MEDIA_FORMATS` picks up "Comic Book (Single Issue)" and the comparison
    against the taxonomy fails on a value that is not a format.

    @returns: Nothing; a leaked label fails the test.
    """
    source = """
export const X = [
  { id: "book", label: "Book" },
  { id: "vinyl", label: "Vinyl Record" },
] as const;
"""
    assert _parse_ts_const_array(source, "X") == frozenset()


def test_array_parser_stops_at_the_matching_bracket() -> None:
    """The scan must not run on into the following declaration.

    An off-by-one in the depth bookkeeping produced exactly this: `MEDIA_FORMATS`
    absorbed every value in `MEDIA_CATEGORIES` and the sync test failed with 38
    values instead of 33.

    @returns: Nothing; a run-on parse fails the test.
    """
    source = """
export const A = ["one", "two"] as const;
export const B = ["three", "four"] as const;
"""
    assert _parse_ts_const_array(source, "A") == frozenset({"one", "two"})
    assert _parse_ts_const_array(source, "B") == frozenset({"three", "four"})


def test_array_parser_raises_when_the_identifier_is_absent() -> None:
    """A missing identifier must raise rather than silently return empty.

    An empty frozenset would compare unequal to the taxonomy and report a
    confusing mismatch instead of naming the missing constant.

    @returns: Nothing; a silent empty result fails the test.
    """
    with pytest.raises(ValueError, match="Could not locate"):
        _parse_ts_const_array('export const OTHER = ["x"] as const;', "MISSING")
