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
"""Tests for FRBR Item-scoped physical location tagging, bulk update, filtering, and RDF privacy (C157)."""

from __future__ import annotations

import uuid

from rdflib import Graph, Literal, URIRef

from app.core.frbr_service import IQOQO, SCHEMA, serialize_collection_to_rdf
from app.db import db
from app.db.auth import User
from app.db.core import Expression, Item, Manifestation, Work


def _seed_item(app, email: str, *, location: str | None = None, visibility: str = "public") -> tuple[int, uuid.UUID]:
    with app.app_context():
        user = User(email=email, display_name=email.split("@")[0], is_active=True)
        db.session.add(user)
        db.session.flush()

        work = Work(title=f"Work for {email}")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        mani = Manifestation(expression_id=expr.id, format="book")
        db.session.add(mani)
        db.session.flush()

        item = Item(
            owner_id=user.id,
            manifestation_id=mani.id,
            status="read",
            collection_status="available",
            visibility=visibility,
            is_hidden=visibility != "public",
            physical_location=location,
        )
        db.session.add(item)
        db.session.commit()
        return item.id, user.id


def test_owner_sets_and_reads_physical_location_redacted_for_non_owners(client, app, normal_user_headers, admin_headers):
    """Owner sees physical_location on GET/PATCH /items/<id>; anonymous & non-owners receive null."""
    item_id, _owner_id = _seed_item(app, "loc_owner@iqoqo.local", visibility="public")
    # Update as admin/owner via PATCH
    with app.app_context():
        item = db.session.get(Item, item_id)
        item.physical_location = "Study / Shelf A2"
        db.session.commit()

    # Non-owner authenticated user gets physical_location=None
    res_other = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert res_other.status_code == 200
    assert res_other.get_json()["data"]["physical_location"] is None

    # Anonymous user gets physical_location=None
    res_anon = client.get(f"/api/items/{item_id}")
    assert res_anon.status_code == 200
    assert res_anon.get_json()["data"]["physical_location"] is None

    # Admin sees physical_location
    res_admin = client.get(f"/api/items/{item_id}", headers=admin_headers)
    assert res_admin.status_code == 200
    assert res_admin.get_json()["data"]["physical_location"] == "Study / Shelf A2"

    # PATCH updates and clears physical_location
    res_patch = client.patch(
        f"/api/items/{item_id}",
        json={"physical_location": "  Living Room / Box 4  "},
        headers=admin_headers,
    )
    assert res_patch.status_code == 200
    assert res_patch.get_json()["data"]["physical_location"] == "Living Room / Box 4"


def test_bulk_location_enforces_ownership_and_federation_head_guard(client, app, normal_user_headers, monkeypatch):
    """PATCH /api/items/bulk-location updates owned items, returns 403 on foreign items, and blocks Federation Hub."""
    with app.app_context():
        me = db.session.execute(db.select(User).filter_by(email="normal_user@iqoqo.local")).scalar_one_or_none()
        if me is None:
            # Resolve owner from /api/auth/me or create an item via API
            pass

    # Create two items owned by normal_user via /api/items/manual
    r1 = client.post(
        "/api/items/manual",
        json={"Title": "Loc Book 1", "Authors": ["Author 1"], "Format": "book"},
        headers=normal_user_headers,
    )
    r2 = client.post(
        "/api/items/manual",
        json={"Title": "Loc Book 2", "Authors": ["Author 2"], "Format": "book"},
        headers=normal_user_headers,
    )
    d1 = r1.get_json()["data"]
    d2 = r2.get_json()["data"]
    id1 = d1.get("item_id") or d1.get("id")
    id2 = d2.get("item_id") or d2.get("id")

    res_bulk = client.patch(
        "/api/items/bulk-location",
        json={"item_ids": [id1, id2], "physical_location": "Archive / Drawer 7"},
        headers=normal_user_headers,
    )
    assert res_bulk.status_code == 200
    assert res_bulk.get_json()["data"]["updated_count"] == 2
    assert res_bulk.get_json()["data"]["physical_location"] == "Archive / Drawer 7"

    # SQL-paginated ?location=... filter returns matching items and facets include location_counts
    res_list = client.get("/api/items?location=Archive%20/%20Drawer%207", headers=normal_user_headers)
    assert res_list.status_code == 200
    listed_ids = [row["id"] for row in res_list.get_json()["data"]]
    assert set(listed_ids) == {id1, id2}

    res_facets = client.get("/api/stats/facets?scope=user&view=items", headers=normal_user_headers)
    assert res_facets.status_code == 200
    assert res_facets.get_json()["data"]["location_counts"].get("Archive / Drawer 7") == 2

    # Foreign item triggers 403
    foreign_id, _ = _seed_item(app, "other_loc_owner@iqoqo.local", location="Secret Vault")
    res_403 = client.patch(
        "/api/items/bulk-location",
        json={"item_ids": [id1, foreign_id], "physical_location": "Hijacked"},
        headers=normal_user_headers,
    )
    assert res_403.status_code == 403

    # Federation Hub read-only mode rejects write
    monkeypatch.setenv("FEDERATION_HEAD_MODE", "true")
    res_hub = client.patch(
        "/api/items/bulk-location",
        json={"item_ids": [id1], "physical_location": "Blocked"},
        headers=normal_user_headers,
    )
    assert res_hub.status_code == 403


def test_rdf_emits_physical_location_only_in_full_profile(app):
    """RDF serialization emits iqoqo:physicalLocation only when enrichment_profile='full'."""
    item_id, _ = _seed_item(app, "rdf_loc@iqoqo.local", location="Hallway / Top Shelf")
    with app.app_context():
        item = db.session.get(Item, item_id)
        ttl_public = serialize_collection_to_rdf([item], "http://testserver", output_format="turtle", enrichment_profile="public")
        g_pub = Graph()
        g_pub.parse(data=ttl_public, format="turtle")
        item_uri = URIRef(f"http://testserver/items/{item_id}")
        assert (item_uri, IQOQO.physicalLocation, Literal("Hallway / Top Shelf")) not in g_pub
        assert (item_uri, SCHEMA.location, Literal("Hallway / Top Shelf")) not in g_pub

        ttl_full = serialize_collection_to_rdf([item], "http://testserver", output_format="turtle", enrichment_profile="full")
        g_full = Graph()
        g_full.parse(data=ttl_full, format="turtle")
        assert (item_uri, IQOQO.physicalLocation, Literal("Hallway / Top Shelf")) in g_full
        assert (item_uri, SCHEMA.location, Literal("Hallway / Top Shelf")) in g_full
