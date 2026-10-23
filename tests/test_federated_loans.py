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
"""Tests for federated friends, collection browsing, and cross-instance loan workflows (C81)."""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.api.auth import generate_internal_jwt
from app.core.federation_client import FederationClient
from app.core.federation_handlers import handle_activity
from app.db import db
from app.db.auth import User
from app.db.core import (
    Expression,
    Item,
    ItemCustodyEvent,
    Manifestation,
    Work,
)
from app.db.federation import (
    FederationActor,
    FederationConsent,
    FederationFollower,
    FederationInstance,
    FollowStatus,
    TrustLevel,
)
from app.db.lending import LoanRequest


@pytest.fixture
def owner_data(app):
    """Create local item owner with federation consent and return (user_id, auth_headers)."""
    with app.app_context():
        u = User(
            email="owner_c81@iqoqo.local",
            public_username="owner_c81",
            display_name="Owner C81",
            visibility="public",
        )
        u.set_password("Secret123!")
        db.session.add(u)
        db.session.flush()

        consent = FederationConsent(user_id=u.id, federated_profile=True, federated_collection=True)
        db.session.add(consent)
        db.session.commit()
        token = generate_internal_jwt(u)
        return u.id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def borrower_data(app):
    """Create local borrower user and return (user_id, auth_headers)."""
    with app.app_context():
        u = User(
            email="borrower_c81@iqoqo.local",
            public_username="borrower_c81",
            display_name="Borrower C81",
            visibility="public",
        )
        u.set_password("Secret123!")
        db.session.add(u)
        db.session.flush()

        consent = FederationConsent(user_id=u.id, federated_profile=True, federated_collection=True)
        db.session.add(consent)
        db.session.commit()
        token = generate_internal_jwt(u)
        return u.id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_item(app, owner_data):
    """Create a physical item owned by owner_data."""
    owner_id, _ = owner_data
    with app.app_context():
        w = Work(title="The Dispossessed")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id, publisher="Harper & Row")
        db.session.add(m)
        db.session.flush()

        it = Item(
            manifestation_id=m.id,
            owner_id=owner_id,
            collection_status="available",
            status="want_to_read",
        )
        db.session.add(it)
        db.session.commit()
        return it.id


@pytest.fixture
def remote_friend_actor(app):
    """Create a remote FederationActor on a trusted instance."""
    with app.app_context():
        inst = FederationInstance(domain="remote.library", trust_level=TrustLevel.TRUSTED)
        db.session.add(inst)
        db.session.flush()

        actor = FederationActor(
            actor_uri="https://remote.library/actor/alice",
            inbox_url="https://remote.library/actor/alice/inbox",
            outbox_url="https://remote.library/actor/alice/outbox",
            username="alice",
            display_name="Alice Reader",
            instance_id=inst.id,
        )
        db.session.add(actor)
        db.session.commit()
        return actor.id


def test_outbound_follow_records_pending_follower(client, app, owner_data):
    """Outbound follow creates FederationFollower record with pending status."""
    owner_id, headers = owner_data
    with app.app_context():
        inst = FederationInstance(domain="fedsocial.org", trust_level=TrustLevel.TRUSTED)
        db.session.add(inst)
        db.session.commit()

    with patch.object(FederationClient, "fetch_actor") as mock_fetch, patch.object(FederationClient, "post_to_inbox") as mock_post:
        mock_fetch.return_value = {
            "id": "https://fedsocial.org/actor/bob",
            "inbox": "https://fedsocial.org/actor/bob/inbox",
            "preferredUsername": "bob",
        }
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 202
        mock_post.return_value = mock_post_resp

        res = client.post(
            "/api/federation/follow",
            json={"actor_uri": "https://fedsocial.org/actor/bob"},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

        # Verify follower record exists in pending status
        with app.app_context():
            stmt = select(FederationFollower).where(FederationFollower.local_user_id == owner_id)
            follower = db.session.execute(stmt).scalars().first()
            assert follower is not None
            assert follower.status == FollowStatus.PENDING


def test_inbound_accept_updates_follow_status(app, owner_data, remote_friend_actor):
    """Inbound Accept activity transitions follower status from pending to accepted."""
    owner_id, _ = owner_data
    with app.app_context():
        follower = FederationFollower(
            local_user_id=owner_id,
            remote_actor_id=remote_friend_actor,
            status=FollowStatus.PENDING,
        )
        db.session.add(follower)
        db.session.commit()

        accept_activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": "https://remote.library/activities/accept-1",
            "type": "Accept",
            "actor": "https://remote.library/actor/alice",
            "object": {
                "type": "Follow",
                "actor": f"http://localhost:5000/actor/u/{owner_id}",
                "object": "https://remote.library/actor/alice",
            },
        }

        handled = handle_activity(accept_activity)
        assert handled is True

        db.session.refresh(follower)
        assert follower.status == FollowStatus.ACCEPTED


