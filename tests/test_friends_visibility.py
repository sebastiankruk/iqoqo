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
from sqlalchemy import select

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
        assert notif.target_iri == "/profile?tab=incoming#friends"
        assert notif.payload_json["target_iri"] == "/profile?tab=incoming#friends"

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
        accept_notif = Notification.query.filter_by(user_id=collector_a, type="friend_accepted").first()
        assert accept_notif is not None
        assert accept_notif.target_iri == "/profile?tab=accepted#friends"
        assert accept_notif.payload_json["target_iri"] == "/profile?tab=accepted#friends"

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


def test_federated_friend_request_and_prefixed_id_disambiguation(app, client, collector_a, headers_a):
    """Verifies sending friend request to @user@domain, PENDING follow creation, and fed: prefixed ID response."""
    from app.db.federation import FederationActor, FederationFollower, FederationInstance, FollowStatus

    with app.app_context():
        inst = FederationInstance(domain="remote.social", trust_level="trusted")
        db.session.add(inst)
        db.session.flush()

        actor = FederationActor(
            actor_uri="https://remote.social/users/charlie",
            inbox_url="https://remote.social/users/charlie/inbox",
            instance_id=inst.id,
            username="charlie",
            display_name="Charlie Remote",
        )
        db.session.add(actor)
        db.session.commit()
        actor_id = actor.id

    # Send request to @charlie@remote.social
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.core.federation_dispatch.dispatch_follow", lambda u, a: True)
        res = client.post(
            "/api/profile/friends/request",
            headers=headers_a,
            json={"identifier": "@charlie@remote.social"},
        )
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["id"].startswith("fed:")

    # Verify friend list returns federated entry with fed: prefix and username
    list_res = client.get("/api/profile/friends", headers=headers_a)
    assert list_res.status_code == 200
    list_data = list_res.get_json()["data"]
    incoming_or_accepted = list_data["incoming"] + list_data["accepted"]
    assert any(str(entry.get("friendship_id", "")).startswith("fed:") for entry in incoming_or_accepted)

    # Now verify incoming federated request acceptance using fed: prefix
    with app.app_context():
        fol = db.session.execute(
            select(FederationFollower).where(
                FederationFollower.local_user_id == collector_a,
                FederationFollower.remote_actor_id == actor_id,
            )
        ).scalar_one()
        fol.status = FollowStatus.PENDING
        db.session.commit()
        fol_id = fol.id

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.core.federation_dispatch.dispatch_accept_follow", lambda u, a, o: None)
        resp_res = client.post(
            f"/api/profile/friends/fed:{fol_id}/respond",
            headers=headers_a,
            json={"action": "accept"},
        )
        assert resp_res.status_code == 200

        with app.app_context():
            fol_after = db.session.get(FederationFollower, fol_id)
            assert fol_after.status == FollowStatus.ACCEPTED

        # Remove federated friend
        del_res = client.delete(f"/api/profile/friends/fed:{fol_id}", headers=headers_a)
        assert del_res.status_code == 200
        with app.app_context():
            assert db.session.get(FederationFollower, fol_id) is None


def test_item_is_hidden_and_visibility_synchronization(app, collector_a):
    """Verifies Item(is_hidden=True) synchronizes with visibility='private' without infinite recursion."""
    with app.app_context():
        item1 = Item(owner_id=collector_a, manifestation_id=1, is_hidden=True)
        assert item1.is_hidden is True
        assert item1.visibility == "private"

        item2 = Item(owner_id=collector_a, manifestation_id=1, visibility="private")
        assert item2.is_hidden is True
        assert item2.visibility == "private"

        item3 = Item(owner_id=collector_a, manifestation_id=1, visibility="public")
        assert item3.is_hidden is False
        assert item3.visibility == "public"

        # Explicit set_visibility
        item3.set_visibility("friends_only")
        assert item3.visibility == "friends_only"
        assert item3.is_hidden is True

        # Direct property assignment
        item4 = Item(owner_id=collector_a, manifestation_id=1)
        item4.visibility = "friends_only"
        assert item4.visibility == "friends_only"
        assert item4.is_hidden is True


