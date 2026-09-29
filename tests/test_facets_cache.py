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
"""Tests for faceted-stats caching, cache-key normalization and invalidation."""

import uuid

import pytest
from sqlalchemy import event

from app.core.data_manager import (
    FACETS_CACHE_PREFIX,
    FACETS_CACHE_TTL_SECONDS,
    DataManager,
    invalidate_facets_cache,
    normalize_facet_cache_key,
)
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def facet_setup(app):
    """Seed one user with two items so facet counts are non-trivial."""
    with app.app_context():
        from app.api.auth import generate_internal_jwt
        from app.core.cache import cache
        from app.db.models import Permission, Role

        cache.clear()

        user = User(email="facet_cache@example.com", display_name="Facet Tester")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.flush()

        # Grant the item permissions the mutation tests below exercise.
        role = Role(name="facet_tester")
        for perm_name in ("write:item", "delete:item", "update:item"):
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
                db.session.flush()
            role.permissions.append(perm)
        user.roles.append(role)
        db.session.add(role)
        db.session.flush()

        work = Work(title="Facet Work", meta={"genres": ["Fantasy"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        m1 = Manifestation(expression_id=expr.id, isbn13="9780000000011", meta={"format": "book", "publisher": "Tor"})
        m2 = Manifestation(expression_id=expr.id, isbn13="9780000000028", meta={"format": "dvd", "publisher": "Tor"})
        db.session.add_all([m1, m2])
        db.session.flush()

        db.session.add(Item(manifestation_id=m1.id, owner_id=user.id, status="reading", collection_status="available"))
        db.session.add(Item(manifestation_id=m2.id, owner_id=user.id, status="read", collection_status="available"))
        db.session.commit()

        return {"user_id": user.id, "headers": {"Authorization": f"Bearer {generate_internal_jwt(user)}"}}


# ── Cache key normalization ────────────────────────────────────────────


def test_key_is_stable_across_calls():
    params = {"view": "items", "genres": ["Fantasy"]}
    assert normalize_facet_cache_key(params, uuid.uuid4()) is not None


def test_key_is_order_independent_for_list_params():
    """`?genres=A,B` and `?genres=B,A` must not fragment the cache."""
    a = normalize_facet_cache_key({"genres": ["Fantasy", "SciFi"]}, None)
    b = normalize_facet_cache_key({"genres": ["SciFi", "Fantasy"]}, None)
    assert a == b


def test_key_is_stripped_and_case_normalized():
    a = normalize_facet_cache_key({"genres": [" Fantasy ", "scifi"]}, None)
    b = normalize_facet_cache_key({"genres": ["Fantasy", "SciFi"]}, None)
    assert a == b


def test_key_varies_with_user():
    """User-scoped counts must never share a cache entry across users."""
    a = normalize_facet_cache_key({"view": "items"}, uuid.uuid4())
    b = normalize_facet_cache_key({"view": "items"}, uuid.uuid4())
    assert a != b


def test_key_varies_with_filters():
    a = normalize_facet_cache_key({"genres": ["Fantasy"]}, None)
    b = normalize_facet_cache_key({"genres": ["SciFi"]}, None)
    assert a != b


def test_key_uses_expected_prefix():
    key = normalize_facet_cache_key({"view": "items"}, None)
    assert key.startswith(f"{FACETS_CACHE_PREFIX}:global:")


def test_key_tolerates_none_values():
    assert normalize_facet_cache_key({"genres": None, "tags": None}, None)


# ── Caching behaviour ──────────────────────────────────────────────────


def test_repeated_request_is_served_from_cache(client, facet_setup, app):
    """A second identical facet request must not re-run the heavy queries."""
    from app.core.cache import cache

    with app.app_context():
        user_id = facet_setup["user_id"]

        params = {"owner_id": user_id, "view": "items"}
        first = DataManager.get_faceted_stats(**params)
        key = normalize_facet_cache_key(
            {
                "borrowed_only": False,
                "category": None,
                "collections": None,
                "fmt": None,
                "genres": None,
                "lod_authority": None,
                "lod_status": None,
                "missing_cover": False,
                "missing_id": False,
                "ownership": None,
                "publishers": None,
                "statuses": None,
                "tags": None,
                "view": "items",
            },
            user_id,
        )
        assert cache.get(key) is not None

        statements = []

        def _record(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", _record)
        try:
            second = DataManager.get_faceted_stats(**params)
        finally:
            event.remove(db.engine, "before_cursor_execute", _record)

    assert second == first
    # All facets came from cache: no SELECT was issued.
    assert statements == [], statements


def test_cache_survives_equivalent_filter_ordering(client, facet_setup, app):
    with app.app_context():
        a = DataManager.get_faceted_stats(owner_id=facet_setup["user_id"], genres=["Fantasy", "SciFi"], view="items")
        b = DataManager.get_faceted_stats(owner_id=facet_setup["user_id"], genres=["SciFi", "Fantasy"], view="items")
    assert a == b


def test_ttl_is_bounded(client, facet_setup, app):
    """The cache must not serve stale counts indefinitely."""
    assert 0 < FACETS_CACHE_TTL_SECONDS <= 600


# ── Invalidation ───────────────────────────────────────────────────────


def test_invalidate_clears_user_entries(client, facet_setup, app):
    from app.core.cache import cache

    with app.app_context():
        user_id = facet_setup["user_id"]
        DataManager.get_faceted_stats(owner_id=user_id, view="items")
        key = normalize_facet_cache_key(
            {
                "borrowed_only": False,
                "category": None,
                "collections": None,
                "fmt": None,
                "genres": None,
                "lod_authority": None,
                "lod_status": None,
                "missing_cover": False,
                "missing_id": False,
                "ownership": None,
                "publishers": None,
                "statuses": None,
                "tags": None,
                "view": "items",
            },
            user_id,
        )
        assert cache.get(key) is not None
        invalidate_facets_cache(user_id)
        assert cache.get(key) is None


def test_invalidate_spares_other_users(client, facet_setup, app):
    """Invalidating one user must not wipe a different user's counts."""
    from app.core.cache import cache

    with app.app_context():
        user_a = facet_setup["user_id"]
        user_b = uuid.uuid4()

        DataManager.get_faceted_stats(owner_id=user_a, view="items")
        DataManager.get_faceted_stats(owner_id=user_b, view="items")

        key_b = normalize_facet_cache_key(
            {
                "borrowed_only": False,
                "category": None,
                "collections": None,
                "fmt": None,
                "genres": None,
                "lod_authority": None,
                "lod_status": None,
                "missing_cover": False,
                "missing_id": False,
                "ownership": None,
                "publishers": None,
                "statuses": None,
                "tags": None,
                "view": "items",
            },
            user_b,
        )
        invalidate_facets_cache(user_a)
        assert cache.get(key_b) is not None


def test_invalidate_with_no_user_clears_global(client, app):
    from app.core.cache import cache

    with app.app_context():
        DataManager.get_faceted_stats(owner_id=None, view="items")
        key = normalize_facet_cache_key(
            {
                "borrowed_only": False,
                "category": None,
                "collections": None,
                "fmt": None,
                "genres": None,
                "lod_authority": None,
                "lod_status": None,
                "missing_cover": False,
                "missing_id": False,
                "ownership": None,
                "publishers": None,
                "statuses": None,
                "tags": None,
                "view": "items",
            },
            None,
        )
        invalidate_facets_cache()
        assert cache.get(key) is None


# ── End-to-end: mutated libraries must serve fresh counts ──────────────


def test_facet_counts_refresh_after_item_creation(client, app, facet_setup):
    """Adding an item must change the next facet response."""
    with app.app_context():
        user_id = facet_setup["user_id"]
        headers = facet_setup["headers"]

        before = client.get("/api/stats/facets?scope=user&view=items", headers=headers).get_json()["data"]
        assert before["status_counts"]["available"] == 2

        work = Work(title="Added Later", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780000000099", meta={"format": "book"})
        db.session.add(manif)
        db.session.flush()
        db.session.add(Item(manifestation_id=manif.id, owner_id=user_id, status="reading", collection_status="available"))
        db.session.commit()
        invalidate_facets_cache(user_id)

        after = client.get("/api/stats/facets?scope=user&view=items", headers=headers).get_json()["data"]

    assert after["status_counts"]["available"] == 3


def test_facet_counts_refresh_after_item_deletion(client, app, facet_setup):
    with app.app_context():
        from app.core.cache import cache

        cache.clear()
        user_id = facet_setup["user_id"]
        headers = facet_setup["headers"]

        item = db.session.query(Item).filter(Item.owner_id == user_id).first()
        item_id = item.id

        before = client.get("/api/stats/facets?scope=user&view=items", headers=headers).get_json()["data"]
        assert before["status_counts"]["available"] == 2

        resp = client.delete(f"/api/items/{item_id}", headers=headers)
        assert resp.status_code == 200

        after = client.get("/api/stats/facets?scope=user&view=items", headers=headers).get_json()["data"]

    assert after["status_counts"]["available"] == 1
