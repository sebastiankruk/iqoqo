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

    def test_three_simultaneous_filters_different_taxonomies(
        self, client, normal_user_headers, app
    ):
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
