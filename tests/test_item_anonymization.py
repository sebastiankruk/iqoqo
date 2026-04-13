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

import pytest

from app.db.models import Expression, Item, Manifestation, Role, User, Work, db


def test_item_detail_anonymization_for_guests(client, app):
    with app.app_context():
        work = Work(title="Secure Book", meta={})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        owner = User(email="owner@example.com", display_name="Owner")
        db.session.add(owner)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["owner_id"] == "Unavailable"


def test_item_detail_anonymization_for_other_user(client, normal_user_headers, app):
    with app.app_context():
        owner = User(email="owner_other@example.com", display_name="Owner Other")
        db.session.add(owner)
        db.session.flush()

        work = Work(title="Other Users Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["owner_id"] == "Unavailable"


def test_item_modification_blocked_for_non_owner(client, normal_user_headers, app):
    with app.app_context():
        owner = User(email="owner_blocked@example.com", display_name="Owner Blocked")
        db.session.add(owner)
        db.session.flush()

        work = Work(title="Test Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.put(f"/api/items/{item_id}", json={"status": "lost"}, headers=normal_user_headers)
    assert response.status_code == 403
    assert response.get_json()["error"] == "Forbidden"


def test_owner_can_view_own_item(client, normal_user_headers, app):
    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").first()

        work = Work(title="My Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=user.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["owner_id"] != "Unavailable"


def test_admin_can_view_any_item(client, admin_headers, app):
    with app.app_context():
        owner = User(email="owner_admin@example.com", display_name="Owner Admin")
        db.session.add(owner)
        db.session.flush()

        work = Work(title="Admin Test Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.get(f"/api/items/{item_id}", headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["owner_id"] != "Unavailable"


def test_owner_can_modify_own_item(client, normal_user_headers, app):
    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").first()

        work = Work(title="My Mod Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=user.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.put(f"/api/items/{item_id}", json={"status": "reading"}, headers=normal_user_headers)
    assert response.status_code == 200


def test_item_detail_includes_owner_count(client, normal_user_headers, app):
    with app.app_context():
        user = User(email="owner_count_test@example.com", display_name="Owner Count Test")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Owner Count Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item1 = Item(manifestation_id=manif.id, owner_id=user.id, status="available", meta={})
        db.session.add(item1)

        other_user = User(email="other_owner@example.com", display_name="Other Owner")
        db.session.add(other_user)
        db.session.flush()
        item2 = Item(manifestation_id=manif.id, owner_id=other_user.id, status="available", meta={})
        db.session.add(item2)
        db.session.commit()

        item_id = item1.id

    response = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert "owner_count" in data["data"]
    assert data["data"]["owner_count"] == 2


def test_manifestation_detail_includes_owner_count(client, app):
    with app.app_context():
        work = Work(title="Manifestation Owner Count", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        owner1 = User(email="manif_owner1@example.com", display_name="Manif Owner 1")
        db.session.add(owner1)
        db.session.flush()
        owner2 = User(email="manif_owner2@example.com", display_name="Manif Owner 2")
        db.session.add(owner2)
        db.session.flush()

        item1 = Item(manifestation_id=manif.id, owner_id=owner1.id, status="available", meta={})
        item2 = Item(manifestation_id=manif.id, owner_id=owner2.id, status="lent", meta={})
        db.session.add_all([item1, item2])
        db.session.commit()

        manif_id = manif.id

    response = client.get(f"/api/manifestations/{manif_id}")
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert "owner_count" in data["data"]
    assert data["data"]["owner_count"] == 2


def test_admin_can_see_owner_name(client, admin_headers, app):
    with app.app_context():
        owner = User(email="owner_admin_test@example.com", display_name="Admin Test Owner")
        db.session.add(owner)
        db.session.flush()

        work = Work(title="Admin Owner Name Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.get(f"/api/items/{item_id}", headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["owner_name"] == "Admin Test Owner"


def test_regular_user_without_read_owners_cannot_see_owner_name(client, normal_user_headers, app):
    with app.app_context():
        owner = User(email="owner_hidden@example.com", display_name="Hidden Owner")
        db.session.add(owner)
        db.session.flush()

        work = Work(title="Hidden Owner Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.get(f"/api/items/{item_id}", headers=normal_user_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["owner_name"] is None
    assert data["data"]["owner_id"] == "Unavailable"


def test_admin_can_delete_any_item(client, admin_headers, app):
    with app.app_context():
        owner = User(email="owner_delete@example.com", display_name="Owner Delete")
        db.session.add(owner)
        db.session.flush()

        work = Work(title="Delete Test Book", meta={})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()

        item_id = item.id

    response = client.delete(f"/api/items/{item_id}", headers=admin_headers)
    assert response.status_code == 200

