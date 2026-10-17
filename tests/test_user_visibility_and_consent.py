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
"""Tests for user item visibility defaults and federation opt-in consent."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.api.auth import generate_internal_jwt
from app.core import federation_keys
from app.db.core import MediaCategory, MediaFormat
from app.db.models import (
    Expression,
    FederationConsent,
    Item,
    Manifestation,
    Permission,
    Role,
    User,
    Work,
    db,
)


@pytest.fixture
def private_user_headers(app):
    """Fixture providing headers for a user with default_item_visibility='private'."""
    with app.app_context():
        user = User(
            email="private_user@iqoqo.local",
            display_name="Private User",
            public_username="privateuser",
            visibility="private",
            default_item_visibility="private",
        )
        user.set_password("secret123")
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
        write_perm = Permission.query.filter_by(name="write:item").first()
        if not write_perm:
            write_perm = Permission(name="write:item")
            db.session.add(write_perm)
        if write_perm not in role.permissions:
            role.permissions.append(write_perm)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()

        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}", "User-ID": str(user.id)}


@pytest.fixture
def public_user_headers(app):
    """Fixture providing headers for a user with default_item_visibility='public'."""
    with app.app_context():
        user = User(
            email="public_user@iqoqo.local",
            display_name="Public User",
            public_username="publicuser",
            visibility="public",
            default_item_visibility="public",
        )
        user.set_password("secret123")
        role = Role.query.filter_by(name="user").first()
        if not role:
            role = Role(name="user")
            db.session.add(role)
        write_perm = Permission.query.filter_by(name="write:item").first()
        if not write_perm:
            write_perm = Permission(name="write:item")
            db.session.add(write_perm)
        if write_perm not in role.permissions:
            role.permissions.append(write_perm)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()

        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}", "User-ID": str(user.id)}


@pytest.fixture
def sample_test_manifestation(app):
    """Fixture providing a persisted test manifestation."""
    with app.app_context():
        work = Work(title="Visibility Test Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type=MediaCategory.TEXT)
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780000000011",
            meta={"format": MediaFormat.BOOK, "title": "Visibility Test Manifestation"},
        )
        db.session.add(manif)
        db.session.commit()
        return manif.id


class TestUserVisibilityDefaults:
    """Test default item visibility scoping upon creation and scanning."""

    def test_user_model_default_item_visibility_attribute(self, app):
        """User model defaults to default_item_visibility='private'."""
        with app.app_context():
            u = User(email="new_default@iqoqo.local")
            assert u.default_item_visibility == "private"
            data = u.to_dict()
            assert data["default_item_visibility"] == "private"

    def test_update_default_item_visibility_via_profile(self, client, private_user_headers):
        """Updating default_item_visibility via PATCH /api/profile/settings."""
        headers = {"Authorization": private_user_headers["Authorization"]}
        res = client.patch("/api/profile/settings", json={"default_item_visibility": "public"}, headers=headers)
        assert res.status_code == 200
        assert res.get_json()["data"]["default_item_visibility"] == "public"

        # Invalid value rejected
        res_invalid = client.patch("/api/profile/settings", json={"default_item_visibility": "invalid"}, headers=headers)
        assert res_invalid.status_code == 400

    def test_item_inherits_private_visibility_on_scan(self, client, private_user_headers, sample_test_manifestation):
        """User with default_item_visibility='private' scans barcode -> Item is_public=False."""
        headers = {"Authorization": private_user_headers["Authorization"]}

        with patch("app.api.scanner._record_scan_telemetry"):
            res = client.post(
                "/api/scan",
                json={
                    "barcode": "9780000000011",
                    "manifestation_id": sample_test_manifestation,
                    "policy": "inventory",
                },
                headers=headers,
            )
            assert res.status_code == 201
            item_id = res.get_json()["data"]["item_id"]

        with client.application.app_context():
            item = db.session.get(Item, item_id)
            assert item is not None
            assert item.is_hidden is True
            assert item.is_public is False
            dict_rep = item.to_dict()
            assert dict_rep["is_hidden"] is True
            assert dict_rep["is_public"] is False

    def test_item_inherits_public_visibility_on_scan(self, client, public_user_headers, sample_test_manifestation):
        """User with default_item_visibility='public' scans barcode -> Item is_public=True."""
        headers = {"Authorization": public_user_headers["Authorization"]}

        with patch("app.api.scanner._record_scan_telemetry"):
            res = client.post(
                "/api/scan",
                json={
                    "barcode": "9780000000011",
                    "manifestation_id": sample_test_manifestation,
                    "policy": "inventory",
                },
                headers=headers,
            )
            assert res.status_code == 201
            item_id = res.get_json()["data"]["item_id"]

        with client.application.app_context():
            item = db.session.get(Item, item_id)
            assert item is not None
            assert item.is_hidden is False
            assert item.is_public is True

    def test_create_item_inherits_user_default_visibility(self, client, private_user_headers, sample_test_manifestation):
        """Manual item creation inherits default_item_visibility."""
        headers = {"Authorization": private_user_headers["Authorization"]}
        res = client.post(
            "/api/items",
            json={"manifestation_id": sample_test_manifestation},
            headers=headers,
        )
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["is_hidden"] is True
        assert data["is_public"] is False

    def test_create_item_explicit_override_visibility(self, client, private_user_headers, sample_test_manifestation):
        """Explicit is_public / is_hidden in payload overrides user default."""
        headers = {"Authorization": private_user_headers["Authorization"]}
        res = client.post(
            "/api/items",
            json={"manifestation_id": sample_test_manifestation, "is_public": True},
            headers=headers,
        )
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["is_hidden"] is False
        assert data["is_public"] is True


class TestFederationConsent:
    """Test Federation Consent API and actor keypair generation."""

    def test_get_federation_consent_default(self, client, private_user_headers):
        """GET /api/v1/profile/federation-consent returns default false values when unconfigured."""
        headers = {"Authorization": private_user_headers["Authorization"]}
        res = client.get("/api/v1/profile/federation-consent", headers=headers)
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["federated_profile"] is False
        assert json_data["data"]["federated_collection"] is False

    def test_update_federation_consent_generates_keys(self, client, private_user_headers):
        """Updating consent to opt in automatically generates actor RSA keypair."""
        headers = {"Authorization": private_user_headers["Authorization"]}
        user_id = private_user_headers["User-ID"]

        res = client.put(
            "/api/v1/profile/federation-consent",
            json={"federated_profile": True, "federated_collection": True},
            headers=headers,
        )
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["federated_profile"] is True
        assert json_data["data"]["federated_collection"] is True

        # Verify key was generated
        with client.application.app_context():
            u = db.session.get(User, uuid.UUID(user_id))
            assert u.federation_public_key is not None
            assert u.federation_key_id is not None
            assert "BEGIN PUBLIC KEY" in u.federation_public_key

    def test_webfinger_respects_federation_consent(self, client, private_user_headers):
        """WebFinger returns 404 for non-consented user and 200 after consent."""
        headers = {"Authorization": private_user_headers["Authorization"]}
        user_id = private_user_headers["User-ID"]

        with client.application.app_context():
            u = db.session.get(User, uuid.UUID(user_id))
            username = u.public_username

        # 1. Non-consented user returns 404
        wf_res = client.get(f"/api/federation/webfinger?resource=acct:{username}@localhost")
        assert wf_res.status_code == 404

        # 2. Opt in
        client.put(
            "/api/v1/profile/federation-consent",
            json={"federated_profile": True},
            headers=headers,
        )

        # 3. WebFinger query now succeeds
        wf_res_after = client.get(f"/api/federation/webfinger?resource=acct:{username}@localhost")
        assert wf_res_after.get_json()["subject"].startswith(f"acct:{username}@")
