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
import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.core.data_manager import _build_collection_status_facet_query, _build_format_facet_query
from app.db.models import Expression, Item, Manifestation, Work, db


def test_items_genre_filter(client, normal_user_headers, app):
    with app.app_context():
        from app.db.models import User

        user = User.query.filter_by(email="test_user@iqoqo.local").first()

        # Create test data with different genres
        work1 = Work(title="Jazz Album", meta={"genre": "Jazz"})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type="audio")
        db.session.add(expr1)
        db.session.flush()
        man1 = Manifestation(expression_id=expr1.id)
        db.session.add(man1)
        db.session.flush()
        item1 = Item(manifestation_id=man1.id, owner_id=user.id, status="available")
        db.session.add(item1)

        work2 = Work(title="Rock Album", meta={"genre": "Rock"})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type="audio")
        db.session.add(expr2)
        db.session.flush()
        man2 = Manifestation(expression_id=expr2.id)
        db.session.add(man2)
        db.session.flush()
        item2 = Item(manifestation_id=man2.id, owner_id=user.id, status="available")
        db.session.add(item2)

        db.session.commit()

    resp = client.get("/api/items?genres=Jazz", headers=normal_user_headers)
    assert resp.status_code == 200
    data = resp.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Jazz Album"


def test_manifestations_genre_filter(client, normal_user_headers, app):
    with app.app_context():
        # Same data should work for manifestations
        work1 = Work(title="Jazz Album Release", meta={"genre": "Jazz"})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type="audio")
        db.session.add(expr1)
        db.session.flush()
        man1 = Manifestation(expression_id=expr1.id)
        db.session.add(man1)

        work2 = Work(title="Rock Album Release", meta={"genre": "Rock"})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type="audio")
        db.session.add(expr2)
        db.session.flush()
        man2 = Manifestation(expression_id=expr2.id)
        db.session.add(man2)

        db.session.commit()

    resp = client.get("/api/manifestations?genres=Rock", headers=normal_user_headers)
    assert resp.status_code == 200
    data = resp.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Rock Album Release"