def test_get_federated_friends_and_cached_collection(client, app, owner_data, remote_friend_actor):
    """Listing friends and fetching friend collections with cache works."""
    owner_id, headers = owner_data
    with app.app_context():
        follower = FederationFollower(
            local_user_id=owner_id,
            remote_actor_id=remote_friend_actor,
            status=FollowStatus.ACCEPTED,
        )
        db.session.add(follower)
        db.session.commit()

    # 1. Test GET /api/federation/friends
    res = client.get("/api/federation/friends", headers=headers)
    assert res.status_code == 200
    friends_data = res.get_json()["data"]
    assert len(friends_data) == 1
    assert friends_data[0]["username"] == "alice"
    assert friends_data[0]["handle"] == "@alice@remote.library"

    # 2. Test GET /api/federation/friends/<actor_id>/collections with mock
    mock_collection = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "type": "OrderedCollection",
        "totalItems": 1,
        "orderedItems": [
            {
                "id": "https://remote.library/items/99",
                "name": "Left Hand of Darkness",
                "collection_status": "available",
            }
        ],
    }

    with patch.object(FederationClient, "fetch_actor_collections") as mock_col:
        mock_col.return_value = mock_collection
        col_res = client.get(f"/api/federation/friends/{remote_friend_actor}/collections", headers=headers)
        assert col_res.status_code == 200
        assert col_res.get_json()["data"]["totalItems"] == 1


def test_inbound_offer_creates_loan_request_and_approval(client, app, owner_data, test_item, remote_friend_actor):
    """Inbound Offer creates pending LoanRequest; approval dispatches Accept and logs custody event."""
    owner_id, headers = owner_data
    with app.app_context():
        # Establish friend relationship
        follower = FederationFollower(
            local_user_id=owner_id,
            remote_actor_id=remote_friend_actor,
            status=FollowStatus.ACCEPTED,
        )
        db.session.add(follower)
        db.session.commit()

        offer_activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": "https://remote.library/activities/offer-101",
            "type": "Offer",
            "actor": "https://remote.library/actor/alice",
            "object": f"http://localhost:5000/items/{test_item}",
            "notes": "Would love to borrow this book!",
        }

        handled = handle_activity(offer_activity)
        assert handled is True

        # Verify LoanRequest created
        stmt = select(LoanRequest).where(LoanRequest.item_id == test_item)
        req = db.session.execute(stmt).scalars().first()
        assert req is not None
        assert req.status == "pending"
        assert "[Federated Offer from" in req.notes
        loan_request_id = req.id

    # Owner approves the loan request
    with patch.object(FederationClient, "post_to_inbox") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = client.patch(
            f"/api/lending/requests/{loan_request_id}",
            json={"action": "approve"},
            headers=headers,
        )
        assert res.status_code == 200

        # Verify Accept was posted to remote inbox
        mock_post.assert_called_once()
        sent_inbox = mock_post.call_args[0][0]
        sent_activity = mock_post.call_args[0][1]
        assert sent_inbox == "https://remote.library/actor/alice/inbox"
        assert sent_activity["type"] == "Accept"
        assert sent_activity["object"]["type"] == "Offer"

    # Verify item status and ItemCustodyEvent
    with app.app_context():
        it = db.session.get(Item, test_item)
        assert it.collection_status == "lent"

        # Check ItemCustodyEvent
        custody_stmt = select(ItemCustodyEvent).where(ItemCustodyEvent.item_id == test_item)
        events = db.session.execute(custody_stmt).scalars().all()
        assert len(events) >= 1
        transfer_event = [e for e in events if e.event_type == "transfer"][0]
        assert transfer_event.from_owner_id == owner_id


