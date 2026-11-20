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
"""Tests for profile and item visibility API."""

import json

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(email="visibility@iqoqo.local", display_name="Visibility User", visibility="private")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def auth_headers(app, test_user):
    with app.app_context():
        user = db.session.get(User, test_user)
        token = generate_internal_jwt(user)
    return {"Authorization": f"Bearer {token}"}


def test_update_profile_settings(client, test_user, auth_headers):
    payload = {"public_username": "newuser", "bio": "I am a cave man", "visibility": "public"}
    response = client.patch("/api/profile/settings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert data["data"]["public_username"] == "newuser"
    assert data["data"]["bio"] == "I am a cave man"
    assert data["data"]["visibility"] == "public"


def test_update_username_conflict(client, app, test_user, auth_headers):
    with app.app_context():
        other = User(email="other@iqoqo.local", public_username="taken")
        db.session.add(other)
        db.session.commit()

    response = client.patch("/api/profile/settings", json={"public_username": "taken"}, headers=auth_headers)
    assert response.status_code == 409


def test_toggle_item_visibility(client, app, test_user, auth_headers):
    with app.app_context():
        work = Work(title="Visibility Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="1234567890123")
        db.session.add(mani)
        db.session.flush()
        item = Item(owner_id=test_user, manifestation_id=mani.id, is_hidden=False)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Hide
    response = client.patch(f"/api/items/{item_id}/visibility", json={"is_hidden": True}, headers=auth_headers)
    assert response.status_code == 200
    assert json.loads(response.data)["is_hidden"] is True

    # Show
    response = client.patch(f"/api/items/{item_id}/visibility", json={"is_hidden": False}, headers=auth_headers)
    assert response.status_code == 200
    assert json.loads(response.data)["is_hidden"] is False


def test_toggle_item_visibility_unauthorized(client, app, test_user):
    with app.app_context():
        # Create item for test_user
        work = Work(title="Spy Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="1234567890124")
        db.session.add(mani)
        db.session.flush()
        item = Item(owner_id=test_user, manifestation_id=mani.id)
        db.session.add(item)

        # Create another user
        other = User(email="spy@iqoqo.local")
        db.session.add(other)
        db.session.commit()
        item_id = item.id
        other_token = generate_internal_jwt(other)

    headers = {"Authorization": f"Bearer {other_token}"}
    response = client.patch(f"/api/items/{item_id}/visibility", json={"is_hidden": True}, headers=headers)
    assert response.status_code == 404  # BOLA protection


def test_filter_items_by_visibility_and_search(client, app, test_user, auth_headers):
    with app.app_context():
        work = Work(title="Visibility Filter Book")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="9780000000011")
        db.session.add(mani)
        db.session.flush()

        pub_item = Item(owner_id=test_user, manifestation_id=mani.id)
        pub_item.set_visibility("public")
        fr_item = Item(owner_id=test_user, manifestation_id=mani.id)
        fr_item.set_visibility("friends_only")
        priv_item = Item(owner_id=test_user, manifestation_id=mani.id)
        priv_item.set_visibility("private")
        db.session.add_all([pub_item, fr_item, priv_item])
        db.session.commit()
        ids = {"public": pub_item.id, "friends_only": fr_item.id, "private": priv_item.id}

    res_fr = client.get("/api/items?visibility=friends_only", headers=auth_headers)
    assert res_fr.status_code == 200
    assert [i["id"] for i in res_fr.get_json()["data"]] == [ids["friends_only"]]

    # 'hidden' alias maps to 'private'
    res_hid = client.get("/api/items?visibility=hidden", headers=auth_headers)
    assert res_hid.status_code == 200
    assert [i["id"] for i in res_hid.get_json()["data"]] == [ids["private"]]

    # Combined with text search q=
    res_search = client.get("/api/items?visibility=friends_only&q=Visibility", headers=auth_headers)
    assert res_search.status_code == 200
    assert [i["id"] for i in res_search.get_json()["data"]] == [ids["friends_only"]]


def test_filter_items_by_visibility_prevents_cross_user_private_leak(client, app, test_user):
    from app.db.auth import UserFriendship

    with app.app_context():
        friend = User(email="friendvis@iqoqo.local")
        db.session.add(friend)
        db.session.flush()
        db.session.add(UserFriendship(requester_id=test_user, addressee_id=friend.id, status="accepted"))

        work = Work(title="Private Friend Book")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="9780000000012")
        db.session.add(mani)
        db.session.flush()
        priv_item = Item(owner_id=test_user, manifestation_id=mani.id)
        priv_item.set_visibility("private")
        fr_item = Item(owner_id=test_user, manifestation_id=mani.id)
        fr_item.set_visibility("friends_only")
        db.session.add_all([priv_item, fr_item])
        db.session.commit()
        fr_id = fr_item.id
        friend_headers = {"Authorization": f"Bearer {generate_internal_jwt(friend)}"}

    res_priv = client.get("/api/items?scope=friends&visibility=private", headers=friend_headers)
    assert res_priv.status_code == 200
    assert res_priv.get_json()["data"] == []

    res_fr = client.get("/api/items?scope=friends&visibility=friends_only", headers=friend_headers)
    assert res_fr.status_code == 200
    assert [i["id"] for i in res_fr.get_json()["data"]] == [fr_id]


def test_bulk_update_item_visibility_and_ownership_guards(client, app, test_user, auth_headers):
    from sqlalchemy import select

    from app.core.permissions import PermissionName
    from app.db.models import Permission, Role

    with app.app_context():
        user = db.session.get(User, test_user)
        write_perm = db.session.execute(select(Permission).where(Permission.name == PermissionName.WRITE_ITEM)).scalars().first()
        if not write_perm:
            write_perm = Permission(name=PermissionName.WRITE_ITEM)
            db.session.add(write_perm)
        role = Role(name="bulk_vis_writer")
        role.permissions.append(write_perm)
        db.session.add(role)
        user.roles.append(role)

        other = User(email="bulkother@iqoqo.local")
        db.session.add(other)
        db.session.flush()
        work = Work(title="Bulk Vis Work")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="9780000000013")
        db.session.add(mani)
        db.session.flush()
        i1 = Item(owner_id=test_user, manifestation_id=mani.id)
        i1.set_visibility("public")
        i2 = Item(owner_id=test_user, manifestation_id=mani.id)
        i2.set_visibility("public")
        i3 = Item(owner_id=other.id, manifestation_id=mani.id)
        i3.set_visibility("public")
        db.session.add_all([i1, i2, i3])
        db.session.commit()
        owned_ids = [i1.id, i2.id]
        other_id = i3.id
        other_headers = {"Authorization": f"Bearer {generate_internal_jwt(other)}"}

    # Unprivileged user without write:item is denied (403)
    assert (
        client.patch(
            "/api/items/bulk-visibility",
            json={"item_ids": [other_id], "visibility": "private"},
            headers=other_headers,
        ).status_code
        == 403
    )

    # Success on owned batch
    res_ok = client.patch(
        "/api/items/bulk-visibility",
        json={"item_ids": owned_ids, "visibility": "friends_only"},
        headers=auth_headers,
    )
    assert res_ok.status_code == 200
    assert res_ok.get_json()["data"]["updated_count"] == 2
    with app.app_context():
        assert db.session.get(Item, owned_ids[0]).visibility == "friends_only"
        assert db.session.get(Item, owned_ids[1]).is_hidden is True

    # Rejects mixed batch with unowned item atomically with uniform 404 (prevents existence oracle)
    res_forbid = client.patch(
        "/api/items/bulk-visibility",
        json={"item_ids": [owned_ids[0], other_id], "visibility": "private"},
        headers=auth_headers,
    )
    assert res_forbid.status_code == 404
    with app.app_context():
        assert db.session.get(Item, owned_ids[0]).visibility == "friends_only"
        assert db.session.get(Item, other_id).visibility == "public"

    # Rejects missing item (404) and invalid visibility (400)
    assert (
        client.patch(
            "/api/items/bulk-visibility",
            json={"item_ids": [999999], "visibility": "public"},
            headers=auth_headers,
        ).status_code
        == 404
    )
    assert (
        client.patch(
            "/api/items/bulk-visibility",
            json={"item_ids": owned_ids, "visibility": "bogus"},
            headers=auth_headers,
        ).status_code
        == 400
    )


