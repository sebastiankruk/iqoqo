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
"""Extended tests for the public API endpoints."""

import json

import pytest

from app.api.auth import generate_internal_jwt
from app.db.contributions import Contributor, WorkContribution
from app.db.models import Expression, Item, Manifestation, SharedCollection, User, UserWorkIntent, Work, db


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(email="extended@iqoqo.local", public_username="extuser", visibility="public")
        db.session.add(user)
        db.session.commit()
        return user.public_username


def test_pagination(client, app, test_user):
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Pagination Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()

        for _ in range(15):
            item = Item(owner_id=user.id, manifestation_id=mani.id, status="read")
            db.session.add(item)
        db.session.commit()

    # Page 1
    response = client.get(f"/api/public/u/{test_user}/items?per_page=10&page=1")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 10
    assert data["data"]["total"] == 15
    assert data["data"]["pages"] == 2

    # Page 2
    response = client.get(f"/api/public/u/{test_user}/items?per_page=10&page=2")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 5


def test_shared_collection_with_status_filter(client, app, test_user):
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Shared Filter Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()

        # 2 read, 1 wishlist
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="wish_list"))

        collection = SharedCollection(user_id=user.id, name="My Read Books", filters={"status": "read"})
        db.session.add(collection)
        db.session.commit()
        token = collection.share_token

    response = client.get(f"/api/public/share/{token}")
    data = json.loads(response.data)
    assert len(data["data"]["items"]) == 2
    for item in data["data"]["items"]:
        assert item["status"] == "read"


def test_shared_collection_with_multiple_statuses(client, app, test_user):
    """A multi-status share must include every listed status.

    The collection page allows multi-select, but the share dialog used to pass
    only statuses[0], so a link was published covering a subset of what the
    sharer had on screen. The stored filter keeps the full list.
    """
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Multi Status Share Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()

        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="wish_list"))
        # want_to_read is a real ITEM_STATUSES value; to_read is not, and the
        # ck_items_status constraint rejects it -- which is why this test caught
        # the bad fixture the first time round.
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="want_to_read"))

        collection = SharedCollection(
            user_id=user.id,
            name="Read and Wishlist",
            filters={"status": ["read", "wish_list"]},
        )
        db.session.add(collection)
        db.session.commit()
        token = collection.share_token

    response = client.get(f"/api/public/share/{token}")
    data = json.loads(response.data)
    statuses = {item["status"] for item in data["data"]["items"]}

    assert statuses == {"read", "wish_list"}
    assert "want_to_read" not in statuses, "an unlisted status must not leak into the share"


def test_shared_collection_single_status_still_works(client, app, test_user):
    """Backwards compatibility: links created before this change store a bare string."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Scalar Status Compat Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()

        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="wish_list"))

        collection = SharedCollection(user_id=user.id, name="Scalar Status", filters={"status": "read"})
        db.session.add(collection)
        db.session.commit()
        token = collection.share_token

    response = client.get(f"/api/public/share/{token}")
    data = json.loads(response.data)
    assert {item["status"] for item in data["data"]["items"]} == {"read"}


def test_shared_collection_malformed_status_matches_nothing(client, app, test_user):
    """A junk filter must narrow, never widen, the shared result set."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Malformed Status Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))

        collection = SharedCollection(user_id=user.id, name="Junk Status", filters={"status": []})
        db.session.add(collection)
        db.session.commit()
        token = collection.share_token

    response = client.get(f"/api/public/share/{token}")
    data = json.loads(response.data)
    assert data["data"]["items"] == [], "an empty status list must not expose the whole library"


def test_check_inventory_missing_query(client, test_user):
    response = client.post(f"/api/public/u/{test_user}/check", json={})
    assert response.status_code == 400
    assert "required" in json.loads(response.data)["error"]


def _make_share_headers(app, email="sharer@iqoqo.local"):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email)
            db.session.add(user)
            db.session.commit()
        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}"}


def test_create_shared_collection_default_no_expiry(client, app):
    """POST /api/sharing without expires_in_days creates collection with no TTL."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "My Library"}, headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert data["name"] == "My Library"
    assert data.get("expires_at") is None


def test_create_shared_collection_with_expiry(client, app):
    """POST /api/sharing with valid expires_in_days sets expires_at."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Temporary Share", "expires_in_days": 7}, headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert data["name"] == "Temporary Share"
    assert data.get("expires_at") is not None


def test_create_shared_collection_expiry_too_low(client, app):
    """POST /api/sharing with expires_in_days < 1 returns 400."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Bad Expiry", "expires_in_days": 0}, headers=headers)
    assert response.status_code == 400


def test_create_shared_collection_expiry_too_high(client, app):
    """POST /api/sharing with expires_in_days > 365 returns 400."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Bad Expiry", "expires_in_days": 366}, headers=headers)
    assert response.status_code == 400