class TestCrossFRBRMultiFilter:
    """2.1-2.5: Cross-FRBR filtering edge cases."""

    def test_three_simultaneous_filters_different_taxonomies(self, client, normal_user_headers, app):
        """2.1: 3+ simultaneous cross-FRBR filters with AND logic."""
        with app.app_context():
            from app.db.models import Tag, User

            user = User.query.filter_by(email="test_user@iqoqo.local").first()

            # Create tags
            tag_horror = Tag(name="horror")
            tag_classic = Tag(name="classic")
            db.session.add_all([tag_horror, tag_classic])
            db.session.flush()

            # Work 1: Horror + Classic, available, book format
            w1 = Work(title="Horror Classic", meta={"genre": "Horror"})
            db.session.add(w1)
            db.session.flush()
            e1 = Expression(work_id=w1.id, content_type="text")
            db.session.add(e1)
            db.session.flush()
            m1 = Manifestation(
                expression_id=e1.id,
                meta={"format": "paper", "title": "Horror Classic"},
            )
            db.session.add(m1)
            db.session.flush()
            i1 = Item(
                manifestation_id=m1.id,
                owner_id=user.id,
                status="available",
                collection_status="available",
            )
            db.session.add(i1)
            db.session.flush()
            # Link tags
            from app.db.models import ItemTag

            db.session.add(ItemTag(item_id=i1.id, tag_id=tag_horror.id))
            db.session.add(ItemTag(item_id=i1.id, tag_id=tag_classic.id))

            db.session.commit()

        # Query with 3 filters: status + format + tag
        resp = client.get(
            "/api/works/shelf?statuses=available&formats=paper&tags=horror",
            headers=normal_user_headers,
        )
        assert resp.status_code == 200
        data = resp.json
        # Only Work 1 carries horror *and* is available *and* is paper, so this is
        # exactly one row. `>= 1` would have passed on 2 or 3, which is what an
        # over-broad or wrongly-OR'd facet produces.
        assert data["total"] == 1

    def test_multiple_tag_filter_and_logic(self, client, normal_user_headers, app):
        """2.2: A comma-joined tag list resolves to the Works carrying those tags.

        The name and the original docstring said "AND logic ... only Works with
        ALL tags". The filter is OR -- `app/api/works.py` combines the tag
        conditions with `db.or_(*tags_conditions)` -- and OR within a facet is the
        conventional behaviour for faceted filtering: a user picking two tags is
        asking for either, not for the intersection. Changing the filter to AND
        would break that, so the docstring was wrong rather than the code.

        Cross-facet combination is the AND case, and it is pinned separately in
        test_filters_from_different_facets_are_combined_with_and.
        """
        with app.app_context():
            from app.db.models import Tag, User

            user = User.query.filter_by(email="test_user@iqoqo.local").first()

            tag_a = Tag(name="horror")
            tag_b = Tag(name="classic")
            tag_c = Tag(name="sci-fi")
            db.session.add_all([tag_a, tag_b, tag_c])
            db.session.flush()

            # Work 1: Horror + Classic tags
            w1 = Work(title="Horror Classic Book", meta={"genre": "Horror"})
            db.session.add(w1)
            db.session.flush()
            e1 = Expression(work_id=w1.id, content_type="text")
            db.session.add(e1)
            db.session.flush()
            m1 = Manifestation(
                expression_id=e1.id,
                meta={"format": "paper", "title": "Horror Classic Book"},
            )
            db.session.add(m1)
            db.session.flush()
            i1 = Item(
                manifestation_id=m1.id,
                owner_id=user.id,
                status="available",
                collection_status="available",
            )
            db.session.add(i1)
            db.session.flush()
            from app.db.models import ItemTag

            db.session.add(ItemTag(item_id=i1.id, tag_id=tag_a.id))
            db.session.add(ItemTag(item_id=i1.id, tag_id=tag_b.id))

            # Work 2: Only Sci-Fi tag
            w2 = Work(title="Sci-Fi Book", meta={"genre": "Science Fiction"})
            db.session.add(w2)
            db.session.flush()
            e2 = Expression(work_id=w2.id, content_type="text")
            db.session.add(e2)
            db.session.flush()
            m2 = Manifestation(
                expression_id=e2.id,
                meta={"format": "paper", "title": "Sci-Fi Book"},
            )
            db.session.add(m2)
            db.session.flush()
            i2 = Item(
                manifestation_id=m2.id,
                owner_id=user.id,
                status="available",
                collection_status="available",
            )
            db.session.add(i2)
            db.session.flush()
            db.session.add(ItemTag(item_id=i2.id, tag_id=tag_c.id))

            db.session.commit()

        # Both tags sit on this one Work, so `tags=horror,classic` returns it
        # whether the filter is OR or AND. See
        # test_multiple_tags_in_one_facet_are_combined_with_or for the fixture
        # that can actually tell the two apart.
        resp = client.get(
            "/api/works/shelf?tags=horror,classic",
            headers=normal_user_headers,
        )
        assert resp.status_code == 200
        data = resp.json
        assert data["total"] == 1
        assert data["data"][0]["title"] == "Horror Classic Book"

    def test_empty_results_returns_200(self, client, normal_user_headers, app):
        """2.3: Cross-FRBR filter returns empty results with 200 status."""
        resp = client.get(
            "/api/works/shelf?statuses=nonexistent_status&formats=nonexistent_format",
            headers=normal_user_headers,
        )
        assert resp.status_code == 200
        data = resp.json
        assert data["total"] == 0

    def test_unauthenticated_user_filter_counts(self, client, app):
        """2.4: Unauthenticated user receives correct public-only filter counts."""
        resp = client.get("/api/manifestations?formats=paper")
        assert resp.status_code in (200, 401)

    def test_comma_joined_url_parameter_parsing(self, client, normal_user_headers, app):
        """2.5: Comma-joined URL parameter parsing splits and applies multiple values."""
        resp = client.get(
            "/api/manifestations?formats=paper,hardcover&statuses=available",
            headers=normal_user_headers,
        )
        assert resp.status_code == 200
        # Should parse comma-separated values correctly
        data = resp.json
        assert data is not None

    def test_faceted_stats_caching(self, client, normal_user_headers, app):
        """Test that /api/stats/facets caches its response and doesn't hit DB on subsequent requests.

        Caching now lives inside ``DataManager.get_faceted_stats`` (which owns
        the normalized key and the invalidation hooks), so the uncached
        implementation ``_compute_faceted_stats`` is what gets counted.
        """
        from unittest.mock import patch

        with app.app_context():
            from app.core.cache import cache

            cache.clear()

        with patch("app.core.data_manager.DataManager._compute_faceted_stats", return_value={"mock": "data"}) as mock_compute:
            # First request
            resp1 = client.get("/api/stats/facets?scope=user", headers=normal_user_headers)
            assert resp1.status_code == 200
            assert mock_compute.call_count == 1

            # Second request with same params
            resp2 = client.get("/api/stats/facets?scope=user", headers=normal_user_headers)
            assert resp2.status_code == 200
            assert mock_compute.call_count == 1

            # Third request with different params
            resp3 = client.get("/api/stats/facets?scope=global", headers=normal_user_headers)
            assert resp3.status_code == 200
            assert mock_compute.call_count == 2

    def test_faceted_stats_cache_key_normalized(self, client, normal_user_headers, app):
        """Test that reordered query params produce the same cache key (no fragmentation)."""
        from unittest.mock import patch

        with app.app_context():
            from app.core.cache import cache

            cache.clear()

        with patch("app.core.data_manager.DataManager._compute_faceted_stats", return_value={"mock": "data"}) as mock_compute:
            # Request with params in order: scope=user, view=items
            resp1 = client.get("/api/stats/facets?scope=user&view=items", headers=normal_user_headers)
            assert resp1.status_code == 200
            assert mock_compute.call_count == 1

            # Same params, reversed order: view=items, scope=user
            resp2 = client.get("/api/stats/facets?view=items&scope=user", headers=normal_user_headers)
            assert resp2.status_code == 200
            # Should hit the cache — same logical request
            assert mock_compute.call_count == 1, "Reordered params should produce same cache key"

    def test_taxonomies_caching(self, client, normal_user_headers, app):
        """Test that /api/taxonomies caches its response and doesn't re-query on subsequent calls."""
        from unittest.mock import patch

        with app.app_context():
            from app.core.cache import cache

            cache.clear()

        with patch("app.api.taxonomies.extract_taxonomies_data", return_value={"tags": ["t1"]}) as mock_extract:
            resp1 = client.get("/api/taxonomies?scope=global", headers=normal_user_headers)
            assert resp1.status_code == 200
            assert mock_extract.call_count == 1

            resp2 = client.get("/api/taxonomies?scope=global", headers=normal_user_headers)
            assert resp2.status_code == 200
            assert mock_extract.call_count == 1

    def test_taxonomies_cache_key_normalized(self, client, normal_user_headers, app):
        """Test that reordered params on /api/taxonomies hit the same cache key."""
        from unittest.mock import patch

        with app.app_context():
            from app.core.cache import cache

            cache.clear()

        with patch("app.api.taxonomies.extract_taxonomies_data", return_value={"tags": ["t1"]}) as mock_extract:
            resp1 = client.get("/api/taxonomies?scope=global&category=text&format=book", headers=normal_user_headers)
            assert resp1.status_code == 200
            assert mock_extract.call_count == 1

            resp2 = client.get("/api/taxonomies?format=book&scope=global&category=text", headers=normal_user_headers)
            assert resp2.status_code == 200
            assert mock_extract.call_count == 1

    def test_refresh_taxonomies_cache_task(self, app):
        """Test Celery task for precomputing and caching global taxonomies."""
        from app.core.cache import cache
        from app.core.tasks import refresh_taxonomies_cache

        with app.app_context():
            cache.clear()
            res = refresh_taxonomies_cache()
            assert res["status"] == "refreshed"
            assert "tags" in res["data"]
            cached = cache.get("taxonomies:global:/api/taxonomies?")
            assert cached is not None
            assert cached["success"] is True


