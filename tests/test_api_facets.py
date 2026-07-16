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
import pytest

from app.db.models import Expression, Item, Manifestation, Work, db


def test_items_genre_filter(client, normal_user_headers, app):
    with app.app_context():
        from app.db.models import User

        user = User.query.filter_by(email="test_user@iqoqo.local").first()

        # Create test data with different genres
        work1 = Work(title="Jazz Album", meta={"genre": "Jazz"})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type="audio")
        db.session.add(expr1)
        db.session.flush()
        man1 = Manifestation(expression_id=expr1.id)
        db.session.add(man1)
        db.session.flush()
        item1 = Item(manifestation_id=man1.id, owner_id=user.id, status="available")
        db.session.add(item1)

        work2 = Work(title="Rock Album", meta={"genre": "Rock"})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type="audio")
        db.session.add(expr2)
        db.session.flush()
        man2 = Manifestation(expression_id=expr2.id)
        db.session.add(man2)
        db.session.flush()
        item2 = Item(manifestation_id=man2.id, owner_id=user.id, status="available")
        db.session.add(item2)

        db.session.commit()

    resp = client.get("/api/items?genres=Jazz", headers=normal_user_headers)
    assert resp.status_code == 200
    data = resp.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Jazz Album"


def test_manifestations_genre_filter(client, normal_user_headers, app):
    with app.app_context():
        # Same data should work for manifestations
        work1 = Work(title="Jazz Album Release", meta={"genre": "Jazz"})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type="audio")
        db.session.add(expr1)
        db.session.flush()
        man1 = Manifestation(expression_id=expr1.id)
        db.session.add(man1)

        work2 = Work(title="Rock Album Release", meta={"genre": "Rock"})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type="audio")
        db.session.add(expr2)
        db.session.flush()
        man2 = Manifestation(expression_id=expr2.id)
        db.session.add(man2)

        db.session.commit()

    resp = client.get("/api/manifestations?genres=Rock", headers=normal_user_headers)
    assert resp.status_code == 200
    data = resp.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Rock Album Release"
