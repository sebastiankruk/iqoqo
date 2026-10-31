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
"""Tests for ActivityPub inbox/outbox routes, Celery queue dispatch, and activity handlers."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from app.core import federation_keys
from app.core.federation_client import FederationClient
from app.core.federation_handlers import handle_activity
from app.core.federation_tasks import process_inbound_activity
from app.core.http_signatures import sign_request
from app.core.iri import canonical_actor_iri, get_federation_base_url
from app.core.tasks import submit_task
from app.db import db
from app.db.auth import User
from app.db.federation import (
    ActivityStatus,
    FederationActivity,
    FederationActor,
    FederationConsent,
    FederationFollower,
    FederationInstance,
    FollowStatus,
    TrustLevel,
)


@pytest.fixture
def rsa_keypair():
    """Generate ephemeral RSA-2048 keypair for signing tests."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_key, pub_pem


@pytest.fixture
def fed_user(app):
    """Create a user with explicit federation consent."""
    with app.app_context():
        user = User(
            email="inbox_tester@iqoqo.local",
            public_username="inboxtester",
            display_name="Inbox Tester",
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.flush()

        consent = FederationConsent(
            user_id=user.id,
            federated_profile=True,
            federated_collection=True,
        )
        db.session.add(consent)
        db.session.commit()
        return {"id": str(user.id), "username": user.public_username}


@pytest.fixture
def remote_peer_instance(app):
    """Seed a remote trusted instance and actor."""
    with app.app_context():
        instance = FederationInstance(
            domain="remote-peer.example.org",
            trust_level=TrustLevel.TRUSTED,
        )
        db.session.add(instance)
        db.session.flush()

        actor = FederationActor(
            actor_uri="https://remote-peer.example.org/users/bob",
            inbox_url="https://remote-peer.example.org/users/bob/inbox",
            instance_id=instance.id,
        )
        db.session.add(actor)
        db.session.commit()
        return {
            "domain": instance.domain,
            "actor_uri": actor.actor_uri,
            "instance_id": instance.id,
            "actor_id": actor.id,
        }


class TestInboxEndpoint:
    """Test suite for ActivityPub inbox endpoints (actor and shared)."""

    def test_inbox_rejects_missing_signature(self, client, app, fed_user):
        """Unsigned inbox requests return 401."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True

        resp = client.post(
            f"/api/federation/actor/{fed_user['username']}/inbox",
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )
        assert resp.status_code == 401
        assert "Invalid signature" in resp.get_json()["error"]

    def test_inbox_rejects_oversized_payload(self, client, app, fed_user):
        """Payloads exceeding 100KB return 413."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True

        oversized_data = b"x" * (101 * 1024)
        resp = client.post(
            f"/api/federation/actor/{fed_user['username']}/inbox",
            data=oversized_data,
            headers={"Content-Type": "application/activity+json"},
        )
        assert resp.status_code == 413
        assert "100KB" in resp.get_json()["error"]

    def test_inbox_rejects_blocked_instance(self, client, app, fed_user, rsa_keypair):
        """Inbound activity from a BLOCKED instance returns 403."""
        priv_key, pub_pem = rsa_keypair
        blocked_actor = "https://blocked-spammer.evil/actor"

        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            instance = FederationInstance(domain="blocked-spammer.evil", trust_level=TrustLevel.BLOCKED)
            db.session.add(instance)
            db.session.commit()

        body = json.dumps({"type": "Follow", "actor": blocked_actor, "object": f"https://iqoqo.local/u/{fed_user['username']}"}).encode(
            "utf-8"
        )
        headers = sign_request(
            method="POST",
            url=f"http://localhost/api/federation/actor/{fed_user['username']}/inbox",
            body=body,
            key_id=f"{blocked_actor}#main-key",
            private_key=priv_key,
        )
        headers["Content-Type"] = "application/activity+json"

        mock_doc = {"id": blocked_actor, "publicKey": {"id": f"{blocked_actor}#main-key", "owner": blocked_actor, "publicKeyPem": pub_pem}}
        with patch.object(FederationClient, "fetch_actor", return_value=mock_doc):
            resp = client.post(
                f"/api/federation/actor/{fed_user['username']}/inbox",
                data=body,
                headers=headers,
            )
        assert resp.status_code == 403
        assert "blocked" in resp.get_json()["error"].lower()

    def test_inbox_rejects_actor_mismatch(self, client, app, fed_user, rsa_keypair):
        """Payload actor differing from verified signature actor returns 403."""
        priv_key, pub_pem = rsa_keypair
        verified_actor = "https://verified.example.org/users/alice"
        impersonated_actor = "https://verified.example.org/users/bob"

        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True

        body = json.dumps({"type": "Follow", "actor": impersonated_actor}).encode("utf-8")
        headers = sign_request(
            method="POST",
            url="http://localhost/api/federation/inbox",
            body=body,
            key_id=f"{verified_actor}#main-key",
            private_key=priv_key,
        )
        headers["Content-Type"] = "application/activity+json"

        mock_doc = {
            "id": verified_actor,
            "publicKey": {"id": f"{verified_actor}#main-key", "owner": verified_actor, "publicKeyPem": pub_pem},
        }
        with patch.object(FederationClient, "fetch_actor", return_value=mock_doc):
            resp = client.post("/api/federation/inbox", data=body, headers=headers)
        assert resp.status_code == 401
        assert "does not match payload actor" in resp.get_json()["error"]

    def test_inbox_accepts_valid_signed_activity_and_dispatches_task(self, client, app, fed_user, remote_peer_instance, rsa_keypair):
        """Valid signed activity returns 202 and queues Celery processing."""
        priv_key, pub_pem = rsa_keypair
        actor_uri = remote_peer_instance["actor_uri"]

        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            base_url = get_federation_base_url()
            target_obj = canonical_actor_iri(uuid.UUID(fed_user["id"]), base_url)

        activity_id = f"https://remote-peer.example.org/activities/{uuid.uuid4()}"
        body = json.dumps(
            {
                "id": activity_id,
                "type": "Follow",
                "actor": actor_uri,
                "object": target_obj,
            }
        ).encode("utf-8")

        headers = sign_request(
            method="POST",
            url=f"http://localhost/api/federation/actor/u/{fed_user['id']}/inbox",
            body=body,
            key_id=f"{actor_uri}#main-key",
            private_key=priv_key,
        )
        headers["Content-Type"] = "application/activity+json"

        mock_doc = {"id": actor_uri, "publicKey": {"id": f"{actor_uri}#main-key", "owner": actor_uri, "publicKeyPem": pub_pem}}
        with patch.object(FederationClient, "fetch_actor", return_value=mock_doc):
            with patch("app.core.tasks.submit_task") as mock_submit:
                mock_submit.return_value = "celery-task-12345"
                resp = client.post(
                    f"/api/federation/actor/u/{fed_user['id']}/inbox",
                    data=body,
                    headers=headers,
                )

        assert resp.status_code == 202
        data = resp.get_json()
        assert data["status"] == "accepted"
        assert data["id"] == activity_id
        mock_submit.assert_called_once()
        assert mock_submit.call_args[1].get("queue") == "federation"


class TestOutboxEndpoint:
    """Test suite for ActivityPub outbox endpoints."""

    def test_outbox_unconsenting_user_returns_404(self, client, app):
        """Outbox returns 404 if user has not enabled federated_profile."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            user = User(email="private_outbox@test.cc", public_username="privateoutbox")
            user.set_password("Password123!")
            db.session.add(user)
            db.session.commit()
            uid = str(user.id)

        resp = client.get(f"/api/federation/actor/u/{uid}/outbox")
        assert resp.status_code == 404

    def test_outbox_returns_ordered_collection_and_page(self, client, app, fed_user):
        """Outbox returns OrderedCollection for root and OrderedCollectionPage for ?page=1."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            base_url = get_federation_base_url()
            actor_iri = canonical_actor_iri(uuid.UUID(fed_user["id"]), base_url)

            # Seed 2 delivered outbound activities
            act1 = FederationActivity(
                actor_uri=actor_iri,
                activity_type="Create",
                object_json={"type": "Create", "content": "First item"},
                direction="outbound",
                status=ActivityStatus.DELIVERED,
            )
            act2 = FederationActivity(
                actor_uri=actor_iri,
                activity_type="Update",
                object_json={"type": "Update", "content": "Second item"},
                direction="outbound",
                status=ActivityStatus.DELIVERED,
            )
            db.session.add_all([act1, act2])
            db.session.commit()

        # Root outbox query
        resp = client.get(f"/api/federation/actor/{fed_user['username']}/outbox")
        assert resp.status_code == 200
        assert "application/activity+json" in resp.content_type
        data = resp.get_json()
        assert data["type"] == "OrderedCollection"
        assert data["totalItems"] == 2
        assert "outbox?page=1" in data["first"]

        # Paginated outbox query
        page_resp = client.get(f"/api/federation/actor/u/{fed_user['id']}/outbox?page=1")
        assert page_resp.status_code == 200
        page_data = page_resp.get_json()
        assert page_data["type"] == "OrderedCollectionPage"
        assert len(page_data["orderedItems"]) == 2
        assert page_data["orderedItems"][0]["type"] in ("Create", "Update")

    def test_outbox_excludes_failed_and_inbound_activities(self, client, app, fed_user):
        """Outbox only exposes outbound activities with DELIVERED status."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            base_url = get_federation_base_url()
            actor_iri = canonical_actor_iri(uuid.UUID(fed_user["id"]), base_url)

            delivered_act = FederationActivity(
                actor_uri=actor_iri,
                activity_type="Create",
                object_json={"type": "Create", "content": "Delivered item"},
                direction="outbound",
                status=ActivityStatus.DELIVERED,
            )
            failed_act = FederationActivity(
                actor_uri=actor_iri,
                activity_type="Create",
                object_json={"type": "Create", "content": "Failed item"},
                direction="outbound",
                status=ActivityStatus.FAILED,
            )
            inbound_act = FederationActivity(
                actor_uri=actor_iri,
                activity_type="Follow",
                object_json={"type": "Follow"},
                direction="inbound",
                status=ActivityStatus.DELIVERED,
            )
            db.session.add_all([delivered_act, failed_act, inbound_act])
            db.session.commit()

        resp = client.get(f"/api/federation/actor/u/{fed_user['id']}/outbox")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["totalItems"] == 1

        page_resp = client.get(f"/api/federation/actor/u/{fed_user['id']}/outbox?page=1")
        assert page_resp.status_code == 200
        page_data = page_resp.get_json()
        assert len(page_data["orderedItems"]) == 1
        assert page_data["orderedItems"][0]["content"] == "Delivered item"

    def test_followers_and_following_collections(self, client, app, fed_user, remote_peer_instance):
        """Followers and following collections return valid OrderedCollection structures."""
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            follower = FederationFollower(
                local_user_id=uuid.UUID(fed_user["id"]),
                remote_actor_id=remote_peer_instance["actor_id"],
                status=FollowStatus.ACCEPTED,
            )
            db.session.add(follower)
            db.session.commit()

        followers_resp = client.get(f"/api/federation/actor/{fed_user['username']}/followers")
        assert followers_resp.status_code == 200
        f_data = followers_resp.get_json()
        assert f_data["type"] == "OrderedCollection"
        assert f_data["totalItems"] == 1

        following_resp = client.get(f"/api/federation/actor/u/{fed_user['id']}/following")
        assert following_resp.status_code == 200
        ing_data = following_resp.get_json()
        assert ing_data["type"] == "OrderedCollection"
        assert ing_data["totalItems"] == 0


class TestActivityHandlers:
    """Test suite for individual ActivityStreams activity handlers."""

    def test_handle_follow_and_undo_follow(self, app, fed_user, remote_peer_instance):
        """Follow creates relationship, Undo removes it."""
        with app.app_context():
            consent = (
                db.session.execute(select(FederationConsent).where(FederationConsent.user_id == uuid.UUID(fed_user["id"])))
                .scalars()
                .first()
            )
            if consent:
                consent.auto_accept_follows = True
                db.session.commit()

            base_url = get_federation_base_url()
            target_iri = canonical_actor_iri(uuid.UUID(fed_user["id"]), base_url)

            follow_activity = {
                "type": "Follow",
                "actor": remote_peer_instance["actor_uri"],
                "object": target_iri,
            }
            handled = handle_activity(follow_activity)
            assert handled is True

            # Verify follower record exists
            follower = (
                db.session.execute(
                    select(FederationFollower).where(
                        FederationFollower.local_user_id == uuid.UUID(fed_user["id"]),
                        FederationFollower.remote_actor_id == remote_peer_instance["actor_id"],
                    )
                )
                .scalars()
                .first()
            )
            assert follower is not None
            assert follower.status == FollowStatus.ACCEPTED

            # Execute Undo(Follow)
            undo_activity = {
                "type": "Undo",
                "actor": remote_peer_instance["actor_uri"],
                "object": follow_activity,
            }
            undo_handled = handle_activity(undo_activity)
            assert undo_handled is True

            # Verify follower record removed
            follower_after = (
                db.session.execute(
                    select(FederationFollower).where(
                        FederationFollower.local_user_id == uuid.UUID(fed_user["id"]),
                        FederationFollower.remote_actor_id == remote_peer_instance["actor_id"],
                    )
                )
                .scalars()
                .first()
            )
            assert follower_after is None

    def test_handle_follow_defaults_to_pending_when_unset_or_disabled(self, app, fed_user, remote_peer_instance):
        """Inbound Follow must default to PENDING (opt-in) without sending Accept unless explicitly enabled."""
        with app.app_context():
            # Ensure setting is unset in InstanceSettings and default False is evaluated
            from app.db.settings import InstanceSettings

            db.session.execute(db.delete(InstanceSettings).where(InstanceSettings.key == "FEDERATION_AUTO_ACCEPT_FOLLOWS"))
            # Make the remote instance UNTRUSTED so trusted bypass does not auto-accept
            inst = db.session.get(FederationInstance, remote_peer_instance["instance_id"])
            inst.trust_level = TrustLevel.UNTRUSTED
            db.session.commit()
            if "FEDERATION_AUTO_ACCEPT_FOLLOWS" in app.config:
                del app.config["FEDERATION_AUTO_ACCEPT_FOLLOWS"]

            base_url = get_federation_base_url()
            target_iri = canonical_actor_iri(uuid.UUID(fed_user["id"]), base_url)

            follow_activity = {
                "type": "Follow",
                "actor": remote_peer_instance["actor_uri"],
                "object": target_iri,
            }
            with patch("app.core.tasks.submit_task") as mock_submit:
                handled = handle_activity(follow_activity)
                assert handled is True
                # Must NOT queue Celery delivery of Accept when auto-accept is disabled
                mock_submit.assert_not_called()

            # Verify follower record exists in PENDING status
            follower = (
                db.session.execute(
                    select(FederationFollower).where(
                        FederationFollower.local_user_id == uuid.UUID(fed_user["id"]),
                        FederationFollower.remote_actor_id == remote_peer_instance["actor_id"],
                    )
                )
                .scalars()
                .first()
            )
            assert follower is not None
            assert follower.status == FollowStatus.PENDING

            # Verify notification was created with deep-link and actionable payload
            from app.db.social import Notification

            notif = (
                db.session.execute(
                    select(Notification)
                    .where(
                        Notification.user_id == uuid.UUID(fed_user["id"]),
                        Notification.type == "follow_request",
                    )
                    .order_by(Notification.created_at.desc())
                )
                .scalars()
                .first()
            )
            assert notif is not None
            assert notif.target_iri == "/profile?tab=incoming#friends"
            assert notif.payload_json.get("friendship_id") == f"fed:{follower.id}"
            assert notif.payload_json.get("target_iri") == "/profile?tab=incoming#friends"
            assert "New friend request from" in notif.payload_json.get("message", "")

    def test_handle_accept_and_reject(self, app, fed_user, remote_peer_instance):
        """Accept sets status to accepted, Reject sets status to rejected."""
        with app.app_context():
            base_url = get_federation_base_url()
            target_iri = canonical_actor_iri(uuid.UUID(fed_user["id"]), base_url)

            # Create initial pending follower
            follower = FederationFollower(
                local_user_id=uuid.UUID(fed_user["id"]),
                remote_actor_id=remote_peer_instance["actor_id"],
                status=FollowStatus.PENDING,
            )
            db.session.add(follower)
            db.session.commit()

            accept_activity = {
                "type": "Accept",
                "actor": remote_peer_instance["actor_uri"],
                "object": {
                    "type": "Follow",
                    "actor": target_iri,
                    "object": remote_peer_instance["actor_uri"],
                },
            }
            assert handle_activity(accept_activity) is True
            db.session.refresh(follower)
            assert follower.status == FollowStatus.ACCEPTED

            reject_activity = {
                "type": "Reject",
                "actor": remote_peer_instance["actor_uri"],
                "object": {
                    "type": "Follow",
                    "actor": target_iri,
                    "object": remote_peer_instance["actor_uri"],
                },
            }
            assert handle_activity(reject_activity) is True
            db.session.refresh(follower)
            assert follower.status == FollowStatus.REJECTED

    def test_handle_delete_remote_actor(self, app, remote_peer_instance):
        """Delete activity referencing remote actor URI cleans up actor and followers."""
        with app.app_context():
            del_activity = {
                "type": "Delete",
                "actor": remote_peer_instance["actor_uri"],
                "object": remote_peer_instance["actor_uri"],
            }
            assert handle_activity(del_activity) is True
            actor = db.session.get(FederationActor, remote_peer_instance["actor_id"])
            assert actor is None

    def test_handle_delete_spoofed_remote_actor_rejected(self, app, remote_peer_instance):
        """Delete activity where actor_uri != object_uri is rejected."""
        with app.app_context():
            del_activity = {
                "type": "Delete",
                "actor": "https://malicious-actor.example.org/users/eve",
                "object": remote_peer_instance["actor_uri"],
            }
            assert handle_activity(del_activity) is False
            actor = db.session.get(FederationActor, remote_peer_instance["actor_id"])
            assert actor is not None

    def test_handle_accept_spoofed_follow_rejected(self, app, remote_peer_instance):
        """Accept activity with mismatched followed object is rejected."""
        with app.app_context():
            spoofed_accept = {
                "type": "Accept",
                "actor": remote_peer_instance["actor_uri"],
                "object": {
                    "type": "Follow",
                    "actor": "https://other.example.org/users/carol",
                    "object": "https://target.example.org/users/victim",
                },
            }
            assert handle_activity(spoofed_accept) is False

    def test_receive_inbox_chunked_oversized_payload_rejected(self, client):
        """Inbound inbox POST exceeding 100KB is rejected with 413."""
        large_body = b" " * 105000
        res = client.post(
            "/api/federation/inbox",
            data=large_body,
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 413

    def test_receive_inbox_per_actor_unconsented_returns_404(self, client, app):
        """Inbound per-actor inbox returns 404 if targeted actor does not exist or has not consented."""
        res = client.post(
            f"/api/federation/actor/u/{uuid.uuid4()}/inbox",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 404

    def test_handle_unknown_activity_type(self, app):
        """Unknown activity type logs warning and returns False without raising."""
        with app.app_context():
            assert handle_activity({"type": "NonExistentActivityType"}) is False

    def test_receive_inbox_blocked_instance_with_port_rejected(self, client, app):
        """Inbound inbox blocks peer registered with non-standard port."""
        with app.app_context():
            blocked_inst = FederationInstance(
                domain="evil.example:8443",
                trust_level=TrustLevel.BLOCKED,
            )
            db.session.add(blocked_inst)
            db.session.commit()

        with patch("app.api.federation.verify_request", return_value="https://evil.example:8443/u/attacker"):
            res = client.post(
                "/api/federation/inbox",
                json={"type": "Create", "actor": "https://evil.example:8443/u/attacker"},
                headers={"Signature": "keyId=...,signature=..."},
            )
            assert res.status_code == 403
            assert "blocked" in res.get_json()["error"].lower()

    def test_handle_follow_strict_opt_in_and_state_preservation(self, app, fed_user, remote_peer_instance):
        """handle_follow requires both auto_accept and TRUSTED, and preserves REJECTED/ACCEPTED."""
        with app.app_context():
            user = db.session.get(User, uuid.UUID(fed_user["id"]))
            actor_uri = remote_peer_instance["actor_uri"]
            inst = db.session.get(FederationInstance, remote_peer_instance["instance_id"])

            # 1. auto_accept_follows=False, trust_level=TRUSTED -> must remain PENDING
            inst.trust_level = TrustLevel.TRUSTED
            consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
            if consent:
                consent.auto_accept_follows = False
            db.session.commit()
            assert (
                handle_activity(
                    {
                        "type": "Follow",
                        "actor": actor_uri,
                        "object": canonical_actor_iri(user.id),
                    }
                )
                is True
            )

            f = (
                db.session.execute(
                    select(FederationFollower).where(
                        FederationFollower.local_user_id == user.id,
                        FederationFollower.remote_actor_id == remote_peer_instance["actor_id"],
                    )
                )
                .scalars()
                .first()
            )
            assert f is not None
            assert f.status == FollowStatus.PENDING

            # 2. Existing is REJECTED -> duplicate Follow stays REJECTED
            f.status = FollowStatus.REJECTED
            if consent:
                consent.auto_accept_follows = True
            db.session.commit()
            assert (
                handle_activity(
                    {
                        "type": "Follow",
                        "actor": actor_uri,
                        "object": canonical_actor_iri(user.id),
                    }
                )
                is True
            )
            db.session.refresh(f)
            assert f.status == FollowStatus.REJECTED

            # 3. Existing is ACCEPTED -> duplicate Follow stays ACCEPTED
            f.status = FollowStatus.ACCEPTED
            if consent:
                consent.auto_accept_follows = False
            db.session.commit()
            with patch("app.core.federation_handlers._accept_follow") as mock_accept:
                assert (
                    handle_activity(
                        {
                            "type": "Follow",
                            "actor": actor_uri,
                            "object": canonical_actor_iri(user.id),
                        }
                    )
                    is True
                )
                mock_accept.assert_called_once()
            db.session.refresh(f)
            assert f.status == FollowStatus.ACCEPTED

    def test_handle_create_cross_port_isolation(self, app):
        """Cross-port services do not inherit TrustLevel.TRUSTED from portless domain."""
        with app.app_context():
            # trusted on port 443
            inst = FederationInstance(domain="trusted.example", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.commit()

            # activity from port 8443 (not registered, or untrusted)
            act = {
                "type": "Create",
                "actor": "https://trusted.example:8443/u/rogue",
                "object": {"type": "Document", "title": "Untrusted Book"},
            }
            # handle_activity returns False because trusted.example:8443 is untrusted
            assert handle_activity(act) is False


class TestCeleryTaskAndQueueRouting:
    """Verify Celery task execution and queue routing."""

    def test_submit_task_routes_to_federation_queue(self):
        """submit_task with federation callable automatically routes to federation queue."""
        with patch("app.core.tasks._task_wrapper.apply_async") as mock_apply:
            mock_apply.return_value = MagicMock(id="task-uuid-999")
            tid = submit_task(process_inbound_activity, "act-id", {"type": "Follow"})
            assert tid == "task-uuid-999"
            mock_apply.assert_called_once()
            assert mock_apply.call_args[1].get("queue") == "federation"

    def test_submit_task_catches_runtime_error_and_returns_none(self):
        """submit_task catches Celery RuntimeError and returns None for graceful sync fallback."""
        with patch("app.core.tasks._task_wrapper.apply_async", side_effect=RuntimeError("Retry limit exceeded while trying to reconnect")):
            tid = submit_task(process_inbound_activity, "act-id", {"type": "Follow"})
            assert tid is None