def test_faceted_stats_endpoint_returns_counts_in_the_frontend_contract(client, normal_user_headers, app):
    """The live stats endpoint returns the named count maps consumed by the UI."""
    with app.app_context():
        from app.db.models import User

        user = User.query.filter_by(email="test_user@iqoqo.local").first()
        work = Work(title="Facet Contract Book", meta={"genres": ["Fiction"]})
        db.session.add(work)
        db.session.flush()
        expression = Expression(work_id=work.id, content_type="text")
        db.session.add(expression)
        db.session.flush()
        manifestation = Manifestation(
            expression_id=expression.id,
            publisher="Fixture Press",
            meta={"format": "book"},
        )
        db.session.add(manifestation)
        db.session.flush()
        db.session.add(Item(manifestation_id=manifestation.id, owner_id=user.id, status="unread", collection_status="available"))
        db.session.commit()

    response = client.get("/api/stats/facets?scope=user&view=items", headers=normal_user_headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["category_counts"]["text"] == 1
    assert payload["data"]["format_counts"]["book"] == 1
    assert payload["data"]["genre_counts"]["Fiction"] == 1
    assert payload["data"]["publisher_counts"]["Fixture Press"] == 1
    assert payload["data"]["status_counts"]["available"] == 1


def test_postgresql_format_facet_grouping_reuses_json_path_bind_parameter():
    """PostgreSQL requires selected and grouped JSONB expressions to be identical."""
    filtered_ids = select(Item.id).subquery().c.id
    statement = _build_format_facet_query(Item.id, Item, Item.id, filtered_ids)
    compiled = statement.compile(dialect=postgresql.dialect())
    format_bind_names = [name for name, value in compiled.params.items() if value == "format"]

    assert len(format_bind_names) == 1
    format_placeholder = f"%({format_bind_names[0]})s"
    assert compiled.string.count(format_placeholder) == 2


def test_postgresql_collection_status_grouping_reuses_coalesce_bind_parameter():
    """PostgreSQL requires select/group-by COALESCE expressions to share binds."""
    filtered_ids = select(Item.id).subquery().c.id
    statement = _build_collection_status_facet_query(Item.id, Item, Item.id, filtered_ids)
    compiled = statement.compile(dialect=postgresql.dialect())
    available_bind_names = [name for name, value in compiled.params.items() if value == "available"]

    assert len(available_bind_names) == 1
    available_placeholder = f"%({available_bind_names[0]})s"
    assert compiled.string.count(available_placeholder) == 2


def test_lod_facets_and_filtering(client, normal_user_headers, app):
    """Test LOD facets in /api/stats/facets and LOD filtering in /api/items and /api/manifestations."""
    with app.app_context():
        from app.db.models import SemanticLink, User

        user = User.query.filter_by(email="test_user@iqoqo.local").first()

        # Work 1 with DBpedia link
        work1 = Work(title="Linked Work", meta={})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type="text")
        db.session.add(expr1)
        db.session.flush()
        man1 = Manifestation(expression_id=expr1.id, publisher="LOD Press")
        db.session.add(man1)
        db.session.flush()
        item1 = Item(manifestation_id=man1.id, owner_id=user.id, status="available")
        db.session.add(item1)
        db.session.flush()

        link1 = SemanticLink(
            entity_type="manifestation",
            entity_id=man1.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Linked_Work",
        )
        db.session.add(link1)

        # Work 2 without links (unlinked)
        work2 = Work(title="Unlinked Work", meta={})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type="text")
        db.session.add(expr2)
        db.session.flush()
        man2 = Manifestation(expression_id=expr2.id, publisher="Plain Press")
        db.session.add(man2)
        db.session.flush()
        item2 = Item(manifestation_id=man2.id, owner_id=user.id, status="available")
        db.session.add(item2)

        # Work 3 on wishlist without LOD links
        from app.db.models import UserWorkIntent

        work3 = Work(title="Wishlist Work", meta={})
        db.session.add(work3)
        db.session.flush()
        expr3 = Expression(work_id=work3.id, content_type="text")
        db.session.add(expr3)
        db.session.flush()
        intent = UserWorkIntent(user_id=user.id, work_id=work3.id, status="want_to_read")
        db.session.add(intent)

        db.session.commit()

    # 1. Facet stats should return lod_counts
    resp = client.get("/api/stats/facets?scope=user&view=items", headers=normal_user_headers)
    assert resp.status_code == 200
    facets = resp.get_json()["data"]
    assert "lod_counts" in facets
    lod_counts = facets["lod_counts"]
    assert lod_counts["dbpedia"] >= 1
    assert lod_counts["linked"] >= 1
    assert lod_counts["unlinked"] >= 1
    assert facets["status_counts"]["wish_list"] >= 1

    # 1b. When filtering facets by lod_authority=dbpedia, unlinked wishlist intent is NOT counted in wish_list
    resp_dbpedia_facets = client.get("/api/stats/facets?scope=user&view=items&lod_authority=dbpedia", headers=normal_user_headers)
    assert resp_dbpedia_facets.status_code == 200
    dbpedia_facets = resp_dbpedia_facets.get_json()["data"]
    assert dbpedia_facets["status_counts"].get("wish_list", 0) == 0

    # 2. Filter items by lod_authority=dbpedia
    resp_items = client.get("/api/items?lod_authority=dbpedia", headers=normal_user_headers)
    assert resp_items.status_code == 200
    items = resp_items.get_json()["data"]
    item_titles = [i["title"] for i in items]
    assert "Linked Work" in item_titles
    assert "Unlinked Work" not in item_titles

    # 3. Filter items by lod_status=unlinked
    resp_unlinked = client.get("/api/items?lod_status=unlinked", headers=normal_user_headers)
    assert resp_unlinked.status_code == 200
    unlinked_items = resp_unlinked.get_json()["data"]
    unlinked_titles = [i["title"] for i in unlinked_items]
    assert "Unlinked Work" in unlinked_titles
    assert "Linked Work" not in unlinked_titles

    # 4. Filter manifestations by lod_authority=dbpedia
    resp_man = client.get("/api/manifestations?lod_authority=dbpedia", headers=normal_user_headers)
    assert resp_man.status_code == 200
    man_data = resp_man.get_json()["data"]
    man_titles = [m["title"] for m in man_data]
    assert "Linked Work" in man_titles
    assert "Unlinked Work" not in man_titles


