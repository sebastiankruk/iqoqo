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
"""Tests for FEDERATION_HEAD_MODE read-only showcase instance behavior (C112)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.api.federation_guard import FEDERATION_HEAD_READONLY_MESSAGE
from app.db.models import Expression, InstanceSettings, Item, Manifestation, User, UserWorkIntent, Work, db


@pytest.fixture
def enable_federation_head(app):
    """Enable FEDERATION_HEAD_MODE and FEDERATION_ENABLED for the test duration."""
    with app.app_context():
        InstanceSettings.set_value("FEDERATION_ENABLED", True)
        InstanceSettings.set_value("FEDERATION_HEAD_MODE", True)
        db.session.commit()
    yield
    with app.app_context():
        InstanceSettings.set_value("FEDERATION_HEAD_MODE", False)
        db.session.commit()


@pytest.fixture
def sample_manifestation(app):
    """Seed an isolated FRBR hierarchy with Manifestation and ISBN."""
    with app.app_context():
        work = Work(title="The Art of Unix Programming", meta={"authors": ["Eric S. Raymond"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780131429017",
            meta={"title": "The Art of Unix Programming"},
            publisher="Addison-Wesley",
        )
        db.session.add(manif)
        db.session.commit()
        return manif.id


def test_public_config_advertises_federation_head_mode(client, enable_federation_head):
    """GET /api/config returns federation_head_mode: true."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["federation_head_mode"] is True
    assert "version" in data


def test_nodeinfo_metadata_advertises_federation_head(client, enable_federation_head):
    """GET /api/federation/nodeinfo/2.1 includes metadata.federationHead = true."""
    resp = client.get("/api/federation/nodeinfo/2.1")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["metadata"]["federationHead"] is True


def test_physical_item_creation_rejected_on_federation_head(client, enable_federation_head, normal_user_headers, sample_manifestation):
    """POST /api/items returns 403 Forbidden on federation head mode."""
    resp = client.post(
        "/api/items",
        json={"manifestation_id": sample_manifestation, "collection_status": "available"},
        headers=normal_user_headers,
    )
    assert resp.status_code == 403
    payload = resp.get_json()
    assert payload["code"] == 403
    assert FEDERATION_HEAD_READONLY_MESSAGE in payload["error"]


def test_manual_item_creation_rejected_on_federation_head(client, enable_federation_head, normal_user_headers):
    """POST /api/items/manual returns 403 Forbidden on federation head mode."""
    resp = client.post(
        "/api/items/manual",
        json={"Title": "Sample Book", "Authors": ["Alice Doe"], "Format": "book"},
        headers=normal_user_headers,
    )
    assert resp.status_code == 403
    payload = resp.get_json()
    assert payload["code"] == 403
    assert FEDERATION_HEAD_READONLY_MESSAGE in payload["error"]


def test_bulk_item_creation_rejected_on_federation_head(client, enable_federation_head, normal_user_headers, sample_manifestation):
    """POST /api/items/bulk returns 403 Forbidden on federation head mode."""
    resp = client.post(
        "/api/items/bulk",
        json={"manifestation_ids": [sample_manifestation], "collection_status": "available"},
        headers=normal_user_headers,
    )
    assert resp.status_code == 403
    payload = resp.get_json()
    assert payload["code"] == 403
    assert FEDERATION_HEAD_READONLY_MESSAGE in payload["error"]


def test_scan_barcode_physical_item_rejected_on_federation_head(client, enable_federation_head, normal_user_headers, sample_manifestation):
    """POST /api/scan with policy='inventory' returns 403 Forbidden."""
    resp = client.post(
        "/api/scan",
        json={"manifestation_id": sample_manifestation, "policy": "inventory", "collection_status": "available"},
        headers=normal_user_headers,
    )
    assert resp.status_code == 403
    payload = resp.get_json()
    assert payload["code"] == 403
    assert FEDERATION_HEAD_READONLY_MESSAGE in payload["error"]


def test_wishlist_additions_allowed_on_federation_head(client, app, enable_federation_head, normal_user_headers, sample_manifestation):
    """POST /api/wishlist and POST /api/scan with policy='wishlist' remain allowed on federation head."""
    # 1. Direct wishlist POST
    with app.app_context():
        manif = db.session.get(Manifestation, sample_manifestation)
        work_id = manif.expression.work_id
        expr_id = manif.expression.id

    resp = client.post(
        "/api/wishlist",
        json={"work_id": work_id, "expression_id": expr_id, "status": "want_to_read"},
        headers=normal_user_headers,
    )
    assert resp.status_code in (200, 201)

    # 2. Scanner wishlist policy POST
    resp_scan = client.post(
        "/api/scan",
        json={"manifestation_id": sample_manifestation, "policy": "wishlist", "collection_status": "wish_list"},
        headers=normal_user_headers,
    )
    assert resp_scan.status_code in (200, 201)
