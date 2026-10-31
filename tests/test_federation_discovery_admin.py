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
"""Tests for admin trust audit logs, actor inbox discovery, and concurrent health probes."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.core import federation_discovery
from app.core.federation_handlers import _get_or_create_actor
from app.db import db
from app.db.core import EntityAuditLog
from app.db.federation import FederationActor, FederationInstance, TrustLevel


class TestFederationDiscoveryAdmin:
    """Test suite for admin trust auditing, actor inbox fetching, and bounded concurrency."""

    def test_admin_trust_mutation_records_audit_log(self, client, admin_headers, app):
        """Updating trust level emits EntityAuditLog with old and new levels."""
        with app.app_context():
            inst = FederationInstance(domain="audit-test.fed.org", trust_level=TrustLevel.UNTRUSTED)
            db.session.add(inst)
            db.session.commit()
            inst_id = inst.id

        resp = client.put(
            f"/api/v1/admin/federation/instances/{inst_id}/trust",
            headers=admin_headers,
            json={"trust_level": "trusted"},
        )
        assert resp.status_code == 200

        with app.app_context():
            audit = (
                db.session.execute(
                    select(EntityAuditLog).where(
                        EntityAuditLog.entity_type == "federation_instance",
                        EntityAuditLog.entity_id == inst_id,
                        EntityAuditLog.change_type == "trust_level_updated",
                    )
                )
                .scalars()
                .first()
            )
            assert audit is not None
            assert audit.diff["old_trust_level"] == "untrusted"
            assert audit.diff["new_trust_level"] == "trusted"
            assert audit.diff["domain"] == "audit-test.fed.org"

    def test_admin_instance_deletion_records_audit_log(self, client, admin_headers, app):
        """Deleting an instance records EntityAuditLog before removing."""
        with app.app_context():
            inst = FederationInstance(domain="delete-test.fed.org", trust_level=TrustLevel.UNTRUSTED)
            db.session.add(inst)
            db.session.commit()
            inst_id = inst.id

        resp = client.delete(
            f"/api/v1/admin/federation/instances/{inst_id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

        with app.app_context():
            audit = (
                db.session.execute(
                    select(EntityAuditLog).where(
                        EntityAuditLog.entity_type == "federation_instance",
                        EntityAuditLog.entity_id == inst_id,
                        EntityAuditLog.change_type == "instance_deleted",
                    )
                )
                .scalars()
                .first()
            )
            assert audit is not None
            assert audit.diff["domain"] == "delete-test.fed.org"
            assert db.session.get(FederationInstance, inst_id) is None

    def test_add_instance_surfaces_probe_succeeded(self, client, admin_headers, app):
        """add_federation_instance includes probe_succeeded in response payload."""
        with patch("app.core.federation_discovery.safe_get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_get.return_value = mock_resp

            resp = client.post(
                "/api/v1/admin/federation/instances",
                headers=admin_headers,
                json={"domain": "probe-test.fed.org"},
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert "probe_succeeded" in data
            assert data["probe_succeeded"] is False
            assert data["data"]["probe_succeeded"] is False

    def test_get_or_create_actor_resolves_remote_inbox_and_key(self, app):
        """_get_or_create_actor calls FederationClient().fetch_actor to resolve canonical inbox."""
        actor_uri = "https://remote-library.org/users/carol"

        with app.app_context():
            mock_actor_doc = {
                "id": actor_uri,
                "type": "Person",
                "inbox": "https://remote-library.org/actors/carol/custom-inbox",
                "publicKey": {
                    "id": f"{actor_uri}#main-key",
                    "owner": actor_uri,
                    "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIB...\n-----END PUBLIC KEY-----",
                },
            }

            with patch("app.core.federation_client.FederationClient.fetch_actor", return_value=mock_actor_doc):
                actor = _get_or_create_actor(actor_uri)
                assert actor is not None
                assert actor.inbox_url == "https://remote-library.org/actors/carol/custom-inbox"
                assert actor.public_key_pem == "-----BEGIN PUBLIC KEY-----\nMIIB...\n-----END PUBLIC KEY-----"

    def test_get_or_create_actor_fallback_when_fetch_fails(self, app):
        """_get_or_create_actor falls back to {actor_uri}/inbox when fetch_actor returns None."""
        actor_uri = "https://unreachable-peer.org/users/dave"

        with app.app_context():
            with patch("app.core.federation_client.FederationClient.fetch_actor", return_value=None):
                actor = _get_or_create_actor(actor_uri)
                assert actor is not None
                assert actor.inbox_url == f"{actor_uri}/inbox"

    def test_probe_registered_instances_bounded_concurrency(self, app):
        """probe_registered_instances probes multiple peers concurrently with bounded workers."""
        with app.app_context():
            db.session.query(FederationInstance).delete()
            for i in range(5):
                inst = FederationInstance(
                    domain=f"peer-{i}.example.org",
                    trust_level=TrustLevel.UNTRUSTED,
                )
                db.session.add(inst)
            db.session.commit()

            with patch("app.core.federation_discovery.probe_instance_health") as mock_probe:
                mock_probe.side_effect = lambda inst: inst.domain.endswith("2.example.org")

                results = federation_discovery.probe_registered_instances(max_workers=3)

                assert len(results) == 5
                assert results["peer-2.example.org"] is True
                assert results["peer-0.example.org"] is False

    def test_probe_registered_instances_deadline_guard(self, app):
        """probe_registered_instances catches timeout exceptions without crashing the job."""
        with app.app_context():
            inst = FederationInstance(
                domain="slow-peer.example.org",
                trust_level=TrustLevel.UNTRUSTED,
            )
            db.session.add(inst)
            db.session.commit()

            with patch("app.core.federation_discovery.probe_instance_health") as mock_probe:

                def slow_probe(_):
                    time.sleep(0.5)
                    return True

                mock_probe.side_effect = slow_probe

                # Run with very small per_probe_timeout to test timeout handling
                results = federation_discovery.probe_registered_instances(
                    max_workers=1,
                    per_probe_timeout=0.05,
                )
                assert "slow-peer.example.org" in results
                assert results["slow-peer.example.org"] is False

    def test_inbound_actor_preserves_port_and_respects_blocked_instance(self, app):
        """_get_or_create_actor preserves non-standard port and attaches to blocked instance."""
        with app.app_context():
            # Block an instance on custom port 8443
            blocked_inst = FederationInstance(
                domain="malicious.example:8443",
                trust_level=TrustLevel.BLOCKED,
            )
            db.session.add(blocked_inst)
            db.session.commit()

            actor_uri = "https://malicious.example:8443/u/attacker"
            with patch("app.core.federation_client.FederationClient.fetch_actor", return_value=None):
                actor = _get_or_create_actor(actor_uri)
                assert actor is not None
                # Must attach to blocked_inst (with port :8443), NOT create a new unblocked 'malicious.example' instance
                assert actor.instance_id == blocked_inst.id
                assert actor.instance.domain == "malicious.example:8443"
                assert actor.instance.trust_level == TrustLevel.BLOCKED

    def test_get_federation_instances_surfaces_key_fingerprint(self, client, admin_headers, app):
        """GET /api/v1/admin/federation/instances includes DER-computed SHA256 key_fingerprint."""
        from app.core import federation_keys

        _, pub_pem = federation_keys.generate_actor_keypair("test-peer")
        expected_fp = federation_keys.compute_pem_fingerprint(pub_pem)

        with app.app_context():
            inst = FederationInstance(domain="fingerprint.fed.org", trust_level=TrustLevel.UNTRUSTED)
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri="https://fingerprint.fed.org/api/federation/actor",
                inbox_url="https://fingerprint.fed.org/api/federation/inbox",
                public_key_pem=pub_pem,
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.commit()

        resp = client.get("/api/v1/admin/federation/instances", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        inst_match = next((i for i in data if i["domain"] == "fingerprint.fed.org"), None)
        assert inst_match is not None
        assert inst_match["key_fingerprint"] == expected_fp

    def test_discover_instance_fetches_and_caches_instance_actor(self, app):
        """discover_instance invokes FederationClient to cache remote instance Application actor."""
        from app.core import federation_keys

        _, pub_pem = federation_keys.generate_actor_keypair("test-peer")
        domain = "remote-peer.example.org"
        actor_uri = f"https://{domain}/api/federation/actor"

        mock_actor_doc = {
            "id": actor_uri,
            "type": "Application",
            "inbox": f"https://{domain}/api/federation/inbox",
            "publicKey": {
                "id": f"{actor_uri}#main-key",
                "owner": actor_uri,
                "publicKeyPem": pub_pem,
            },
        }

        with app.app_context():
            with (
                patch("app.core.federation_discovery._probe_domain_http") as mock_probe,
                patch("app.core.federation_client.safe_get") as mock_safe_get,
            ):
                mock_probe.return_value = (True, {"software_name": "iqoqo", "instance_actor_url": actor_uri})
                mock_safe_resp = MagicMock()
                mock_safe_resp.status_code = 200
                mock_safe_resp.json.return_value = mock_actor_doc
                mock_safe_get.return_value = mock_safe_resp

                instance = federation_discovery.discover_instance(domain)
                assert instance is not None
                assert instance.software_name == "iqoqo"

                cached_actor = db.session.execute(select(FederationActor).where(FederationActor.actor_uri == actor_uri)).scalars().first()
                assert cached_actor is not None
                assert cached_actor.public_key_pem == pub_pem

    def test_admin_trust_mutation_normalizes_pending_to_untrusted(self, client, admin_headers, app):
        """Updating trust level with legacy 'pending' normalizes to 'untrusted'."""
        with app.app_context():
            inst = FederationInstance(domain="legacy-pending.fed.org", trust_level=TrustLevel.TRUSTED)
            db.session.add(inst)
            db.session.commit()
            inst_id = inst.id

        resp = client.put(
            f"/api/v1/admin/federation/instances/{inst_id}/trust",
            headers=admin_headers,
            json={"trust_level": "pending"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["trust_level"] == "untrusted"

        with app.app_context():
            updated = db.session.get(FederationInstance, inst_id)
            assert updated.trust_level == TrustLevel.UNTRUSTED