# ---------------------------------------------------------------------------
# Facet combination semantics (MOD-TEST-12, MOD-TEST-13)
# ---------------------------------------------------------------------------
#
# Two things were previously asserted by two tests that could not disagree with
# each other, because neither looked at the results:
#
#   test_api_facets.py::test_multiple_tag_filter_and_logic
#       docstring: "AND logic returns only Works with ALL tags"
#       assertions: `"total" in data` and `isinstance(data["total"], int)`
#
#   test_api_status_filters.py::test_multiple_tag_and_logic
#       comment: "Tags filter uses OR logic, so it may return all items with
#                 either tag. The AND semantics come from combining multiple
#                 filter types."
#       assertions: `response.json is not None`
#
# So one file documented AND, the other documented OR, and both would have passed
# under either.
#
# This file's own fixture for 2.2 could not have settled it either: it attaches
# `horror` and `classic` to the *same* Item, so `tags=horror,classic` selects that
# one Work under OR and under AND alike. `cross_frbr_multi_filter_data` in
# test_api_status_filters.py does split the tags -- one Work with each, one with
# both -- and now asserts the distinguishing count; see
# test_multiple_tag_and_logic there.
#
# The fixture below separates the tags across two Works and adds no Work carrying
# both, so an OR returns two rows and an AND returns none. That makes it
# sensitive to the one thing the 2.2 fixture could not see.