def test_loan_request_on_friends_only_item(app, client, collector_a, collector_b, headers_b, book_manifestation):
    """Test loan request on friends_only item succeeds for confirmed friends and rejects for non-friends."""
    with app.app_context():
        # Item owned by Alice with friends_only visibility
        item = Item(
            owner_id=collector_a,
            manifestation_id=book_manifestation,
            visibility="friends_only",
            collection_status="available",
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Bob is not yet friends with Alice -> 403 Forbidden
    res_non_friend = client.post(
        f"/api/lending/items/{item_id}/loan-request",
        headers=headers_b,
        json={"notes": "Can I borrow this?"},
    )
    assert res_non_friend.status_code == 403

    # Now make Alice and Bob friends
    with app.app_context():
        friendship = UserFriendship(
            requester_id=collector_a,
            addressee_id=collector_b,
            status="accepted",
        )
        db.session.add(friendship)
        db.session.commit()

    # Now Bob requests loan -> 201 Created
    res_friend = client.post(
        f"/api/lending/items/{item_id}/loan-request",
        headers=headers_b,
        json={"notes": "Can I borrow this now, friend?"},
    )
    assert res_friend.status_code == 201


def test_sparql_and_search_friends_only_visibility(app, client, collector_a, collector_b, headers_b, book_manifestation):
    """Test that SPARQL queries and search with scope=friends include friends_only items for confirmed friends."""
    with app.app_context():
        # Item owned by Alice with friends_only visibility
        item = Item(
            owner_id=collector_a,
            manifestation_id=book_manifestation,
            visibility="friends_only",
            collection_status="available",
        )
        db.session.add(item)
        friendship = UserFriendship(
            requester_id=collector_a,
            addressee_id=collector_b,
            status="accepted",
        )
        db.session.add(friendship)
        db.session.commit()
        item_id = item.id

    # 1. Search with scope=friends
    res_search = client.get(
        "/api/items?scope=friends&q=Hobbit",
        headers=headers_b,
    )
    assert res_search.status_code == 200
    search_data = res_search.get_json()["data"]
    found_ids = [it["id"] for it in search_data]
    assert item_id in found_ids

    # 2. SPARQL _get_sparql_items includes friends_only item for Bob
    with app.app_context():
        from app.api.sparql import _get_sparql_items

        user_b = db.session.get(User, collector_b)
        sparql_items = _get_sparql_items(user_b)
        sparql_item_ids = [it.id for it in sparql_items]
        assert item_id in sparql_item_ids


def test_check_inventory_friends_only_gate(app, client, collector_a, collector_b, headers_b, book_manifestation):
    """Test check_inventory only exposes friends_only items to confirmed friends, not anonymous callers."""
    with app.app_context():
        item = Item(
            owner_id=collector_a,
            manifestation_id=book_manifestation,
            visibility="friends_only",
            collection_status="available",
        )
        db.session.add(item)
        friendship = UserFriendship(
            requester_id=collector_a,
            addressee_id=collector_b,
            status="accepted",
        )
        db.session.add(friendship)
        db.session.commit()
        item_id = item.id

    # Unauthenticated user checks Bob's friend inventory -> friend's friends_only item NOT returned
    unauth_res = client.post(
        "/api/public/u/bob/check",
        json={"query": "Hobbit", "include_friends": True},
    )
    assert unauth_res.status_code == 200
    unauth_data = unauth_res.get_json()["data"]
    assert not any(it.get("type") == "friend_item" for it in unauth_data)

    # Authenticated friend (Bob) checks Bob's friend inventory -> Alice's friends_only item IS returned
    auth_res = client.post(
        "/api/public/u/bob/check",
        headers=headers_b,
        json={"query": "Hobbit", "include_friends": True},
    )
    assert auth_res.status_code == 200
    auth_data = auth_res.get_json()["data"]
    friend_items = [it for it in auth_data if it.get("type") == "friend_item"]
    assert len(friend_items) == 1
    assert friend_items[0]["id"] == item_id
