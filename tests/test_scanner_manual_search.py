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
"""Tests for manual search candidate ingestion and Item.local_barcode owner scoping."""

import json


def test_scan_manual_search_with_meta_succeeds_without_barcode(client, normal_user_headers):
    """Verify adding an item found via text search with payload.meta succeeds when barcode is empty."""
    payload = {
        "barcode": "",
        "manifestation_id": None,
        "format": "book",
        "collection_status": "available",
        "policy": "inventory",
        "meta": {
            "title": "The Hitchhiker's Guide to the Galaxy",
            "author": "Douglas Adams",
            "data_source": "search",
            "publication_year": 1979,
        },
    }

    res = client.post(
        "/api/scan",
        data=json.dumps(payload),
        headers=normal_user_headers,
        content_type="application/json",
    )
    data = res.get_json()
    assert res.status_code in (200, 201), f"Scan failed: {data}"
    assert data["success"] is True
    assert data["data"]["manifestation_id"] is not None


def test_lookup_local_barcode_cross_user_isolation(client, normal_user_headers, admin_headers, app):
    """Verify scanning another user's local_barcode does not leak their private item."""
    from app.db.models import Expression, Manifestation, Work, db

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
        sample_manifestation = manif.id

    local_code = "SHELF-TAG-SECRET-123"
    create_res = client.post(
        "/api/items",
        data=json.dumps(
            {
                "manifestation_id": sample_manifestation,
                "local_barcode": local_code,
                "status": "want_to_read",
            }
        ),
        headers=admin_headers,
        content_type="application/json",
    )
    assert create_res.status_code == 201, f"Create item failed: {create_res.get_json()}"

    # Normal user looks up admin's local barcode
    lookup_res = client.get(f"/api/lookup/{local_code}", headers=normal_user_headers)
    if lookup_res.status_code == 200:
        data = lookup_res.get_json()["data"]
        # Should not match admin's item
        assert data.get("local_barcode") != local_code
        assert data.get("already_in_collection") is False
    else:
        # Not found locally for normal user, which is correct
        assert lookup_res.status_code == 404