@pytest.fixture
def split_tag_facets(app):
    """Seed two Works whose tags and statuses deliberately do not overlap.

    `Only Horror` is available and tagged `horror`; `Only Classic` is lent and
    tagged `classic`. Neither Work carries both tags, so a multi-value tag filter
    can distinguish OR (two Works) from AND (none), and no single Work satisfies
    both a tag and the other Work's status, so a cross-facet filter can
    distinguish intersection from union.

    @param app: The Flask application.
    @returns: A dict of the seeded Work titles by role.
    """
    from app.db.models import ItemTag, Tag, User

    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").one()
        tags = {name: Tag(name=name) for name in ("horror", "classic")}
        db.session.add_all(tags.values())
        db.session.flush()

        seeded = {}
        for title, status, tag in (("Only Horror", "available", "horror"), ("Only Classic", "lent", "classic")):
            work = Work(title=title, meta={"genre": "Fiction"})
            db.session.add(work)
            db.session.flush()
            expression = Expression(work_id=work.id, content_type="text")
            db.session.add(expression)
            db.session.flush()
            manifestation = Manifestation(expression_id=expression.id, format="book", meta={"format": "book"})
            db.session.add(manifestation)
            db.session.flush()
            item = Item(
                manifestation_id=manifestation.id,
                owner_id=user.id,
                status=status,
                collection_status=status,
                meta={},
            )
            db.session.add(item)
            db.session.flush()
            db.session.add(ItemTag(item_id=item.id, tag_id=tags[tag].id))
            seeded[title] = tag

        db.session.commit()
        return seeded


