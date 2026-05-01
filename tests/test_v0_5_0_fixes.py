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

import json
from unittest.mock import MagicMock, patch

import pytest

from app.db.models import Manifestation, Permission, db
from app.utils.bgg import clean_bgg_query
from app.utils.llm_covers import is_placeholder


def test_profile_no_trailing_slash_redirect_fix(client, normal_user_headers):
    """
    Test that /api/profile (without trailing slash) returns 200 OK
    instead of a 308 redirect, thanks to strict_slashes=False.
    """
    # GET should already work due to how Flask handles it, but let's be sure.
    response = client.get("/api/profile", headers=normal_user_headers)
    assert response.status_code == 200

    # PUT was the one failing with 308 in the browser/axios
    response = client.put("/api/profile", headers=normal_user_headers, json={"display_name": "Test Name"})
    assert response.status_code == 200
    assert response.json["display_name"] == "Test Name"


def test_scan_by_manifestation_id(client, normal_user_headers):
    """
    Test that we can add an item to the collection using a manifestation_id directly.
    """
    from app.core import frbr_service

    # 1. Create a valid FRBR hierarchy
    work = frbr_service.create_work(title="Test Work")
    expr = frbr_service.create_expression(work_id=work.id, content_type="text")
    manif = frbr_service.create_manifestation(expression_id=expr.id, meta={"title": "Test Game"})

    m_id = manif.id

    # 2. Add via ID
    payload = {"manifestation_id": m_id, "format": "boardgame"}
    response = client.post("/api/scan", json=payload, headers=normal_user_headers)

    assert response.status_code == 201
    assert response.json["data"]["manifestation_id"] == m_id
    assert response.json["data"]["title"] == "Test Game"


def test_bgg_query_cleaning_logic():
    """Unit test for BGG query cleaning regex."""
    assert clean_bgg_query("Brass: Pittsburgh (2027)") == "Brass: Pittsburgh"
    assert clean_bgg_query("Catan (Big Box)") == "Catan"
    assert clean_bgg_query("Dixit [Limited Edition]") == "Dixit"
    assert clean_bgg_query("Standard Title") == "Standard Title"


def test_llm_placeholder_detection_logic():
    """Unit test for LLM placeholder detection."""
    assert is_placeholder("Unknown") is True
    assert is_placeholder("None") is True
    assert is_placeholder("Null") is True
    assert is_placeholder("  unknown author  ") is True
    assert is_placeholder("The Great Gatsby") is False
    assert is_placeholder("") is True
    assert is_placeholder(None) is True


def test_permission_descriptions_visible_in_api(client, admin_headers):
    """
    Verify that permission descriptions added to YAML are returned by the admin API.
    """
    # 1. Ensure at least one permission has a description in the DB
    perm = Permission.query.first()
    if not perm:
        perm = Permission(name="test:perm", description="Self-explanatory")
        db.session.add(perm)
        db.session.commit()

    perm.description = "Test description"
    db.session.commit()

    # 2. Call admin permissions API
    response = client.get("/api/v1/admin/permissions", headers=admin_headers)
    assert response.status_code == 200

    found = False
    # Correctly iterate over the 'data' list
    for p in response.json["data"]:
        if p["name"] == perm.name:
            assert p["description"] == "Test description"
            found = True
            break
    assert found is True
