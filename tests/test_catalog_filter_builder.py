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
"""Unit tests for the shared CatalogFilterBuilder query abstraction.

These tests compile the generated SQL (no database round-trip required) to
assert that filters produce the expected clauses and, critically, that joins
are de-duplicated when several item-scoped facets are combined.
"""

import re
import uuid

import pytest

from app.api.filters import CatalogFilterBuilder
from app.db.models import Expression, Item, Manifestation, Work, db


def _sql(query, literal_binds: bool = True) -> str:
    """Render a Query to a SQL string for assertions.

    Whitespace is collapsed so the same assertions hold on both the SQLite
    and PostgreSQL dialects, which differ in join/column spacing.  Pass
    ``literal_binds=False`` for statements containing JSONB containment
    parameters, which PostgreSQL cannot render as literals.
    """
    compiled = str(query.statement.compile(db.engine, compile_kwargs={"literal_binds": literal_binds})).lower()
    return " ".join(compiled.split())


def _count_join(sql: str, table: str) -> int:
    """Count JOINs against ``table`` regardless of join style or schema prefix.

    Both ``JOIN items`` and ``LEFT OUTER JOIN inventory.items`` must count,
    while the column references (``items.status``) must not.
    """
    return len(re.findall(rf"join (?:[a-z_]+\.)?{table}\b", sql))


@pytest.fixture
def user_id():
    return uuid.uuid4()


# ── Join de-duplication ────────────────────────────────────────────────


def test_tags_and_collections_share_single_item_join(user_id):
    """tags + collections + statuses must not emit a duplicate JOIN items."""
    query = Manifestation.query.join(Expression).join(Work)
    built = CatalogFilterBuilder(query, user_id=user_id).apply(
        tags=["fiction"],
        collections=["Shelf"],
        statuses=["available"],
    )
    assert _count_join(_sql(built), "items") == 1, _sql(built)


def test_statuses_alone_joins_items_exactly_once(user_id):
    query = Manifestation.query.join(Expression).join(Work)
    built = CatalogFilterBuilder(query, user_id=user_id).apply(statuses=["available"])
    assert _count_join(_sql(built), "items") == 1, _sql(built)


def test_statuses_after_tags_does_not_duplicate_join(user_id):
    query = Manifestation.query.join(Expression).join(Work)
    built = CatalogFilterBuilder(query, user_id=user_id).apply(
        tags=["fiction"],
        statuses=["lent"],
    )
    assert _count_join(_sql(built), "items") == 1, _sql(built)


def test_item_root_does_not_join_items():
    """Item-rooted queries must not re-join the Item table."""
    built = CatalogFilterBuilder(
        Item.query,
        root=CatalogFilterBuilder.ROOT_ITEM,
        user_id=uuid.uuid4(),
        ensure_frbr_join=True,
    ).apply(tags=["fiction"], statuses=["available"])
    sql = _sql(built)
    assert _count_join(sql, "items") == 0, sql
    assert _count_join(sql, "manifestations") == 1, sql


def test_item_root_joins_frbr_chain_once():
    built = CatalogFilterBuilder(
        Item.query,
        root=CatalogFilterBuilder.ROOT_ITEM,
        user_id=uuid.uuid4(),
        ensure_frbr_join=True,
    ).apply(
        category=["text"],
        genres=["Fantasy"],
        tags=["a"],
        collections=["b"],
    )
    sql = _sql(built, literal_binds=False)
    assert _count_join(sql, "expressions") == 1, sql
    assert _count_join(sql, "works") == 1, sql
    assert _count_join(sql, "manifestations") == 1, sql


# ── Filter semantics ───────────────────────────────────────────────────


def test_format_filter_targets_json_format_key():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query).apply(fmt=["paperback"]))
    assert "format" in sql
    assert "paperback" in sql


def test_category_filter_targets_expression_content_type():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query).apply(category=["music"]))
    assert "content_type" in sql
    assert "music" in sql