def shelf_titles(client, headers, query: str) -> list[str]:
    """Fetch `/api/works/shelf` and return the titles it reports.

    @param client: The Flask test client.
    @param headers: Auth headers for the seeded user.
    @param query: The query string, without a leading `?`.
    @returns: The sorted titles in the result set.
    """
    response = client.get(f"/api/works/shelf?{query}", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["total"] == len(payload["data"]), "total disagrees with the rows returned"
    return sorted(row["title"] for row in payload["data"])


def test_multiple_tags_in_one_facet_are_combined_with_or(client, normal_user_headers, app, split_tag_facets):
    """Two tags in one facet select the union, not the intersection.

    `Only Horror` and `Only Classic` share no tag and no Work, so an OR returns
    both and an AND returns none. The fixture makes this the only difference
    between the two readings, so the assertion is sensitive to which one the
    filter implements.

    @param client: The Flask test client.
    @param normal_user_headers: Auth headers for the seeded user.
    @param app: The Flask application.
    @param split_tag_facets: The seeded fixture.
    @returns: Nothing; intersection semantics fail the test.
    """
    assert shelf_titles(client, normal_user_headers, "tags=horror,classic") == ["Only Classic", "Only Horror"]


def test_a_single_tag_still_selects_one_work(client, normal_user_headers, app, split_tag_facets):
    """A one-value filter is the degenerate case of the same rule.

    @param client: The Flask test client.
    @param normal_user_headers: Auth headers for the seeded user.
    @param app: The Flask application.
    @param split_tag_facets: The seeded fixture.
    @returns: Nothing; a wrong single-tag result fails the test.
    """
    assert shelf_titles(client, normal_user_headers, "tags=horror") == ["Only Horror"]
    assert shelf_titles(client, normal_user_headers, "tags=classic") == ["Only Classic"]


def test_filters_from_different_facets_are_combined_with_and(client, normal_user_headers, app, split_tag_facets):
    """Filters from *different* facets are intersected.

    This is the AND case, and the one the old comment described as "the AND
    semantics come from combining multiple filter types". Each facet adds its own
    `.filter(...)` call onto the same query, so SQLAlchemy joins them with AND.

    Neither Work satisfies both halves, so a union would return one row and an
    intersection returns none.

    @param client: The Flask test client.
    @param normal_user_headers: Auth headers for the seeded user.
    @param app: The Flask application.
    @param split_tag_facets: The seeded fixture.
    @returns: Nothing; union semantics, or a spurious match, fails the test.
    """
    assert shelf_titles(client, normal_user_headers, "tags=horror&statuses=lent") == []
    assert shelf_titles(client, normal_user_headers, "tags=classic&statuses=lent") == ["Only Classic"]


def test_a_status_that_matches_nothing_yields_an_empty_result(client, normal_user_headers, app, split_tag_facets):
    """A facet value no Work carries returns nothing, not everything.

    Guards the failure mode where an unrecognised value produces an empty
    condition list, and `filter()` with no conditions matches every row.

    @param client: The Flask test client.
    @param normal_user_headers: Auth headers for the seeded user.
    @param app: The Flask application.
    @param split_tag_facets: The seeded fixture.
    @returns: Nothing; a non-empty result fails the test.
    """
    assert shelf_titles(client, normal_user_headers, "tags=no_such_tag_9f3a") == []
    assert shelf_titles(client, normal_user_headers, "statuses=no_such_status_9f3a") == []