def test_bulk_visibility_dispatches_fts_and_include_public_pins_non_owned(client, app, test_user, auth_headers, monkeypatch):
    """Bulk visibility triggers FTS reindex on visibility flip and include_public never leaks foreign private items."""
    from sqlalchemy import select

    from app.core.permissions import PermissionName
    from app.db.models import Permission, Role

    fts_calls: list[tuple[str, int]] = []
    monkeypatch.setattr("app.api.items.enqueue_fts_reindex", lambda etype, eid: fts_calls.append((etype, eid)))

    with app.app_context():
        user = db.session.get(User, test_user)
        write_perm = db.session.execute(select(Permission).where(Permission.name == PermissionName.WRITE_ITEM)).scalars().first()
        if not write_perm:
            write_perm = Permission(name=PermissionName.WRITE_ITEM)
            db.session.add(write_perm)
        role = Role(name="bulk_fts_writer")
        role.permissions.append(write_perm)
        db.session.add(role)
        user.roles.append(role)

        other = User(email="otherpin@iqoqo.local")
        db.session.add(other)
        db.session.flush()
        work = Work(title="Pin Test Book")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id)
        db.session.add(expr)
        db.session.flush()
        mani = Manifestation(expression_id=expr.id, isbn13="9780000000099")
        db.session.add(mani)
        db.session.flush()
        own = Item(owner_id=test_user, manifestation_id=mani.id)
        own.set_visibility("public")
        foreign_priv = Item(owner_id=other.id, manifestation_id=mani.id)
        foreign_priv.set_visibility("private")
        db.session.add_all([own, foreign_priv])
        db.session.commit()
        own_id = own.id
        foreign_id = foreign_priv.id

    res_flip = client.patch(
        "/api/items/bulk-visibility",
        json={"item_ids": [own_id], "visibility": "private"},
        headers=auth_headers,
    )
    assert res_flip.status_code == 200
    assert ("item", own_id) in fts_calls

    res_list = client.get("/api/items?include_public=true&visibility=friends_only,private", headers=auth_headers)
    assert res_list.status_code == 200
    returned_ids = {row["id"] for row in res_list.get_json()["data"]}
    assert foreign_id not in returned_ids
