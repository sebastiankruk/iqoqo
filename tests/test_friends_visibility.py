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
"""Test suite for three-tier visibility (private, friends_only, public) and unified friends management."""

from __future__ import annotations

import pytest

from app.api.auth import generate_internal_jwt
from app.core.friend_service import get_friend_user_ids, is_friend_of
from app.db.auth import User, UserFriendship
from app.db.core import Expression, Item, Manifestation, Work
from app.db.models import Permission, Role, db
from app.db.social import Notification


@pytest.fixture
def collector_a(app):
    """Fixture providing user A with write:item permission."""
    with app.app_context():
        perm = Permission.query.filter_by(name="write:item").first()
        if not perm:
            perm = Permission(name="write:item")
            db.session.add(perm)

        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
        if perm not in role.permissions:
            role.permissions.append(perm)

        user = User(
            email="alice@iqoqo.local",
            public_username="alice",
            display_name="Alice",
            visibility="public",
            default_item_visibility="private",
        )
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def headers_a(app, collector_a):
    """Auth headers for collector A."""
    with app.app_context():
        user = db.session.get(User, collector_a)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def collector_b(app):
    """Fixture providing user B with write:item permission."""
    with app.app_context():
        role = Role.query.filter_by(name="user").first()
        user = User(
            email="bob@iqoqo.local",
            public_username="bob",
            display_name="Bob",
            visibility="public",
            default_item_visibility="private",
        )
        if role:
            user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def headers_b(app, collector_b):
    """Auth headers for collector B."""
    with app.app_context():
        user = db.session.get(User, collector_b)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def book_manifestation(app):
    """Fixture providing a sample book manifestation."""
    with app.app_context():
        work = Work(title="The Hobbit", meta={"authors": ["J.R.R. Tolkien"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(expression_id=expr.id, isbn13="9780261103344", meta={"title": "The Hobbit"})
        db.session.add(man)
        db.session.commit()
        return man.id


def test_user_three_tier_visibility_settings(client, app, collector_a, headers_a):
    """Collector can configure visibility and default_item_visibility to 'friends_only'."""
    res = client.patch(
        "/api/profile/settings",
        json={"visibility": "friends_only", "default_item_visibility": "friends_only"},
        headers=headers_a,
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["visibility"] == "friends_only"
    assert data["default_item_visibility"] == "friends_only"

    with app.app_context():
        user = db.session.get(User, collector_a)
        assert user.visibility == "friends_only"
        assert user.default_item_visibility == "friends_only"


def test_item_creation_inherits_friends_only_default(client, app, collector_a, headers_a, book_manifestation):
    """When default_item_visibility is friends_only, new item is created with visibility='friends_only'."""
    with app.app_context():
        user = db.session.get(User, collector_a)
        user.default_item_visibility = "friends_only"
        db.session.commit()

    res = client.post(
        "/api/items",
        json={"manifestation_id": book_manifestation, "status": "want_to_read"},
        headers=headers_a,
    )
    assert res.status_code == 201
    item_id = res.get_json()["data"]["id"]

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item is not None
        assert item.visibility == "friends_only"
        assert item.is_hidden is True
        assert item.is_public is False


def test_item_visibility_override_via_patch(client, app, collector_a, headers_a, book_manifestation):
    """Item visibility can be explicitly patched to 'friends_only', 'public', or 'private'."""
    with app.app_context():
        item = Item(
            manifestation_id=book_manifestation,
            owner_id=collector_a,
            status="reading",
            collection_status="available",
            visibility="public",
            is_hidden=False,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Update to friends_only
    res = client.patch(
        f"/api/items/{item_id}",
        json={"visibility": "friends_only"},
        headers=headers_a,
    )
    assert res.status_code == 200

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item.visibility == "friends_only"
        assert item.is_hidden is True
        assert item.is_public is False

    # Update to public
    res = client.patch(
        f"/api/items/{item_id}",
        json={"visibility": "public"},
        headers=headers_a,
    )
    assert res.status_code == 200

    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item.visibility == "public"
        assert item.is_hidden is False
        assert item.is_public is True


def test_friends_crud_and_notifications_flow(client, app, collector_a, headers_a, collector_b, headers_b):
    """Full lifecycle of friend requests: send, notification, accept, list, remove."""
    # Alice sends friend request to Bob
    res = client.post(
        "/api/profile/friends/request",
        json={"identifier": "bob"},
        headers=headers_a,
    )
    assert res.status_code == 201
    friendship_id = res.get_json()["data"]["id"]

    with app.app_context():
        notif = Notification.query.filter_by(user_id=collector_b, type="friend_request").first()
        assert notif is not None
        assert notif.payload_json["username"] in ("alice", "alice@iqoqo.local")

        fs = db.session.get(UserFriendship, friendship_id)
        assert fs.status == "pending"
        assert not is_friend_of(collector_a, collector_b)

    # Bob accepts request
    accept_res = client.post(
        f"/api/profile/friends/{friendship_id}/respond",
        json={"action": "accept"},
        headers=headers_b,
    )
    assert accept_res.status_code == 200

    with app.app_context():
        assert is_friend_of(collector_a, collector_b) is True
        assert is_friend_of(collector_b, collector_a) is True
        assert collector_b in get_friend_user_ids(collector_a)
        assert collector_a in get_friend_user_ids(collector_b)

    # Alice lists friends
    list_res = client.get("/api/profile/friends", headers=headers_a)
    assert list_res.status_code == 200
    friends_list = list_res.get_json()["data"]["accepted"]
    assert len(friends_list) == 1
    assert friends_list[0]["user_id"] == str(collector_b)

    # Alice removes friend
    del_res = client.delete(f"/api/profile/friends/{friendship_id}", headers=headers_a)
    assert del_res.status_code == 200

    with app.app_context():
        assert is_friend_of(collector_a, collector_b) is False


def test_friends_only_item_access_authorization(client, app, collector_a, headers_a, collector_b, headers_b, book_manifestation):
    """Friends-only items are visible to accepted friends, but completely 404 to non-friends & anonymous."""
    with app.app_context():
        item = Item(
            manifestation_id=book_manifestation,
            owner_id=collector_a,
            status="reading",
            collection_status="available",
            visibility="friends_only",
            is_hidden=True,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # 1. Anonymous visitor -> 404
    anon_res = client.get(f"/api/items/{item_id}")
    assert anon_res.status_code == 404

    # 2. Non-friend Bob -> 404
    non_friend_res = client.get(f"/api/items/{item_id}", headers=headers_b)
    assert non_friend_res.status_code == 404

    # Now make Alice and Bob friends
    with app.app_context():
        fs = UserFriendship(requester_id=collector_a, addressee_id=collector_b, status="accepted")
        db.session.add(fs)
        db.session.commit()

    # 3. Accepted friend Bob -> 200 OK
    friend_res = client.get(f"/api/items/{item_id}", headers=headers_b)
    assert friend_res.status_code == 200
    item_data = friend_res.get_json()["data"]
    assert item_data["id"] == item_id
    assert item_data["visibility"] == "friends_only"
    assert item_data["is_friend"] is True
    assert item_data["owner_id"] == str(collector_a)


def test_scope_friends_collection_and_stats(client, app, collector_a, headers_a, collector_b, book_manifestation):
    """Querying /api/items?scope=friends and /api/stats?scope=friends returns friend items."""
    with app.app_context():
        item_public = Item(
            manifestation_id=book_manifestation,
            owner_id=collector_b,
            status="reading",
            collection_status="available",
            visibility="public",
            is_hidden=False,
        )
        item_friends = Item(
            manifestation_id=book_manifestation,
            owner_id=collector_b,
            status="read",
            collection_status="available",
            visibility="friends_only",
            is_hidden=True,
        )
        item_private = Item(
            manifestation_id=book_manifestation,
            owner_id=collector_b,
            status="want_to_read",
            collection_status="available",
            visibility="private",
            is_hidden=True,
        )
        db.session.add_all([item_public, item_friends, item_private])

        # Establish friendship
        fs = UserFriendship(requester_id=collector_a, addressee_id=collector_b, status="accepted")
        db.session.add(fs)
        db.session.commit()
        pub_id = item_public.id
        friends_id = item_friends.id
        priv_id = item_private.id

    # Query items with scope=friends
    res = client.get("/api/items?scope=friends", headers=headers_a)
    assert res.status_code == 200
    data = res.get_json()["data"]
    returned_ids = [it["id"] for it in data]
    assert pub_id in returned_ids
    assert friends_id in returned_ids
    assert priv_id not in returned_ids

    # Query stats with scope=friends
    stats_res = client.get("/api/stats?scope=friends", headers=headers_a)
    assert stats_res.status_code == 200
    stats = stats_res.get_json()["data"]
    assert stats["total_items"] == 2
    assert stats["items_reading"] == 1
    assert stats["items_read"] == 1
