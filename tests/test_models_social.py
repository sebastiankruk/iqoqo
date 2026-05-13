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
"""Tests for social and sharing models."""

import pytest
from app.db.models import User, SharedCollection, db
from sqlalchemy.exc import IntegrityError

def test_shared_collection_token_generation(app):
    with app.app_context():
        user = User(email="token@iqoqo.local")
        db.session.add(user)
        db.session.commit()
        
        sc = SharedCollection(user_id=user.id, name="Test Collection")
        db.session.add(sc)
        db.session.commit()
        
        assert sc.share_token is not None
        assert len(sc.share_token) == 36

def test_public_username_uniqueness(app):
    with app.app_context():
        u1 = User(email="u1@iqoqo.local", public_username="same")
        db.session.add(u1)
        db.session.commit()
        
        u2 = User(email="u2@iqoqo.local", public_username="same")
        db.session.add(u2)
        with pytest.raises(IntegrityError):
            db.session.commit()

def test_cascade_delete_user(app):
    with app.app_context():
        user = User(email="cascade@iqoqo.local")
        db.session.add(user)
        db.session.flush()
        
        sc = SharedCollection(user_id=user.id, name="Delete Me")
        db.session.add(sc)
        db.session.commit()
        sc_id = sc.id
        
        db.session.delete(user)
        db.session.commit()
        
        assert db.session.get(SharedCollection, sc_id) is None
