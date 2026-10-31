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
#
"""Orthogonal federation combinatorial matrix test suite (OpenSpec C92).

Verifies the 6-dimensional state space:
  D1: Instance A trust toward B (T_{A->B} in {unregistered, untrusted, trusted, blocked})
  D2: Instance B trust toward A (T_{B->A} in {unregistered, untrusted, trusted, blocked})
  D3: User Consent Vector (C_u in {False, True}^2 for federated_profile x federated_collection)
  D4: Follow Auto-Approval (auto_accept_follows in {False, True} x peer trust)
  D5: Directional Social State (none, pending_outgoing, pending_incoming, accepted, rejected/unfollowed)
  D6: Resource Visibility (private, friends_only, shared, public)
"""

from __future__ import annotations

import itertools
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import or_, select

from app.api.auth import generate_internal_jwt
from app.api.federation import _get_domain
from app.core import federation_handlers, federation_keys, federation_sync, friend_service
from app.core.federation_keys import generate_actor_keypair, get_actor_private_key, get_actor_public_key
from app.core.friend_service import is_friend_of, list_friends, respond_friend_request, send_friend_request
from app.core.http_signatures import sign_request, verify_request
from app.core.iri import canonical_actor_iri, get_federation_base_url
from app.core.item_access import is_item_publicly_visible
from app.db import db
from app.db.auth import User, UserFriendship
from app.db.core import Expression, Item, Manifestation, Work
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
def matrix_rsa_keypair() -> tuple[rsa.RSAPrivateKey, str]:
    """Generate ephemeral RSA-2048 keypair."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = (
        priv.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return priv, pub_pem


@pytest.fixture
def matrix_users(app):
    """Create User A on Alpha and User B on Beta."""
    with app.app_context():
        user_a = User(
            id=uuid.uuid4(),
            email=f"alpha_{uuid.uuid4().hex[:6]}@alpha.test",
            public_username=f"alpha_{uuid.uuid4().hex[:6]}",
            display_name="User Alpha",
            visibility="public",
            default_item_visibility="public",
        )
        user_a.set_password("AlphaPass123!")

        user_b = User(
            id=uuid.uuid4(),
            email=f"beta_{uuid.uuid4().hex[:6]}@beta.test",
            public_username=f"beta_{uuid.uuid4().hex[:6]}",
            display_name="User Beta",
            visibility="public",
            default_item_visibility="public",
        )
        user_b.set_password("BetaPass123!")

        db.session.add_all([user_a, user_b])
        db.session.commit()
        return user_a.id, user_b.id


# ===========================================================================
# MATRIX 1: 4x4 = 16 Bilateral & Asymmetric Peering Topologies
# ===========================================================================
TRUST_LEVELS = ["unregistered", "untrusted", "trusted", "blocked"]


class TestMatrix1PeeringTopologies:
    """Matrix 1: 4x4 Cartesian product of instance trust states T_{A->B} x T_{B->A}."""

    @pytest.mark.parametrize(
        "trust_a_to_b,trust_b_to_a",
        list(itertools.product(TRUST_LEVELS, repeat=2)),
    )
    def test_matrix_1_peering_topologies(
        self,
        app,
        matrix_users,
        trust_a_to_b: str,
        trust_b_to_a: str,
    ) -> None:
        """Verify behavior across all 16 bilateral and asymmetric peering topologies."""
        user_a_id, user_b_id = matrix_users
        domain_b = f"beta-{uuid.uuid4().hex[:6]}.library"

        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            user_a = db.session.get(User, user_a_id)
            user_b = db.session.get(User, user_b_id)

            # Setup instance record on Alpha representing Beta
            instance_b = None
            actor_b = None
            if trust_a_to_b != "unregistered":
                instance_b = FederationInstance(
                    domain=domain_b,
                    software_name="iqoqo",
                    trust_level=trust_a_to_b,
                )
                db.session.add(instance_b)
                db.session.flush()

                actor_b = FederationActor(
                    actor_uri=f"https://{domain_b}/ap/users/{user_b.public_username}",
                    username=user_b.public_username,
                    inbox_url=f"https://{domain_b}/ap/users/{user_b.public_username}/inbox",
                    instance_id=instance_b.id,
                )
                db.session.add(actor_b)
                db.session.commit()

            # 1. Test Outbound Friend Request gate (A -> B)
            target_handle = f"@{user_b.public_username}@{domain_b}"

            mock_unregistered_actor = None
            if trust_a_to_b == "unregistered":
                # Create a temporary unregistered instance and actor for mock return
                unregistered_inst = FederationInstance(
                    domain=domain_b,
                    software_name="iqoqo",
                    trust_level=TrustLevel.UNTRUSTED,
                )
                db.session.add(unregistered_inst)
                db.session.flush()
                mock_unregistered_actor = FederationActor(
                    actor_uri=f"https://{domain_b}/ap/users/{user_b.public_username}",
                    username=user_b.public_username,
                    inbox_url=f"https://{domain_b}/ap/users/{user_b.public_username}/inbox",
                    instance_id=unregistered_inst.id,
                )
                db.session.add(mock_unregistered_actor)
                db.session.commit()

            with patch("app.core.federation_handlers._get_or_create_actor") as mock_get_actor:
                if mock_unregistered_actor:
                    mock_get_actor.return_value = mock_unregistered_actor
                with patch("app.core.federation_dispatch.dispatch_follow"):
                    result, err, status = send_friend_request(user_a.id, target_handle)

            if trust_a_to_b == "blocked":
                # Outbound initiation to blocked peer MUST be rejected locally with 403
                assert status == 403
                assert "blocked" in (err or "").lower()
            else:
                # Unregistered, untrusted, or trusted peers permit outbound request creation
                assert status in (200, 201)
                assert err is None

            # 2. Test Inbound Ingest / FRBR Metadata Sync disposition (B -> A)
            test_work = Work(title="Matrix Bibliographic Entity")
            test_expr = Expression(work=test_work, language="en", content_type="text")
            test_manif = Manifestation(
                expression=test_expr,
                isbn13=f"978{uuid.uuid4().int % 10000000000:010d}",
            )
            db.session.add_all([test_work, test_expr, test_manif])
            db.session.commit()

            remote_metadata = {
                "isbn13": test_manif.isbn13,
                "page_count": 345,
                "publisher": "Orthogonal Press",
            }

            sync_trust = trust_b_to_a if trust_b_to_a != "unregistered" else TrustLevel.UNTRUSTED
            sync_result = federation_sync.sync_manifestation(
                manifestation=test_manif,
                remote_data=remote_metadata,
                domain=domain_b,
                trust_level=sync_trust,
            )

            if trust_b_to_a == "blocked":
                assert sync_result["status"] == "ignored"
            elif trust_b_to_a in ("unregistered", "untrusted"):
                assert sync_result["status"] in ("queued_for_review", "already_queued")
            elif trust_b_to_a == "trusted":
                assert sync_result["status"] == "merged"
                assert test_manif.publisher == "Orthogonal Press"


# ===========================================================================
# MATRIX 2: 4x2x3 = 24 Consent x Auto-Accept x Peer Trust Intersections
# ===========================================================================
AUTO_ACCEPTS = [False, True]
PEER_TRUST_LEVELS = [TrustLevel.UNTRUSTED, TrustLevel.TRUSTED, TrustLevel.BLOCKED]


class TestMatrix2ConsentAutoAcceptTrust:
    """Matrix 2: 24 combinations of recipient consent, follow auto-accept, and peer trust."""

    @pytest.mark.parametrize(
        "fed_profile,fed_collection,auto_accept,peer_trust",
        list(
            itertools.product(
                [False, True],
                [False, True],
                AUTO_ACCEPTS,
                PEER_TRUST_LEVELS,
            )
        ),
    )
    def test_matrix_2_recipient_consent_and_auto_accept(
        self,
        app,
        matrix_users,
        fed_profile: bool,
        fed_collection: bool,
        auto_accept: bool,
        peer_trust: str,
    ) -> None:
        """Verify recipient follow handling across consent, auto-accept, and trust levels."""
        user_a_id, user_b_id = matrix_users
        domain_peer = f"peer-{uuid.uuid4().hex[:6]}.library"

        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            user_b = db.session.get(User, user_b_id)

            # Configure recipient consent
            consent = FederationConsent(
                user_id=user_b.id,
                federated_profile=fed_profile,
                federated_collection=fed_collection,
                auto_accept_follows=auto_accept,
            )
            db.session.merge(consent)

            # Configure sender peer instance
            instance = FederationInstance(
                domain=domain_peer,
                software_name="iqoqo",
                trust_level=peer_trust,
            )
            db.session.add(instance)
            db.session.flush()

            remote_actor_uri = f"https://{domain_peer}/ap/users/remote_requester"
            remote_actor = FederationActor(
                actor_uri=remote_actor_uri,
                username="remote_requester",
                inbox_url=f"https://{domain_peer}/ap/users/remote_requester/inbox",
                instance_id=instance.id,
            )
            db.session.add(remote_actor)
            db.session.commit()

            follow_activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://{domain_peer}/activities/{uuid.uuid4()}",
                "type": "Follow",
                "actor": remote_actor_uri,
                "object": canonical_actor_iri(user_b.id, get_federation_base_url()),
            }

            with patch("app.core.federation_handlers._accept_follow") as mock_accept:
                handled = federation_handlers.handle_follow(follow_activity)

            follower = (
                db.session.execute(
                    select(FederationFollower).where(
                        FederationFollower.local_user_id == user_b.id,
                        FederationFollower.remote_actor_id == remote_actor.id,
                    )
                )
                .scalars()
                .first()
            )

            if not fed_profile:
                # If recipient does not consent to federated profile, follow MUST be rejected
                assert handled is False
                assert follower is None
            elif peer_trust == TrustLevel.BLOCKED:
                # If peer is blocked, follow activity is rejected
                assert handled is False
                assert follower is None
            elif auto_accept and peer_trust == TrustLevel.TRUSTED:
                # ONLY auto-accepts when BOTH auto_accept=True AND peer is TRUSTED
                assert handled is True
                assert follower is not None
                assert follower.status == FollowStatus.ACCEPTED
                mock_accept.assert_called_once()
            else:
                # Otherwise placed into PENDING state for manual review
                assert handled is True
                assert follower is not None
                assert follower.status == FollowStatus.PENDING
                mock_accept.assert_not_called()


# ===========================================================================
# MATRIX 3: 5x4x2 = 40 Social State x Item Visibility x Collection Consent
# ===========================================================================
SOCIAL_STATES = ["none", "pending_outgoing", "pending_incoming", "accepted", "rejected_or_unfollowed"]
VISIBILITY_TIERS = ["private", "friends_only", "shared", "public"]
COLLECTION_CONSENTS = [False, True]


class TestMatrix3SocialVisibilityConsent:
    """Matrix 3: 40 combinations of social relationship, item visibility, and collection consent."""

    @pytest.mark.parametrize(
        "social_state,visibility,collection_consent",
        list(itertools.product(SOCIAL_STATES, VISIBILITY_TIERS, COLLECTION_CONSENTS)),
    )
    def test_matrix_3_access_and_visibility_gating(
        self,
        app,
        matrix_users,
        social_state: str,
        visibility: str,
        collection_consent: bool,
    ) -> None:
        """Verify item visibility, is_friend_of(), and public visibility gating."""
        user_a_id, user_b_id = matrix_users

        with app.app_context():
            user_a = db.session.get(User, user_a_id)
            user_b = db.session.get(User, user_b_id)

            # Configure Owner B's federation consent
            consent_b = FederationConsent(
                user_id=user_b.id,
                federated_profile=True,
                federated_collection=collection_consent,
            )
            db.session.merge(consent_b)

            # Establish Social State between A and B
            if social_state == "accepted":
                friendship = UserFriendship(
                    requester_id=user_a.id,
                    addressee_id=user_b.id,
                    status="accepted",
                )
                db.session.merge(friendship)
            elif social_state == "pending_outgoing":
                friendship = UserFriendship(
                    requester_id=user_a.id,
                    addressee_id=user_b.id,
                    status="pending",
                )
                db.session.merge(friendship)
            elif social_state == "pending_incoming":
                friendship = UserFriendship(
                    requester_id=user_b.id,
                    addressee_id=user_a.id,
                    status="pending",
                )
                db.session.merge(friendship)
            elif social_state == "rejected_or_unfollowed":
                friendship = UserFriendship(
                    requester_id=user_a.id,
                    addressee_id=user_b.id,
                    status="rejected",
                )
                db.session.merge(friendship)

            # Create an item owned by User B
            work = Work(title=f"Item Work {uuid.uuid4().hex[:6]}")
            expr = Expression(work=work, language="en", content_type="text")
            manif = Manifestation(expression=expr, isbn13=f"978{uuid.uuid4().int % 10000000000:010d}")
            item = Item(
                manifestation=manif,
                owner_id=user_b.id,
                visibility=visibility,
                is_hidden=(visibility != "public"),
                collection_status="available",
            )
            db.session.add_all([work, expr, manif, item])
            db.session.commit()

            # 1. Check is_friend_of(Viewer A, Owner B)
            is_friend = is_friend_of(user_a.id, user_b.id)
            if social_state == "accepted":
                assert is_friend is True
            else:
                assert is_friend is False

            # 2. Check public federation visibility (SPARQL snapshot & public RDF)
            is_publicly_visible = is_item_publicly_visible(item)
            if visibility in ("private", "friends_only", "shared") or not collection_consent:
                assert is_publicly_visible is False
            else:
                # public with collection_consent=True
                assert is_publicly_visible is True


# ===========================================================================
# MATRIX 4: 12 Directional, Cryptographic & Constraint Lifecycle Transitions
# ===========================================================================
class TestMatrix4LifecycleAndEdgeCases:
    """Matrix 4: 12 edge cases across directionality, cryptography, and DB constraints."""

    def test_case_01_outbound_follow_auto_provisions_consent_and_keys(self, app, matrix_users) -> None:
        """Requester with no prior consent auto-provisions federated_profile=True and RSA keys."""
        user_a_id, user_b_id = matrix_users
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            user_a = db.session.get(User, user_a_id)

            inst = FederationInstance(domain="peer.example", software_name="iqoqo", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri="https://peer.example/users/bob",
                username="bob",
                inbox_url="https://peer.example/users/bob/inbox",
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.commit()

            with patch("app.core.federation_dispatch.dispatch_follow"):
                send_friend_request(user_a.id, "@bob@peer.example")

            consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user_a.id)).scalars().first()
            assert consent is not None
            assert consent.federated_profile is True
            # Collection consent MUST NOT be implicitly enabled
            assert consent.federated_collection is False
            assert user_a.federation_public_key is not None

    def test_case_02_crossover_follow_timestamp_direction_resolution(self, app, matrix_users) -> None:
        """Newer inbound follow overrides stale outbound follow for direction in list_friends."""
        user_a_id, user_b_id = matrix_users
        with app.app_context():
            user_b = db.session.get(User, user_b_id)
            remote_actor_uri = "https://peer.test/users/charlie"

            inst = FederationInstance(domain="peer.test", software_name="iqoqo", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri=remote_actor_uri,
                username="charlie",
                inbox_url="https://peer.test/users/charlie/inbox",
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.flush()

            follower = FederationFollower(
                local_user_id=user_b.id,
                remote_actor_id=actor.id,
                status=FollowStatus.PENDING,
            )
            db.session.add(follower)
            db.session.flush()

            # Stale outbound at t=10
            stale_outbound = FederationActivity(
                activity_type="Follow",
                direction="outbound",
                actor_uri=canonical_actor_iri(user_b.id),
                target_uri=remote_actor_uri,
                status=ActivityStatus.DELIVERED,
                created_at=datetime.now(UTC) - timedelta(hours=2),
            )
            # Newer inbound at t=20
            newer_inbound = FederationActivity(
                activity_type="Follow",
                direction="inbound",
                actor_uri=remote_actor_uri,
                target_uri=canonical_actor_iri(user_b.id),
                status=ActivityStatus.DELIVERED,
                created_at=datetime.now(UTC) - timedelta(minutes=5),
            )
            db.session.add_all([stale_outbound, newer_inbound])
            db.session.commit()

            friends_data = list_friends(user_b.id)
            incoming_items = friends_data.get("incoming", [])
            target_incoming = next((item for item in incoming_items if item["friendship_id"] == f"fed:{follower.id}"), None)
            assert target_incoming is not None

    def test_case_03_requester_cannot_self_accept_outgoing_follow(self, app, matrix_users) -> None:
        """Calling respond_friend_request on an outgoing request returns HTTP 400."""
        user_a_id, _ = matrix_users
        with app.app_context():
            user_a = db.session.get(User, user_a_id)
            remote_actor_uri = "https://peer.test/users/david"

            inst = FederationInstance(domain="peer.test", software_name="iqoqo", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri=remote_actor_uri,
                username="david",
                inbox_url="https://peer.test/users/david/inbox",
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.flush()

            follower = FederationFollower(
                local_user_id=user_a.id,
                remote_actor_id=actor.id,
                status=FollowStatus.PENDING,
            )
            db.session.add(follower)
            db.session.flush()

            outbound_activity = FederationActivity(
                activity_type="Follow",
                direction="outbound",
                actor_uri=canonical_actor_iri(user_a.id),
                target_uri=actor.inbox_url,
                object_json={"object": remote_actor_uri},
                status=ActivityStatus.DELIVERED,
                created_at=datetime.now(UTC),
            )
            db.session.add(outbound_activity)
            db.session.commit()

            result, err, status = respond_friend_request(user_a.id, f"fed:{follower.id}", action="accept")
            assert status == 400
            assert "outgoing request" in (err or "").lower()

    def test_case_04_accept_payload_contains_canonical_actor_iri(self, app, matrix_users) -> None:
        """Accept dispatch contains canonical actor IRI rather than internal local:id string."""
        _, user_b_id = matrix_users
        with app.app_context():
            user_b = db.session.get(User, user_b_id)
            remote_actor_uri = "https://peer.test/users/eva"

            inst = FederationInstance(domain="peer.test", software_name="iqoqo", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri=remote_actor_uri,
                username="eva",
                inbox_url="https://peer.test/users/eva/inbox",
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.flush()

            follower = FederationFollower(
                local_user_id=user_b.id,
                remote_actor_id=actor.id,
                status=FollowStatus.PENDING,
            )
            db.session.add(follower)
            db.session.flush()

            inbound_activity = FederationActivity(
                activity_type="Follow",
                direction="inbound",
                actor_uri=remote_actor_uri,
                target_uri=canonical_actor_iri(user_b.id),
                status=ActivityStatus.DELIVERED,
                created_at=datetime.now(UTC),
            )
            db.session.add(inbound_activity)
            db.session.commit()

            with patch("app.core.federation_dispatch.dispatch_accept_follow") as mock_dispatch:
                result, err, status = respond_friend_request(user_b.id, f"fed:{follower.id}", action="accept")

            assert status == 200
            assert err is None
            mock_dispatch.assert_called_once()
            dispatched_follow = mock_dispatch.call_args[0][2]
            assert dispatched_follow["type"] == "Follow"
            assert dispatched_follow["object"] == canonical_actor_iri(user_b.id, get_federation_base_url())

    def test_case_05_handle_accept_accepts_canonical_iri_and_local_id(self, app, matrix_users) -> None:
        """handle_accept accepts both canonical actor IRI and fallback local:<id>."""
        user_a_id, _ = matrix_users
        with app.app_context():
            user_a = db.session.get(User, user_a_id)
            remote_actor_uri = "https://peer.test/users/frank"

            inst = FederationInstance(domain="peer.test", software_name="iqoqo", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri=remote_actor_uri,
                username="frank",
                inbox_url="https://peer.test/users/frank/inbox",
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.flush()

            follower = FederationFollower(
                local_user_id=user_a.id,
                remote_actor_id=actor.id,
                status=FollowStatus.PENDING,
            )
            db.session.add(follower)
            db.session.commit()

            canonical_iri = canonical_actor_iri(user_a.id, get_federation_base_url())
            accept_payload = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://peer.test/activities/{uuid.uuid4()}",
                "type": "Accept",
                "actor": remote_actor_uri,
                "object": {
                    "type": "Follow",
                    "actor": canonical_iri,
                    "object": remote_actor_uri,
                },
            }

            handled = federation_handlers.handle_accept(accept_payload)
            assert handled is True
            db.session.refresh(follower)
            assert follower.status == FollowStatus.ACCEPTED

    def test_case_06_handle_accept_rejects_spoofed_actor(self, app, matrix_users) -> None:
        """handle_accept rejects spoofed Accept activities where actor doesn't match object target."""
        user_a_id, _ = matrix_users
        with app.app_context():
            user_a = db.session.get(User, user_a_id)
            canonical_iri = canonical_actor_iri(user_a.id, get_federation_base_url())

            spoofed_accept = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://peer.test/activities/{uuid.uuid4()}",
                "type": "Accept",
                "actor": "https://evil.test/users/mallory",
                "object": {
                    "type": "Follow",
                    "actor": canonical_iri,
                    "object": "https://legit.test/users/alice",  # Does not match evil actor
                },
            }
            handled = federation_handlers.handle_accept(spoofed_accept)
            assert handled is False

    def test_case_07_get_actor_public_key_syncs_from_disk_pem(self, app, matrix_users) -> None:
        """get_actor_public_key derives public key from disk private key and updates DB."""
        user_a_id, _ = matrix_users
        with app.app_context():
            user_a = db.session.get(User, user_a_id)
            user_a.federation_public_key = "STALE_KEY_DATA"
            db.session.commit()

            # Ensure disk key exists
            generate_actor_keypair(str(user_a.id))
            priv_key = get_actor_private_key(str(user_a.id))
            assert priv_key is not None
            derived_pub_pem = (
                priv_key.public_key()
                .public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                .decode("utf-8")
                .strip()
            )

            retrieved_pub_pem = get_actor_public_key(str(user_a.id))
            assert retrieved_pub_pem is not None
            assert retrieved_pub_pem.strip() == derived_pub_pem
            db.session.refresh(user_a)
            assert user_a.federation_public_key.strip() == derived_pub_pem

    def test_case_08_undo_follow_revokes_friendship(self, app, matrix_users) -> None:
        """Undo(Follow) activity removes active friendship."""
        _, user_b_id = matrix_users
        with app.app_context():
            user_b = db.session.get(User, user_b_id)
            remote_actor_uri = "https://peer.test/users/grace"

            inst = FederationInstance(domain="peer.test", software_name="iqoqo", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri=remote_actor_uri,
                username="grace",
                inbox_url="https://peer.test/users/grace/inbox",
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.flush()

            follower = FederationFollower(
                local_user_id=user_b.id,
                remote_actor_id=actor.id,
                status=FollowStatus.ACCEPTED,
            )
            db.session.add(follower)
            db.session.commit()

            undo_activity = {
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": f"https://peer.test/activities/{uuid.uuid4()}",
                "type": "Undo",
                "actor": remote_actor_uri,
                "object": {
                    "type": "Follow",
                    "actor": remote_actor_uri,
                    "object": canonical_actor_iri(user_b.id, get_federation_base_url()),
                },
            }
            handled = federation_handlers.handle_undo(undo_activity)
            assert handled is True
            follower_stmt = select(FederationFollower).where(
                FederationFollower.local_user_id == user_b.id,
                FederationFollower.remote_actor_id == actor.id,
            )
            follower_after = db.session.execute(follower_stmt).scalars().first()
            assert follower_after is None

    def test_case_09_user_friends_only_visibility_check_constraint(self, app) -> None:
        """User table permits 'friends_only' for visibility and default_item_visibility."""
        with app.app_context():
            u = User(
                email=f"constraint_{uuid.uuid4().hex[:6]}@example.com",
                public_username=f"constraint_{uuid.uuid4().hex[:6]}",
                visibility="friends_only",
                default_item_visibility="friends_only",
            )
            u.set_password("Pass1234!")
            db.session.add(u)
            db.session.commit()
            db.session.refresh(u)
            assert u.visibility == "friends_only"
            assert u.default_item_visibility == "friends_only"

    def test_case_10_consent_endpoint_syncs_with_federation_consent(self, client, app, matrix_users) -> None:
        """POST /api/profile/consent with consent_type='federation' syncs FederationConsent."""
        user_a_id, _ = matrix_users
        with app.app_context():
            user_a = db.session.get(User, user_a_id)
            token = generate_internal_jwt(user_a)

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            "/api/profile/consent",
            json={"consent_type": "federation", "is_granted": True},
            headers=headers,
        )
        assert resp.status_code == 200

        with app.app_context():
            consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user_a_id)).scalars().first()
            assert consent is not None
            assert consent.federated_profile is True

    def test_case_11_unconsented_actor_webfinger_returns_404(self, client, app, matrix_users) -> None:
        """WebFinger returns 404 for users with federated_profile=False."""
        user_a_id, _ = matrix_users
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            domain = _get_domain()
            user_a = db.session.get(User, user_a_id)
            consent = FederationConsent(user_id=user_a.id, federated_profile=False)
            db.session.merge(consent)
            db.session.commit()
            username = user_a.public_username

        resp = client.get(f"/.well-known/webfinger?resource=acct:{username}@{domain}")
        assert resp.status_code == 404

    def test_case_12_consented_actor_webfinger_returns_200(self, client, app, matrix_users) -> None:
        """WebFinger returns 200 with Actor link for users with federated_profile=True."""
        user_a_id, _ = matrix_users
        with app.app_context():
            app.config["FEDERATION_ENABLED"] = True
            domain = _get_domain()
            user_a = db.session.get(User, user_a_id)
            consent = FederationConsent(user_id=user_a.id, federated_profile=True)
            db.session.merge(consent)
            db.session.commit()
            username = user_a.public_username

        resp = client.get(f"/.well-known/webfinger?resource=acct:{username}@{domain}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["subject"] == f"acct:{username}@{domain}"
        links = data.get("links", [])
        assert any(link.get("rel") == "self" for link in links)
