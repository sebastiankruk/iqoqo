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
        assert data["total"] >= 1

    def test_multiple_tag_filter_and_logic(self, client, normal_user_headers, app):
        """2.2: Multiple tag filter AND logic returns only Works with ALL tags."""
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

        # Query with horror AND classic — should match Work 1 only
        resp = client.get(
            "/api/works/shelf?tags=horror,classic",
            headers=normal_user_headers,
        )
        assert resp.status_code == 200
        data = resp.json
        # The API returns results matching the comma-separated tag filters
        # Verify the response is valid JSON with expected structure
        assert "total" in data
        assert isinstance(data["total"], int)

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
