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

"""
Unit tests validating FRBR structural boundaries and schema rules for v0.7.8.
"""

import secrets

import pytest
from pydantic import ValidationError

from app.api.schemas import ItemCreateSchema, ItemUpdateSchema
from app.db.models import User, UserWorkIntent, Work, db


def _make_virtual_item(app, user_id, status="want_to_read", is_hidden=False):
    """Helper: create a Work + UserWorkIntent, return virtual_item_id."""
    with app.app_context():
        work = Work(title=f"078 Boundary Work {secrets.token_hex(4)}", meta={"authors": ["Test"]})
        db.session.add(work)
        db.session.flush()
        intent = UserWorkIntent(user_id=user_id, work_id=work.id, status=status, is_hidden=is_hidden)
        db.session.add(intent)
        db.session.commit()
        return -intent.id


def test_put_virtual_item_boundary(client, app, normal_user_headers):
    """Assert that PUT /api/items/{negative_id} returns 404 (negative IDs no longer accepted)."""
    with app.app_context():
        user = User.query.first()
        user_id = user.id

    virtual_item_id = _make_virtual_item(app, user_id)

    # Negative IDs are no longer routed through /api/items.
    # The URL converter rejects them, resulting in 404.
    response = client.put(f"/api/items/{virtual_item_id}", json={"barcode": "1234567890", "condition": "Mint"}, headers=normal_user_headers)

    # Must be rejected - negative IDs are not valid for /api/items
    assert response.status_code == 404


def test_payload_schema_rejects_id_zero():
    """Assert that payload schemas explicitly reject id: 0 with a validation error."""
    with pytest.raises(ValidationError) as exc_info:
        ItemUpdateSchema(id=0, status="read")
    assert "Item identifier must be a positive integer" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        ItemCreateSchema(id=0, status="read")
    assert "Item identifier must be a positive integer" in str(exc_info.value)


def test_lego_item_update_frbr_boundary(client, app, normal_user_headers):
    """Assert that PUT /api/items/<id> stores LEGO copy attributes strictly in item.meta, not manifestation.meta."""
    from app.db.models import Expression, Item, Manifestation, Work

    with app.app_context():
        user = User.query.first()
        work = Work(title="LEGO Test Set", meta={"theme": "Technic"})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work=work, language="en", content_type="lego")
        db.session.add(expr)
        db.session.flush()

        man = Manifestation(expression=expr, format="standard_set", format_type="standard_set", meta={"set_number": "42100"})
        db.session.add(man)
        db.session.flush()

        item = Item(manifestation=man, owner_id=user.id, status="want_to_build", collection_status="available", meta={})
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        man_id = man.id

    payload = {
        "build_status": "incomplete",
        "missing_pieces_count": 5,
        "instructions_included": False,
        "box_condition": "damaged",
    }
    resp = client.put(f"/api/items/{item_id}", json=payload, headers=normal_user_headers)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["build_status"] == "incomplete"
    assert data["missing_pieces_count"] == 5
    assert data["instructions_included"] is False
    assert data["box_condition"] == "damaged"

    with app.app_context():
        updated_item = db.session.get(Item, item_id)
        assert updated_item.meta["build_status"] == "incomplete"
        assert updated_item.meta["missing_pieces_count"] == 5
        assert updated_item.meta["instructions_included"] is False
        assert updated_item.meta["box_condition"] == "damaged"

        parent_man = db.session.get(Manifestation, man_id)
        assert "build_status" not in parent_man.meta
        assert "missing_pieces_count" not in parent_man.meta
        assert "instructions_included" not in parent_man.meta
        assert "box_condition" not in parent_man.meta
