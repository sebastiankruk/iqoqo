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
    """Assert that PUT /api/items/{virtual_id} rejects physical trait updates."""
    with app.app_context():
        user = User.query.first()
        user_id = user.id

    virtual_item_id = _make_virtual_item(app, user_id)

    # Attempting to mutate or treat a virtual placeholder as a physical shelf item
    response = client.put(f"/api/items/{virtual_item_id}", json={"barcode": "1234567890", "condition": "Mint"}, headers=normal_user_headers)

    # Must be rejected due to FRBR structural violation
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "FRBR Ontology Violation" in data["error"] or "cannot accept physical state mutations" in data["error"]


def test_payload_schema_rejects_id_zero():
    """Assert that payload schemas explicitly reject id: 0 with a validation error."""
    with pytest.raises(ValidationError) as exc_info:
        ItemUpdateSchema(id=0, status="read")
    assert "Item identifier cannot be zero" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        ItemCreateSchema(id=0, status="read")
    assert "Item identifier cannot be zero" in str(exc_info.value)
