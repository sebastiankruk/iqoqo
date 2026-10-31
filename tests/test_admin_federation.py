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
"""Tests for administrative federation management endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.permissions import PermissionName
from app.db import db
from app.db.auth import Permission, Role, User
from app.db.federation import FederationActivity, FederationInstance, TrustLevel


class TestAdminFederationEndpoints:
    """Test suite for /api/v1/admin/federation/* routes."""

    def test_instances_permission_denied(self, client, normal_user_headers):
        resp = client.get("/api/v1/admin/federation/instances", headers=normal_user_headers)
        assert resp.status_code == 403

    def test_instances_unauthorized(self, client):
        resp = client.get("/api/v1/admin/federation/instances")
        assert resp.status_code in (401, 302)

    def test_get_instances_list(self, client, admin_headers, app):
        with app.app_context():
            inst1 = FederationInstance(domain="alpha.fed.org", trust_level=TrustLevel.TRUSTED)
            inst2 = FederationInstance(domain="beta.fed.org", trust_level=TrustLevel.UNTRUSTED)
            db.session.add_all([inst1, inst2])
            db.session.commit()

        resp = client.get("/api/v1/admin/federation/instances", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        domains = [i["domain"] for i in data["data"]]
        assert "alpha.fed.org" in domains
        assert "beta.fed.org" in domains

    def test_add_instance_success(self, client, admin_headers, app):
        with patch("app.core.federation_discovery.safe_get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp

            resp = client.post(
                "/api/v1/admin/federation/instances",
                headers=admin_headers,
                json={"domain": "new-peer.fed.org"},
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["success"] is True
            assert data["data"]["domain"] == "new-peer.fed.org"
            assert data["data"]["trust_level"] == TrustLevel.UNTRUSTED

    def test_update_instance_trust_level(self, client, admin_headers, app):
        with app.app_context():
            inst = FederationInstance(domain="gamma.fed.org", trust_level=TrustLevel.UNTRUSTED)
            db.session.add(inst)
            db.session.commit()
            inst_id = inst.id

        resp = client.put(
            f"/api/v1/admin/federation/instances/{inst_id}/trust",
            headers=admin_headers,
            json={"trust_level": "trusted"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["trust_level"] == "trusted"

        # Verify DB updated
        with app.app_context():
            updated = db.session.get(FederationInstance, inst_id)
            assert updated.trust_level == TrustLevel.TRUSTED

    def test_update_instance_trust_invalid(self, client, admin_headers, app):
        with app.app_context():
            inst = FederationInstance(domain="delta.fed.org", trust_level=TrustLevel.UNTRUSTED)
            db.session.add(inst)
            db.session.commit()
            inst_id = inst.id

        resp = client.put(
            f"/api/v1/admin/federation/instances/{inst_id}/trust",
            headers=admin_headers,
            json={"trust_level": "super_trusted"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "invalid trust_level" in data["error"].lower()

    def test_delete_instance(self, client, admin_headers, app):
        with app.app_context():
            inst = FederationInstance(domain="omega.fed.org", trust_level=TrustLevel.BLOCKED)
            db.session.add(inst)
            db.session.commit()
            inst_id = inst.id

        resp = client.delete(f"/api/v1/admin/federation/instances/{inst_id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True

        with app.app_context():
            assert db.session.get(FederationInstance, inst_id) is None

    def test_get_federation_activities(self, client, admin_headers, app):
        with app.app_context():
            act1 = FederationActivity(
                actor_uri="https://peer.org/actor",
                activity_type="Update",
                direction="inbound",
                status="delivered",
            )
            act2 = FederationActivity(
                actor_uri="https://local.org/actor/me",
                activity_type="Create",
                direction="outbound",
                status="queued",
            )
            db.session.add_all([act1, act2])
            db.session.commit()

        resp = client.get(
            "/api/v1/admin/federation/activities?page=1&per_page=10",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "pagination" in data
        assert len(data["data"]) >= 2

        # Filter by direction
        filtered_resp = client.get(
            "/api/v1/admin/federation/activities?direction=inbound",
            headers=admin_headers,
        )
        assert filtered_resp.status_code == 200
        filtered_data = filtered_resp.get_json()
        assert all(a["direction"] == "inbound" for a in filtered_data["data"])

    def test_get_key_fingerprint(self, client, admin_headers, app):
        resp = client.get("/api/v1/admin/federation/key-fingerprint", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "fingerprint" in data["data"]
