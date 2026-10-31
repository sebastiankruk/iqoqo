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
"""Unit and integration tests for friend_service and federated follow direction segregation (C87f)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.api.auth import generate_internal_jwt
from app.core.friend_service import (
    list_friends,
    remove_friend,
    respond_friend_request,
    send_friend_request,
)
from app.core.iri import canonical_actor_iri
from app.db import db
from app.db.auth import User, UserFriendship
from app.db.federation import (
    ActivityStatus,
    FederationActivity,
    FederationActor,
    FederationFollower,
    FederationInstance,
    FollowStatus,
    TrustLevel,
)


@pytest.fixture
def friend_users(app):
    """Create two test users for friendship tests."""
    with app.app_context():
        u1 = User(
            id=uuid.uuid4(),
            email=f"user1_{uuid.uuid4().hex[:6]}@example.com",
            public_username=f"u1_{uuid.uuid4().hex[:6]}",
            password_hash="argon2_fake_hash",
        )
        u2 = User(
            id=uuid.uuid4(),
            email=f"user2_{uuid.uuid4().hex[:6]}@example.com",
            public_username=f"u2_{uuid.uuid4().hex[:6]}",
            password_hash="argon2_fake_hash",
        )
        db.session.add_all([u1, u2])
        db.session.commit()
        return u1.id, u2.id


@pytest.fixture
def remote_actor_setup(app):
    """Create a remote federation instance and actor."""
    with app.app_context():
        domain = f"peer-{uuid.uuid4().hex[:6]}.library"
        inst = FederationInstance(
            domain=domain,
            software_name="iqoqo",
            trust_level=TrustLevel.TRUSTED,
        )
        db.session.add(inst)
        db.session.flush()

        actor = FederationActor(
            instance_id=inst.id,
            actor_uri=f"https://{domain}/api/federation/actor/u/remote-alice",
            inbox_url=f"https://{domain}/api/federation/inbox",
            username="alice",
            display_name="Alice from Peer",
            public_key_pem="fake-pem",
        )
        db.session.add(actor)
        db.session.commit()
        return inst.id, actor.id, actor.actor_uri, actor.inbox_url


def test_list_friends_outbound_vs_inbound_federated(app, friend_users, remote_actor_setup):
    """Outbound federated follows appear in outgoing; inbound federated follows appear in incoming."""
    u1_id, _ = friend_users
    _, actor_id, actor_uri, inbox_url = remote_actor_setup

    with app.app_context():
        # 1. Create a pending follower relationship
        follower = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor_id,
            status=FollowStatus.PENDING,
        )
        db.session.add(follower)
        db.session.commit()

        # Without an outbound FederationActivity, it defaults to INCOMING
        friends = list_friends(u1_id)
        assert len(friends["incoming"]) == 1
        assert len(friends["outgoing"]) == 0
        assert friends["incoming"][0]["friendship_id"] == f"fed:{follower.id}"

        # 2. Add an outbound FederationActivity initiated by u1_id
        actor_iri = canonical_actor_iri(u1_id)
        act = FederationActivity(
            actor_uri=actor_iri,
            activity_type="Follow",
            object_json={"type": "Follow", "actor": actor_iri, "object": actor_uri},
            target_uri=inbox_url,
            direction="outbound",
            status=ActivityStatus.QUEUED,
        )
        db.session.add(act)
        db.session.commit()

        # Now list_friends MUST place it into OUTGOING, not incoming
        friends_after = list_friends(u1_id)
        assert len(friends_after["incoming"]) == 0
        assert len(friends_after["outgoing"]) == 1
        assert friends_after["outgoing"][0]["friendship_id"] == f"fed:{follower.id}"
        assert friends_after["outgoing"][0]["is_federated"] is True


def test_respond_friend_request_rejects_outbound_follow_self_response(app, friend_users, remote_actor_setup):
    """Caller cannot accept or reject an outbound follow request they initiated."""
    u1_id, _ = friend_users
    _, actor_id, actor_uri, inbox_url = remote_actor_setup

    with app.app_context():
        follower = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor_id,
            status=FollowStatus.PENDING,
        )
        db.session.add(follower)
        db.session.flush()

        actor_iri = canonical_actor_iri(u1_id)
        act = FederationActivity(
            actor_uri=actor_iri,
            activity_type="Follow",
            object_json={"type": "Follow", "actor": actor_iri, "object": actor_uri},
            target_uri=inbox_url,
            direction="outbound",
            status=ActivityStatus.QUEUED,
        )
        db.session.add(act)
        db.session.commit()

        # Attempt to accept outbound follow
        res, err, status = respond_friend_request(u1_id, f"fed:{follower.id}", "accept")
        assert res is None
        assert status == 400
        assert "Cannot respond to an outgoing request you initiated; use cancel instead" in (err or "")

        # Attempt to reject outbound follow
        res, err, status = respond_friend_request(u1_id, f"fed:{follower.id}", "reject")
        assert res is None
        assert status == 400
        assert "Cannot respond to an outgoing request you initiated; use cancel instead" in (err or "")


def test_respond_friend_request_allows_inbound_follow_acceptance(app, friend_users, remote_actor_setup):
    """Recipient can accept an inbound federated follow request."""
    u1_id, _ = friend_users
    _, actor_id, _, _ = remote_actor_setup

    with app.app_context():
        follower = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor_id,
            status=FollowStatus.PENDING,
        )
        db.session.add(follower)
        db.session.commit()

        # Inbound request (no outbound activity) can be accepted
        with patch("app.core.federation_dispatch.dispatch_accept_follow") as mock_dispatch:
            res, err, status = respond_friend_request(u1_id, f"fed:{follower.id}", "accept")
            assert status == 200
            assert err is None
            assert res is not None
            assert res["status"] == FollowStatus.ACCEPTED
            assert mock_dispatch.called is True

        # Verify follower status in DB is now ACCEPTED
        fol_db = db.session.get(FederationFollower, follower.id)
        assert fol_db is not None
        assert fol_db.status == FollowStatus.ACCEPTED


def test_remove_friend_cancels_outbound_federated_follow(app, friend_users, remote_actor_setup):
    """User can cancel their pending outbound federated follow via remove_friend."""
    u1_id, _ = friend_users
    _, actor_id, _, _ = remote_actor_setup

    with app.app_context():
        follower = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor_id,
            status=FollowStatus.PENDING,
        )
        db.session.add(follower)
        db.session.commit()

        success, err, status = remove_friend(u1_id, f"fed:{follower.id}")
        assert success is True
        assert status == 200
        assert err is None

        # Verify record deleted
        assert db.session.get(FederationFollower, follower.id) is None


def test_api_profile_friends_endpoints(client, app, friend_users, remote_actor_setup):
    """Integration: HTTP endpoints /api/profile/friends segregate directions and enforce self-response guard."""
    u1_id, _ = friend_users
    _, actor_id, actor_uri, inbox_url = remote_actor_setup

    with app.app_context():
        user = db.session.get(User, u1_id)
        token = generate_internal_jwt(user)

        follower = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor_id,
            status=FollowStatus.PENDING,
        )
        db.session.add(follower)
        actor_iri = canonical_actor_iri(u1_id)
        act = FederationActivity(
            actor_uri=actor_iri,
            activity_type="Follow",
            object_json={"type": "Follow", "actor": actor_iri, "object": actor_uri},
            target_uri=inbox_url,
            direction="outbound",
            status=ActivityStatus.QUEUED,
        )
        db.session.add(act)
        db.session.commit()
        fol_id = follower.id

    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/profile/friends -> outbound request listed in outgoing, not incoming
    get_res = client.get("/api/profile/friends", headers=headers)
    assert get_res.status_code == 200
    json_data = get_res.get_json()["data"]
    assert len(json_data["incoming"]) == 0
    assert len(json_data["outgoing"]) == 1
    assert json_data["outgoing"][0]["friendship_id"] == f"fed:{fol_id}"

    # 2. POST /api/profile/friends/fed:<id>/respond -> fails with 400
    respond_res = client.post(
        f"/api/profile/friends/fed:{fol_id}/respond",
        json={"action": "accept"},
        headers=headers,
    )
    assert respond_res.status_code == 400
    assert "Cannot respond to an outgoing request" in respond_res.get_json()["error"]

    # 3. DELETE /api/profile/friends/fed:<id> -> cancels with 200
    del_res = client.delete(f"/api/profile/friends/fed:{fol_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # 4. GET /api/profile/friends -> outgoing is now empty
    get_res2 = client.get("/api/profile/friends", headers=headers)
    assert len(get_res2.get_json()["data"]["outgoing"]) == 0


def test_send_friend_request_rejects_blocked_peer(app, friend_users):
    """Sending friend request to blocked instance returns 403."""
    u1_id, _ = friend_users
    with app.app_context():
        inst = FederationInstance(domain="blocked-instance.org", trust_level=TrustLevel.BLOCKED)
        db.session.add(inst)
        db.session.commit()

        res_data, err, code = send_friend_request(u1_id, "alice@blocked-instance.org")
        assert code == 403
        assert "blocked" in err.lower()


def test_send_friend_request_handles_double_at_identifier(app, friend_users):
    """Double-@ handle like user@email-domain@instance-domain parses domain from rightmost @."""
    u1_id, _ = friend_users
    with app.app_context():
        inst = FederationInstance(domain="peer.example.org", trust_level=TrustLevel.TRUSTED)
        db.session.add(inst)
        db.session.flush()

        actor = FederationActor(
            instance_id=inst.id,
            actor_uri="https://peer.example.org/api/federation/actor/u/alice",
            inbox_url="https://peer.example.org/api/federation/inbox",
            username="alice@iqoqo.cc",
        )
        db.session.add(actor)
        db.session.commit()

        with patch("app.core.federation_dispatch.dispatch_follow") as mock_dispatch:
            res_data, err, code = send_friend_request(u1_id, "alice@iqoqo.cc@peer.example.org")
            assert code == 201
            assert res_data is not None
            mock_dispatch.assert_called_once()


def test_send_friend_request_ensures_federation_consent_and_keys(app, friend_users):
    """Sending friend request to remote federated actor auto-provisions FederationConsent and actor keys."""
    u1_id, _ = friend_users
    with app.app_context():
        from sqlalchemy import select

        from app.db.federation import FederationConsent

        inst = FederationInstance(domain="peer2.example.org", trust_level=TrustLevel.TRUSTED)
        db.session.add(inst)
        db.session.flush()

        actor = FederationActor(
            instance_id=inst.id,
            actor_uri="https://peer2.example.org/api/federation/actor/u/bob",
            inbox_url="https://peer2.example.org/api/federation/inbox",
            username="bob",
        )
        db.session.add(actor)
        db.session.commit()

        consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == u1_id)).scalars().first()
        assert consent is None

        with patch("app.core.federation_dispatch.dispatch_follow") as mock_dispatch:
            res_data, err, code = send_friend_request(u1_id, "@bob@peer2.example.org")
            assert code == 201
            mock_dispatch.assert_called_once()

            consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == u1_id)).scalars().first()
            assert consent is not None
            assert consent.federated_profile is True
            u1 = db.session.get(User, u1_id)
            assert u1.federation_public_key is not None


def test_inbound_follow_scoped_to_target_user(app, friend_users):
    """Inbound Follow intended for User 2 cannot be adopted or self-accepted by User 1."""
    u1_id, u2_id = friend_users
    with app.app_context():
        inst = FederationInstance(domain="scoped-peer.example.org", trust_level=TrustLevel.TRUSTED)
        db.session.add(inst)
        db.session.flush()

        actor = FederationActor(
            instance_id=inst.id,
            actor_uri="https://scoped-peer.example.org/api/federation/actor/u/remote-actor",
            inbox_url="https://scoped-peer.example.org/api/federation/inbox",
            username="remote-actor",
        )
        db.session.add(actor)
        db.session.flush()

        # Inbound follow from remote actor targeting User 2
        inbound_act = FederationActivity(
            actor_uri=actor.actor_uri,
            activity_type="Follow",
            target_uri=f"https://local.test/api/federation/actor/u/{u2_id}",
            direction="inbound",
            status=ActivityStatus.DELIVERED,
            created_at=datetime.now(UTC),
        )
        db.session.add(inbound_act)

        # User 1 has an outgoing pending follow to remote actor
        fol1 = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor.id,
            status=FollowStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        db.session.add(fol1)
        outbound_act = FederationActivity(
            actor_uri=f"https://local.test/api/federation/actor/u/{u1_id}",
            activity_type="Follow",
            target_uri=actor.actor_uri,
            direction="outbound",
            status=ActivityStatus.DELIVERED,
            created_at=datetime.now(UTC),
        )
        db.session.add(outbound_act)
        db.session.commit()

        # User 1 listing friends should see fol1 as outgoing, not incoming!
        friends_u1 = list_friends(u1_id)
        assert len(friends_u1["incoming"]) == 0
        assert len(friends_u1["outgoing"]) == 1

        # User 1 attempting to accept should be rejected as self-accepting outgoing request
        _, err, code = respond_friend_request(u1_id, f"fed:{fol1.id}", "accept")
        assert code == 400
        assert "Cannot respond to an outgoing request" in (err or "")


def test_reject_and_remove_federated_friend_dispatches_activities(app, friend_users):
    """Rejecting inbound federated follow and removing active friendship dispatch Reject and Undo."""
    u1_id, _ = friend_users
    with app.app_context():
        inst = FederationInstance(domain="dispatch-peer.example.org", trust_level=TrustLevel.TRUSTED)
        db.session.add(inst)
        db.session.flush()

        actor = FederationActor(
            instance_id=inst.id,
            actor_uri="https://dispatch-peer.example.org/api/federation/actor/u/peer-user",
            inbox_url="https://dispatch-peer.example.org/api/federation/inbox",
            username="peer-user",
        )
        db.session.add(actor)
        db.session.flush()

        # 1. Inbound pending follow to be rejected
        fol_reject = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor.id,
            status=FollowStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        db.session.add(fol_reject)
        inbound_act = FederationActivity(
            actor_uri=actor.actor_uri,
            activity_type="Follow",
            target_uri=f"https://local.test/api/federation/actor/u/{u1_id}",
            direction="inbound",
            status=ActivityStatus.DELIVERED,
            created_at=datetime.now(UTC),
        )
        db.session.add(inbound_act)
        db.session.commit()

        with patch("app.core.federation_dispatch.dispatch_reject_follow") as mock_reject:
            res_data, err, code = respond_friend_request(u1_id, f"fed:{fol_reject.id}", "reject")
            assert code == 200
            mock_reject.assert_called_once()
            assert res_data["status"] == "rejected"

        # 2. Accepted follow to be removed
        fol_remove = FederationFollower(
            local_user_id=u1_id,
            remote_actor_id=actor.id,
            status=FollowStatus.ACCEPTED,
            created_at=datetime.now(UTC),
        )
        db.session.add(fol_remove)
        db.session.commit()

        with patch("app.core.federation_dispatch.dispatch_undo_follow") as mock_undo:
            success, err, code = remove_friend(u1_id, f"fed:{fol_remove.id}")
            assert code == 200
            assert success is True
            mock_undo.assert_called_once()


def test_send_friend_request_normalizes_domain_for_block_check(app, friend_users):
    """Domain port and scheme are cleaned before evaluating TrustLevel.BLOCKED."""
    u1_id, _ = friend_users
    with app.app_context():
        inst = FederationInstance(domain="blocked-domain.example.org", trust_level=TrustLevel.BLOCKED)
        db.session.add(inst)
        db.session.commit()

        _, err, code = send_friend_request(u1_id, "@charlie@https://blocked-domain.example.org:443/")
        assert code == 403
        assert "Cannot connect with user from blocked instance" in (err or "")
