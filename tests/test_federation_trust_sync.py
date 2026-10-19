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
"""Tests for Fediverse Trust Graph, Health Discovery, and Metadata Reconciliation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.core import federation_discovery, federation_sync, frbr_service
from app.db import db
from app.db.core import EntityAuditLog, Expression, Manifestation, Work
from app.db.federation import FederationActor, FederationInstance, TrustLevel
from app.utils.http_client import SSRFError


@pytest.fixture
def frbr_catalog(app):
    """Seed sample Work -> Expression -> Manifestation hierarchy for sync testing."""
    with app.app_context():
        work = Work(title="Dune", sort_title="Dune", meta={"authors": ["Frank Herbert"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, language="en", content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780441172719",
            publisher=None,
            cover_url=None,
            meta={},
            raw_payload={},
        )
        db.session.add(manif)
        db.session.commit()

        return {
            "work_id": work.id,
            "expression_id": expr.id,
            "manifestation_id": manif.id,
        }


class TestFederationDiscovery:
    """Test suite for instance discovery and periodic health probes."""

    def test_clean_instance_domain_preserves_non_standard_port(self):
        assert federation_discovery.clean_instance_domain("peer-web:5000") == "peer-web:5000"
        assert federation_discovery.clean_instance_domain("http://peer-web:5000/inbox") == "peer-web:5000"
        assert federation_discovery.clean_instance_domain("https://mastodon.social:443") == "mastodon.social"
        assert federation_discovery.clean_instance_domain("https://mastodon.social") == "mastodon.social"
        assert federation_discovery.clean_instance_domain("localhost:5005") == "localhost:5005"

    def test_discover_instance_creates_untrusted(self, app):
        with app.app_context():
            with patch("app.core.federation_discovery.safe_get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 404
                mock_get.return_value = mock_resp

                inst = federation_discovery.discover_instance("https://books.remote-library.org/about")
                assert inst is not None
                assert inst.domain == "books.remote-library.org"
                assert inst.trust_level == TrustLevel.UNTRUSTED

    def test_probe_instance_health_http_fallback(self, app, monkeypatch):
        monkeypatch.setenv("FEDERATION_ALLOW_LOOPBACK", "true")
        with app.app_context():
            inst = FederationInstance(
                domain="peer-web:5000",
                trust_level=TrustLevel.UNTRUSTED,
            )
            db.session.add(inst)
            db.session.commit()

            with patch("app.core.federation_discovery.safe_get") as mock_get:
                # https raises connection error, http succeeds
                http_ni = MagicMock()
                http_ni.status_code = 200
                http_ni.json.return_value = {
                    "software": {"name": "iqoqo", "version": "0.9.1"},
                }

                def safe_get_mock(url, *args, **kwargs):
                    if url.startswith("https://"):
                        raise ConnectionRefusedError("Connection refused")
                    if "/.well-known/nodeinfo" in url:
                        resp = MagicMock(status_code=200)
                        resp.json.return_value = {
                            "links": [
                                {"rel": "http://nodeinfo.diaspora.software/ns/schema/2.1", "href": "http://peer-web:5000/api/nodeinfo"}
                            ]
                        }
                        return resp
                    if "/api/nodeinfo" in url:
                        return http_ni
                    return MagicMock(status_code=404)

                mock_get.side_effect = safe_get_mock
                success = federation_discovery.probe_instance_health(inst)
                assert success is True
                assert inst.software_name == "iqoqo"
                assert inst.software_version == "0.9.1"
                assert inst.last_seen_at is not None

    def test_probe_instance_health_nodeinfo(self, app):
        with app.app_context():
            inst = FederationInstance(
                domain="nodeinfo.peer.net",
                trust_level=TrustLevel.PENDING,
            )
            db.session.add(inst)
            db.session.commit()

            with patch("app.core.federation_discovery.safe_get") as mock_get:
                well_known_resp = MagicMock()
                well_known_resp.status_code = 200
                well_known_resp.json.return_value = {
                    "links": [{"rel": "http://nodeinfo.diaspora.software/ns/schema/2.1", "href": "https://nodeinfo.peer.net/ni/2.1"}]
                }

                ni_resp = MagicMock()
                ni_resp.status_code = 200
                ni_resp.json.return_value = {
                    "software": {"name": "iqoqo", "version": "0.9.1"},
                    "metadata": {"sharedInbox": "https://nodeinfo.peer.net/inbox"},
                }

                mock_get.side_effect = [well_known_resp, ni_resp]

                success = federation_discovery.probe_instance_health(inst)
                assert success is True
                assert inst.software_name == "iqoqo"
                assert inst.software_version == "0.9.1"
                assert inst.shared_inbox_url == "https://nodeinfo.peer.net/inbox"
                assert inst.last_seen_at is not None

    def test_probe_instance_health_skips_blocked(self, app):
        with app.app_context():
            inst = FederationInstance(
                domain="spammer.badsite.org",
                trust_level=TrustLevel.BLOCKED,
            )
            db.session.add(inst)
            db.session.commit()

            with patch("app.core.federation_discovery.safe_get") as mock_get:
                success = federation_discovery.probe_instance_health(inst)
                assert success is False
                mock_get.assert_not_called()

    def test_probe_instance_health_ssrf_handled(self, app):
        with app.app_context():
            inst = FederationInstance(
                domain="internal.loopback.net",
                trust_level=TrustLevel.UNTRUSTED,
            )
            db.session.add(inst)
            db.session.commit()

            with patch("app.core.federation_discovery.safe_get", side_effect=SSRFError("Blocked private IP")):
                success = federation_discovery.probe_instance_health(inst)
                assert success is False


class TestFederationMetadataSync:
    """Test suite for trust-gated metadata reconciliation."""

    def test_trusted_peer_updates_empty_fields_and_provenance(self, app, frbr_catalog):
        with app.app_context():
            manif_id = frbr_catalog["manifestation_id"]
            manif = db.session.get(Manifestation, manif_id)

            remote_data = {
                "isbn13": "9780441172719",
                "page_count": 412,
                "publisher": "Ace Books",
                "format": "paperback",
            }

            res = federation_sync.sync_manifestation(
                manifestation=manif,
                remote_data=remote_data,
                domain="trusted-peer.org",
                trust_level=TrustLevel.TRUSTED,
            )

            assert res["status"] == "merged"
            assert manif.publisher == "Ace Books"
            assert manif.format == "paperback"
            assert manif.meta.get("page_count") == 412

            prov = manif.meta.get("_provenance", {})
            assert prov.get("page_count") == "federation:trusted-peer.org"
            assert prov.get("publisher") == "federation:trusted-peer.org"
            assert prov.get("format") == "federation:trusted-peer.org"
            assert "federation:trusted-peer.org" in manif.meta.get("prov:wasDerivedFrom", [])

            audit = (
                db.session.execute(
                    select(EntityAuditLog).where(
                        EntityAuditLog.entity_id == manif_id,
                        EntityAuditLog.change_type == "federation_sync_auto_fill",
                    )
                )
                .scalars()
                .first()
            )
            assert audit is not None
            assert audit.diff["fields"]["page_count"] == 412

    def test_trusted_peer_preserves_existing_local_values(self, app, frbr_catalog):
        with app.app_context():
            manif_id = frbr_catalog["manifestation_id"]
            manif = db.session.get(Manifestation, manif_id)
            manif.publisher = "Original Chilton Edition"
            manif.meta = {"page_count": 412}
            db.session.commit()

            remote_data = {
                "isbn13": "9780441172719",
                "publisher": "Hostile Remote Overwrite",
                "page_count": 999,
                "cover_url": "https://trusted-peer.org/cover.jpg",
            }

            res = federation_sync.sync_manifestation(
                manifestation=manif,
                remote_data=remote_data,
                domain="trusted-peer.org",
                trust_level=TrustLevel.TRUSTED,
            )

            assert res["status"] == "merged"
            assert manif.publisher == "Original Chilton Edition"
            assert manif.meta.get("page_count") == 412
            assert manif.cover_url == "https://trusted-peer.org/cover.jpg"
            assert manif.meta["_provenance"].get("cover_url") == "federation:trusted-peer.org"

    def test_pending_peer_queues_for_custodian_merge(self, app, frbr_catalog):
        with app.app_context():
            manif_id = frbr_catalog["manifestation_id"]
            manif = db.session.get(Manifestation, manif_id)

            remote_data = {
                "isbn13": "9780441172719",
                "publisher": "Candidate Press",
                "page_count": 500,
            }

            res = federation_sync.sync_manifestation(
                manifestation=manif,
                remote_data=remote_data,
                domain="pending-peer.org",
                trust_level=TrustLevel.PENDING,
            )

            assert res["status"] == "queued_for_review"
            assert manif.publisher is None
            assert manif.meta.get("page_count") is None

            provider_key = "federation:pending-peer.org"
            assert manif.raw_payload[provider_key]["publisher"] == "Candidate Press"
            assert manif.meta["raw_payload"][provider_key]["page_count"] == 500

            audit = (
                db.session.execute(
                    select(EntityAuditLog).where(
                        EntityAuditLog.entity_id == manif_id,
                        EntityAuditLog.change_type == "federation_merge_proposed",
                    )
                )
                .scalars()
                .first()
            )
            assert audit is not None
            assert audit.diff["provider"] == provider_key

    def test_untrusted_and_blocked_peers_ignored(self, app, frbr_catalog):
        with app.app_context():
            manif_id = frbr_catalog["manifestation_id"]
            manif = db.session.get(Manifestation, manif_id)

            remote_data = {"isbn13": "9780441172719", "page_count": 777}

            untrusted_res = federation_sync.sync_manifestation(
                manifestation=manif,
                remote_data=remote_data,
                domain="unknown.org",
                trust_level=TrustLevel.UNTRUSTED,
            )
            assert untrusted_res["status"] == "ignored"

            blocked_res = federation_sync.sync_manifestation(
                manifestation=manif,
                remote_data=remote_data,
                domain="bad.org",
                trust_level=TrustLevel.BLOCKED,
            )
            assert blocked_res["status"] == "ignored"
            assert manif.meta.get("page_count") is None


class TestFederationParentLinking:
    """Test suite for linking remote Manifestations to Expressions and Expressions to Works."""

    def test_link_manifestation_to_expression(self, app, frbr_catalog):
        with app.app_context():
            work2 = Work(title="Messiah", sort_title="Messiah")
            db.session.add(work2)
            db.session.flush()

            expr2 = Expression(work_id=work2.id, language="pl")
            db.session.add(expr2)
            db.session.commit()

            manif_id = frbr_catalog["manifestation_id"]
            manif = db.session.get(Manifestation, manif_id)
            assert manif.expression_id == frbr_catalog["expression_id"]

            federation_sync.link_manifestation_to_expression(
                manifestation_id=manif_id,
                expression_id=expr2.id,
            )

            db.session.refresh(manif)
            assert manif.expression_id == expr2.id

    def test_link_expression_to_work(self, app, frbr_catalog):
        with app.app_context():
            work2 = Work(title="Children of Dune", sort_title="Children of Dune")
            db.session.add(work2)
            db.session.commit()

            expr_id = frbr_catalog["expression_id"]
            expr = db.session.get(Expression, expr_id)
            assert expr.work_id == frbr_catalog["work_id"]

            federation_sync.link_expression_to_work(
                expression_id=expr_id,
                work_id=work2.id,
            )

            db.session.refresh(expr)
            assert expr.work_id == work2.id


class TestActivityPubInboxSyncIntegration:
    """Test suite for end-to-end ActivityPub Update activity through inbox pipeline."""

    def test_inbound_update_activity_trusted_peer(self, app, frbr_catalog):
        with app.app_context():
            inst = FederationInstance(
                domain="library.alpha.org",
                trust_level=TrustLevel.TRUSTED,
            )
            db.session.add(inst)
            db.session.flush()

            actor = FederationActor(
                actor_uri="https://library.alpha.org/actor/catalog",
                inbox_url="https://library.alpha.org/inbox",
                instance_id=inst.id,
            )
            db.session.add(actor)
            db.session.commit()

            activity = {
                "type": "Update",
                "actor": "https://library.alpha.org/actor/catalog",
                "object": {
                    "type": "Document",
                    "id": "https://library.alpha.org/manifestation/9780441172719",
                    "isbn13": "9780441172719",
                    "page_count": 890,
                    "publisher": "Alpha Scholastic",
                },
            }

            from app.core import federation_handlers

            handled = federation_handlers.handle_update(activity)
            assert handled is True

            manif_id = frbr_catalog["manifestation_id"]
            manif = db.session.get(Manifestation, manif_id)
            assert manif.publisher == "Alpha Scholastic"
            assert manif.meta.get("page_count") == 890
            assert manif.meta["_provenance"]["page_count"] == "federation:library.alpha.org"
