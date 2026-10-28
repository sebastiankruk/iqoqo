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
"""Tests for federation models, Alembic migration, and Fernet-encrypted RSA key management."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core import account_lifecycle, federation_keys
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
from app.db.models import User, db


@pytest.fixture
def custom_keys_dir(tmp_path, monkeypatch):
    """Isolate key storage in temporary test directory."""
    keys_dir = tmp_path / "keys"
    monkeypatch.setattr(federation_keys, "_KEYS_DIR", keys_dir)
    return keys_dir


class TestFederationModels:
    """Test suite for federation database models and serialization."""

    def test_federation_instance_creation(self, app):
        with app.app_context():
            instance = FederationInstance(
                domain="federated.example.com",
                shared_inbox_url="https://federated.example.com/inbox",
                software_name="Mastodon",
                software_version="4.2.0",
                trust_level=TrustLevel.TRUSTED,
            )
            db.session.add(instance)
            db.session.commit()

            assert instance.id is not None
            assert instance.domain == "federated.example.com"
            assert instance.trust_level == TrustLevel.TRUSTED
            assert instance.created_at is not None

            data = instance.to_dict()
            assert data["domain"] == "federated.example.com"
            assert data["trust_level"] == TrustLevel.TRUSTED
            assert data["software_name"] == "Mastodon"

    def test_federation_actor_and_relationships(self, app):
        with app.app_context():
            instance = FederationInstance(domain="actor.example.com")
            db.session.add(instance)
            db.session.commit()

            actor = FederationActor(
                actor_uri="https://actor.example.com/users/alice",
                inbox_url="https://actor.example.com/users/alice/inbox",
                outbox_url="https://actor.example.com/users/alice/outbox",
                public_key_pem="-----BEGIN PUBLIC KEY-----\nMIIB...",
                instance_id=instance.id,
                display_name="Alice Explorer",
                username="alice",
            )
            db.session.add(actor)
            db.session.commit()

            assert actor.id is not None
            assert actor.instance.domain == "actor.example.com"

            data = actor.to_dict()
            assert data["actor_uri"] == "https://actor.example.com/users/alice"
            assert data["username"] == "alice"

    def test_federation_follower_and_consent(self, app):
        with app.app_context():
            user = User(email="localuser@iqoqo.local", public_username="localuser")
            user.set_password("SecurePassword123!")
            db.session.add(user)
            db.session.commit()

            instance = FederationInstance(domain="follower.example.com")
            db.session.add(instance)
            db.session.commit()

            actor = FederationActor(
                actor_uri="https://follower.example.com/users/bob",
                inbox_url="https://follower.example.com/users/bob/inbox",
                instance_id=instance.id,
            )
            db.session.add(actor)
            db.session.commit()

            follower = FederationFollower(
                local_user_id=user.id,
                remote_actor_id=actor.id,
                status=FollowStatus.ACCEPTED,
            )
            db.session.add(follower)

            consent = FederationConsent(
                user_id=user.id,
                federated_profile=True,
                federated_collection=False,
            )
            db.session.add(consent)
            db.session.commit()

            assert follower.id is not None
            assert consent.id is not None
            assert consent.federated_profile is True
            assert consent.federated_collection is False

            consent_dict = consent.to_dict()
            assert consent_dict["user_id"] == str(user.id)
            assert consent_dict["federated_profile"] is True

            follower_dict = follower.to_dict()
            assert follower_dict["local_user_id"] == str(user.id)
            assert follower_dict["status"] == FollowStatus.ACCEPTED

    def test_federation_activity_lifecycle(self, app):
        with app.app_context():
            activity_id = uuid.uuid4()
            activity = FederationActivity(
                id=activity_id,
                actor_uri="https://iqoqo.local/users/admin",
                activity_type="Create",
                object_json={"type": "Note", "content": "Hello fediverse"},
                target_uri="https://remote.example.org/inbox",
                direction="outbound",
                status=ActivityStatus.QUEUED,
            )
            db.session.add(activity)
            db.session.commit()

            stored = db.session.get(FederationActivity, activity_id)
            assert stored is not None
            assert stored.activity_type == "Create"
            assert stored.object_json == {"type": "Note", "content": "Hello fediverse"}

            dict_repr = stored.to_dict()
            assert dict_repr["id"] == str(activity_id)
            assert dict_repr["status"] == ActivityStatus.QUEUED


class TestFederationKeys:
    """Test suite for RSA-2048 keypair generation and Fernet encryption at rest."""

    def test_keypair_generation_and_fernet_encryption_at_rest(self, custom_keys_dir):
        user_id = str(uuid.uuid4())
        suffix, public_key_pem = federation_keys.generate_actor_keypair(user_id)

        assert suffix == "#main-key"
        assert public_key_pem.startswith("-----BEGIN PUBLIC KEY-----")

        key_path = custom_keys_dir / f"{user_id}.pem"
        assert key_path.exists()

        # Security check: Ensure file is NOT cleartext PEM
        raw_bytes = key_path.read_bytes()
        assert not raw_bytes.startswith(b"-----BEGIN")

        # Permissions check: 0600 restrictive
        file_mode = oct(os.stat(key_path).st_mode & 0o777)
        assert file_mode == "0o600"

        # Decryption and signature verification
        private_key = federation_keys.get_actor_private_key(user_id)
        assert isinstance(private_key, rsa.RSAPrivateKey)
        assert private_key.key_size == 2048

        # Test signing and verification
        test_payload = b"iqoqo activitypub signature verification"
        signature = private_key.sign(
            test_payload,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        pub_obj = load_pem_public_key(public_key_pem.encode("utf-8"))
        # Verification succeeds without raising
        pub_obj.verify(
            signature,
            test_payload,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

    def test_get_actor_public_key_fallback_and_deletion(self, custom_keys_dir):
        user_id = str(uuid.uuid4())
        _, expected_pub = federation_keys.generate_actor_keypair(user_id)

        pub_key = federation_keys.get_actor_public_key(user_id)
        assert pub_key == expected_pub

        # Test deletion
        deleted = federation_keys.delete_actor_keypair(user_id)
        assert deleted is True
        assert not (custom_keys_dir / f"{user_id}.pem").exists()

        # Subsequent calls return None
        assert federation_keys.get_actor_private_key(user_id) is None
        assert federation_keys.get_actor_public_key(user_id) is None
        assert federation_keys.delete_actor_keypair(user_id) is False

    def test_legacy_unencrypted_pem_fallback(self, custom_keys_dir):
        """Ensure backward compatibility if an unencrypted PEM is encountered."""
        user_id = str(uuid.uuid4())
        raw_rsa = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        from cryptography.hazmat.primitives import serialization

        cleartext_pem = raw_rsa.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        custom_keys_dir.mkdir(parents=True, exist_ok=True)
        key_path = custom_keys_dir / f"{user_id}.pem"
        key_path.write_bytes(cleartext_pem)

        loaded_key = federation_keys.get_actor_private_key(user_id)
        assert isinstance(loaded_key, rsa.RSAPrivateKey)
        assert loaded_key.key_size == 2048

    def test_path_traversal_protection(self, custom_keys_dir):
        """Security: Path traversal attempts must be rejected with ValueError."""
        with pytest.raises(ValueError, match="Invalid user_id"):
            federation_keys.generate_actor_keypair("../../etc/passwd")

        with pytest.raises(ValueError, match="Invalid user_id"):
            federation_keys.generate_actor_keypair("../foo")

        with pytest.raises(ValueError, match="Invalid user_id"):
            federation_keys.get_actor_private_key("../../etc/passwd")

        with pytest.raises(ValueError, match="Invalid user_id"):
            federation_keys.delete_actor_keypair("/var/log/syslog")

    def test_ensure_instance_actor_key_and_fingerprint(self, custom_keys_dir):
        """Instance actor key (server.pem) must be generated and fingerprint computed."""
        server_key = custom_keys_dir / "server.pem"
        assert not server_key.exists()

        fp1 = federation_keys.ensure_instance_actor_key()
        assert fp1.startswith("SHA256:")
        assert server_key.exists()

        # Idempotent call does not regenerate
        fp2 = federation_keys.ensure_instance_actor_key()
        assert fp2 == fp1

        # Rotate key
        fp3 = federation_keys.ensure_instance_actor_key(rotate=True)
        assert fp3.startswith("SHA256:")
        assert fp3 != fp1

    def test_missing_secret_key_raises_runtime_error(self, monkeypatch):
        """Missing SECRET_KEY must raise RuntimeError instead of falling back to insecure default."""
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with patch("flask.current_app", None):
            with patch("app.config.Config.SECRET_KEY", None):
                with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
                    federation_keys._get_fernet_cipher()


class TestAccountLifecycleIntegration:
    """Verify federation cascades and key deletion when accounts are deleted."""

    def test_account_deletion_cleans_up_federation_entities_and_keys(self, app, custom_keys_dir):
        with app.app_context():
            user = User(email="deleteme@iqoqo.local", public_username="deleteme")
            user.set_password("TempPassword123!")
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Create federation consent and keys
            consent = FederationConsent(user_id=user_id, federated_profile=True)
            db.session.add(consent)
            db.session.commit()

            suffix, pub = federation_keys.generate_actor_keypair(str(user_id))
            user.federation_key_id = f"https://iqoqo.local/users/{user_id}{suffix}"
            user.federation_public_key = pub
            db.session.commit()

            key_file = custom_keys_dir / f"{user_id}.pem"
            assert key_file.exists()

            # Execute deletion
            removed_children = account_lifecycle._delete_account_rows(user)
            db.session.commit()

            assert removed_children >= 1
            # Verify user and consent rows are gone
            assert db.session.get(User, user_id) is None
            assert db.session.execute(db.select(FederationConsent).where(FederationConsent.user_id == user_id)).scalar_one_or_none() is None

            # Verify private key file is removed from disk
            assert not key_file.exists()