def test_create_shared_collection_expiry_non_int(client, app):
    """POST /api/sharing with non-integer expires_in_days returns 400."""
    headers = _make_share_headers(app)

    response = client.post("/api/sharing", json={"name": "Bad Expiry", "expires_in_days": "seven"}, headers=headers)
    assert response.status_code == 400


def test_expired_shared_collection_returns_404(client, app):
    """GET /api/public/share/<expired_token> returns 404."""
    with app.app_context():
        from datetime import UTC, datetime, timedelta

        user = User(email="expired_share@iqoqo.local")
        db.session.add(user)
        db.session.flush()
        work = Work(title="Expired Shared Collection Book")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id)
        db.session.add(manif)
        db.session.flush()
        item = Item(owner_id=user.id, manifestation_id=manif.id, status="read")
        db.session.add(item)

        expired = SharedCollection(
            user_id=user.id,
            name="Expired Share",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.session.add(expired)
        db.session.commit()
        token = expired.share_token

    response = client.get(f"/api/public/share/{token}")
    assert response.status_code == 404


def test_active_shared_collection_returns_200(client, app):
    """GET /api/public/share/<active_token> returns 200 with items."""
    with app.app_context():
        from datetime import UTC, datetime, timedelta

        user = User(email="active_share@iqoqo.local")
        db.session.add(user)
        db.session.flush()
        work = Work(title="Active Shared Collection Book")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id)
        db.session.add(manif)
        db.session.flush()
        item = Item(owner_id=user.id, manifestation_id=manif.id, status="read")
        db.session.add(item)

        active = SharedCollection(
            user_id=user.id,
            name="Active Share",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        db.session.add(active)
        db.session.commit()
        token = active.share_token

    response = client.get(f"/api/public/share/{token}")
    assert response.status_code == 200
    assert response.json["success"] is True


def test_shared_collection_with_query_filter_title_and_diacritics(client, app, test_user):
    """Search query in shared collection must match Work.title and fold diacritics."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work1 = Work(title="Dieta w insulinooporności")
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id)
        db.session.add(expr1)
        db.session.flush()
        mani1 = Manifestation(expression_id=expr1.id)
        db.session.add(mani1)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani1.id, status="read"))

        work2 = Work(title="Cooking Italian Classics")
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id)
        db.session.add(expr2)
        db.session.flush()
        mani2 = Manifestation(expression_id=expr2.id)
        db.session.add(mani2)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani2.id, status="read"))

        # Query using unaccented text 'insulinoopornosci'
        coll_unaccented = SharedCollection(
            user_id=user.id,
            name="Insulin Resistance Query",
            filters={"query": "insulinoopornosci"},
        )
        # Query using accented text 'insulinooporności'
        coll_accented = SharedCollection(
            user_id=user.id,
            name="Insulin Resistance Accented",
            filters={"query": "insulinooporności"},
        )
        db.session.add_all([coll_unaccented, coll_accented])
        db.session.commit()
        token1 = coll_unaccented.share_token
        token2 = coll_accented.share_token

    res1 = client.get(f"/api/public/share/{token1}")
    data1 = res1.json
    assert data1["success"] is True
    assert len(data1["data"]["items"]) == 1
    assert data1["data"]["items"][0]["title"] == "Dieta w insulinooporności"

    res2 = client.get(f"/api/public/share/{token2}")
    data2 = res2.json
    assert data2["success"] is True
    assert len(data2["data"]["items"]) == 1
    assert data2["data"]["items"][0]["title"] == "Dieta w insulinooporności"


def test_shared_collection_with_query_filter_contributor(client, app, test_user):
    """Search query in shared collection must match author/contributor names."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Sultans of Swing")
        db.session.add(work)
        db.session.flush()
        contrib = Contributor(name="Dire Straits")
        db.session.add(contrib)
        db.session.flush()
        db.session.add(WorkContribution(work_id=work.id, contributor_id=contrib.id, role="artist"))

        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id)
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))

        coll = SharedCollection(
            user_id=user.id,
            name="Dire Straits Search",
            filters={"query": "dire straits"},
        )
        db.session.add(coll)
        db.session.commit()
        token = coll.share_token

    res = client.get(f"/api/public/share/{token}")
    data = res.json
    assert data["success"] is True
    assert len(data["data"]["items"]) == 1
    assert data["data"]["items"][0]["title"] == "Sultans of Swing"

    # Also verify feed.xml yields item
    feed_res = client.get(f"/api/public/share/{token}/feed.xml")
    assert feed_res.status_code == 200
    assert "Sultans of Swing" in feed_res.data.decode("utf-8")