def test_missing_cover_requires_both_cover_fields_empty():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query).apply(missing_cover=True))
    assert "cover_url" in sql
    assert "is null" in sql


def test_missing_id_checks_all_identifier_columns():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query).apply(missing_id=True))
    for column in ("isbn13", "upc", "ean", "barcode", "catalog_number"):
        assert column in sql, f"{column} missing from: {sql}"


def test_genre_filter_applied_to_work_meta():
    """Genre filtering targets Work.meta on both dialects.

    SQLite uses an ILIKE on extracted JSON keys; PostgreSQL uses jsonb
    containment. Only the target column is dialect-stable, so that is what
    is asserted.
    """
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query).apply(genres=["Fantasy"]), literal_binds=False)
    # Works is joined either directly or via the catalog schema prefix.
    assert re.search(r"(?:[a-z_]+\.)?works\.meta", sql), sql
    # The genre values themselves are bound parameters, not literals, on both
    # dialects, so the target column is the only stable assertion.


def test_publisher_filter_covers_publishers_and_music_label():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query).apply(publishers=["Tor"]))
    assert "publisher" in sql
    assert "label" in sql


def test_ownership_filter_is_uncorrelated_exists(user_id):
    """ownership must use EXISTS, never a JOIN that duplicates rows."""
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query, user_id=user_id).apply(ownership=["owned"]))
    assert "exists" in sql
    assert _count_join(sql, "items") == 0, sql


def test_ownership_not_owned_negates_exists(user_id):
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query, user_id=user_id).apply(ownership=["not_owned"]))
    assert "not (exists" in sql or "not exists" in sql, sql


def test_ownership_ignored_without_user():
    """Anonymous requests must not be silently scoped to a (None) owner."""
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query, user_id=None).apply(ownership=["owned"]))
    assert "exists" not in sql, sql


def test_statuses_ignored_without_user():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query, user_id=None).apply(statuses=["available"]))
    assert _count_join(sql, "items") == 0, sql


def test_statuses_progress_only_style():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query, user_id=uuid.uuid4(), statuses_style="progress_only").apply(statuses=["reading"]))
    assert re.search(r"(?:[a-z_]+\.)?items\.status", sql), sql
    assert "collection_status" not in sql


def test_statuses_auto_style_uses_collection_status():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query, user_id=uuid.uuid4()).apply(statuses=["available"]))
    assert "collection_status" in sql


def test_collections_scoped_to_owner(user_id):
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query, user_id=user_id).apply(collections=["Shelf"]))
    assert "owner_id" in sql
    assert re.search(r"(?:[a-z_]+\.)?user_collections", sql), sql


def test_lod_authority_filter_lowercases_input():
    query = Manifestation.query.join(Expression).join(Work)
    sql = _sql(CatalogFilterBuilder(query).apply(lod_authority="DBPedia"))
    assert "semantic_links" in sql
    assert "lower" in sql


def test_lod_status_linked_and_unlinked():
    query = Manifestation.query.join(Expression).join(Work)
    linked = _sql(CatalogFilterBuilder(query).apply(lod_status="linked"))
    unlinked = _sql(CatalogFilterBuilder(query).apply(lod_status="unlinked"))
    assert "not in" not in linked, linked
    assert " not in " in unlinked, unlinked


def test_no_filters_returns_query_unchanged():
    query = Manifestation.query.join(Expression).join(Work)
    built = CatalogFilterBuilder(query).apply()
    assert built is not None
    sql = _sql(built)
    assert "where" not in sql, sql


def test_build_alias_matches_apply():
    query = Manifestation.query.join(Expression).join(Work)
    apply_sql = _sql(CatalogFilterBuilder(query).apply(fmt=["book"]))
    build_sql = _sql(CatalogFilterBuilder(query).build(fmt=["book"]))
    assert apply_sql == build_sql