def test_return_loaned_item_records_custody_event(client, app, owner_data, borrower_data, test_item):
    """Returning a lent item changes status to available and records custody return event."""
    owner_id, owner_headers = owner_data
    borrower_id, _ = borrower_data
    with app.app_context():
        it = db.session.get(Item, test_item)
        it.collection_status = "lent"
        it.lent_to_user_id = borrower_id
        db.session.commit()

    res = client.post(f"/api/lending/items/{test_item}/return", headers=owner_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    with app.app_context():
        it = db.session.get(Item, test_item)
        assert it.collection_status == "available"
        assert it.lent_to_user_id is None

        # Verify return custody event
        stmt = select(ItemCustodyEvent).where(
            ItemCustodyEvent.item_id == test_item,
            ItemCustodyEvent.event_type == "return",
        )
        ret_event = db.session.execute(stmt).scalars().first()
        assert ret_event is not None
        assert ret_event.to_owner_id == owner_id
        assert ret_event.from_owner_id == borrower_id


def test_outbound_federated_loan_request(client, app, owner_data, remote_friend_actor):
    """POST /api/lending/federated-request dispatches an Offer activity to remote actor."""
    owner_id, headers = owner_data
    with patch.object(FederationClient, "fetch_actor") as mock_fetch, patch.object(FederationClient, "post_to_inbox") as mock_post:
        mock_fetch.return_value = {
            "id": "https://remote.library/actor/alice",
            "inbox": "https://remote.library/actor/alice/inbox",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_post.return_value = mock_resp

        res = client.post(
            "/api/lending/federated-request",
            json={
                "target_item_uri": "https://remote.library/items/42",
                "target_actor_uri": "https://remote.library/actor/alice",
                "notes": "May I borrow your exemplar?",
            },
            headers=headers,
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["success"] is True
        assert data["activity"]["type"] == "Offer"
        assert data["activity"]["object"] == "https://remote.library/items/42"


def test_check_inventory_with_federated_friends(client, app, owner_data, remote_friend_actor):
    """Check inventory includes matches from federated friends when requested."""
    owner_id, _ = owner_data
    with app.app_context():
        follower = FederationFollower(
            local_user_id=owner_id,
            remote_actor_id=remote_friend_actor,
            status=FollowStatus.ACCEPTED,
        )
        db.session.add(follower)
        db.session.commit()

    mock_collection = {
        "orderedItems": [
            {
                "id": "https://remote.library/items/55",
                "name": "Solaris (Stanislaw Lem)",
                "collection_status": "available",
                "image": "https://remote.library/covers/solaris.jpg",
            }
        ]
    }

    with patch.object(FederationClient, "fetch_actor_collections") as mock_col:
        mock_col.return_value = mock_collection

        res = client.post(
            "/api/public/u/owner_c81/check",
            json={"query": "Solaris", "include_friends": True},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        matches = data["data"]
        assert len(matches) == 1
        assert matches[0]["type"] == "friend_item"
        assert matches[0]["title"] == "Solaris (Stanislaw Lem)"
        assert matches[0]["owner_handle"] == "@alice@remote.library"