def test_shared_collection_with_query_filter_identifiers_and_meta(client, app, test_user):
    """Search query in shared collection must match barcode, UPC, and meta."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Album With Barcode")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(
            expression_id=expr.id,
            barcode="5099950453023",
            upc="012345678905",
            meta={"label": "Harvest Records"},
        )
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))

        coll_barcode = SharedCollection(user_id=user.id, name="Barcode Share", filters={"query": "5099950453023"})
        coll_upc = SharedCollection(user_id=user.id, name="UPC Share", filters={"query": "012345678905"})
        coll_meta = SharedCollection(user_id=user.id, name="Meta Share", filters={"query": "Harvest Records"})
        db.session.add_all([coll_barcode, coll_upc, coll_meta])
        db.session.commit()
        tok_barcode = coll_barcode.share_token
        tok_upc = coll_upc.share_token
        tok_meta = coll_meta.share_token

    for tok in (tok_barcode, tok_upc, tok_meta):
        res = client.get(f"/api/public/share/{tok}")
        data = res.json
        assert data["success"] is True
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["title"] == "Album With Barcode"


def test_shared_collection_query_does_not_match_arbitrary_description(client, app, test_user):
    """Search query 'dom' must not match an item just because 'dom' is in description or address."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Pieklo jest puste")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(
            expression_id=expr.id,
            meta={
                "description": "podczas powrotu do domu",
                "producerAddress": "ul. Domaniewska 48",
            },
        )
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))

        coll = SharedCollection(user_id=user.id, name="Dom Search", filters={"query": "dom", "tags": ["text"]})
        db.session.add(coll)
        db.session.commit()
        token = coll.share_token

    res = client.get(f"/api/public/share/{token}")
    data = res.json
    assert data["success"] is True
    # 'dom' is in 'domu' and 'Domaniewska' in description/address, not in title/authors/tags
    assert len(data["data"]["items"]) == 0


def test_shared_collection_authors_from_work_meta(client, app, test_user):
    """Items in shared collection must pull authors from Work.meta when manifestation meta lacks them."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Czarny Dom", meta={"authors": ["Stephen King", "Peter Straub"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, meta={})
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read"))

        coll = SharedCollection(user_id=user.id, name="Authors Test", filters={"query": "Czarny"})
        db.session.add(coll)
        db.session.commit()
        token = coll.share_token

    res = client.get(f"/api/public/share/{token}")
    data = res.json
    assert data["success"] is True
    assert len(data["data"]["items"]) == 1
    item = data["data"]["items"][0]
    assert item["title"] == "Czarny Dom"
    assert item["authors"] == ["Stephen King", "Peter Straub"]


def test_shared_collection_multi_status_with_wishlist_query(client, app, test_user):
    """Multi-status list filter with query must handle list statuses without TypeError and return intents."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Dune Messiah", meta={"authors": ["Frank Herbert"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, meta={"title": "Dune Messiah"})
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="reading"))

        # Add wishlist intent
        intent = UserWorkIntent(user_id=user.id, work_id=work.id, status="want_to_read", is_hidden=False)
        db.session.add(intent)

        coll = SharedCollection(
            user_id=user.id,
            name="Multi Status Share",
            filters={"status": ["want_to_read", "reading"], "query": "Dune"},
        )
        db.session.add(coll)
        db.session.commit()
        token = coll.share_token

    res = client.get(f"/api/public/share/{token}")
    data = res.json
    assert res.status_code == 200
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 1


def test_shared_collection_excludes_hidden_items(client, app, test_user):
    """Hidden items (is_hidden=True) must be strictly excluded from shared collections."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Hidden Secret Book", meta={"authors": ["Secret Author"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, meta={"title": "Hidden Secret Book"})
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=True))

        coll = SharedCollection(user_id=user.id, name="Public Share", filters={"query": "Hidden"})
        db.session.add(coll)
        db.session.commit()
        token = coll.share_token

    res = client.get(f"/api/public/share/{token}")
    data = res.json
    assert res.status_code == 200
    assert len(data["data"]["items"]) == 0


def test_shared_collection_escapes_sql_wildcards(client, app, test_user):
    """Searching for SQL wildcards like % or _ should not match every item."""
    with app.app_context():
        user = User.query.filter_by(public_username=test_user).first()
        work = Work(title="Normal Book Title", meta={"authors": ["Normal Author"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, meta={"title": "Normal Book Title"})
        db.session.add(mani)
        db.session.flush()
        db.session.add(Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=False))

        coll = SharedCollection(user_id=user.id, name="Wildcard Share", filters={"query": "%"})
        db.session.add(coll)
        db.session.commit()
        token = coll.share_token

    res = client.get(f"/api/public/share/{token}")
    data = res.json
    assert res.status_code == 200
    assert len(data["data"]["items"]) == 0
