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
"""Tests for SPARQL federated access rights and privacy scoping."""

import uuid

import pytest

from app.core.item_access import is_item_publicly_visible
from app.core.sparql_service import build_graph, execute_sparql
from app.db import db
from app.db.auth import User
from app.db.core import Expression, Item, Manifestation, Work
from app.db.federation import FederationConsent


@pytest.fixture
def private_user(app):
    """User with default_item_visibility='private'."""
    with app.app_context():
        user = User(
            email=f"private_u_{uuid.uuid4().hex[:6]}@example.com",
            public_username=f"priv_{uuid.uuid4().hex[:6]}",
            display_name="Private Collector",
            default_item_visibility="private",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def non_consented_user(app):
    """User without federation collection consent."""
    with app.app_context():
        user = User(
            email=f"noconsent_{uuid.uuid4().hex[:6]}@example.com",
            public_username=f"noconsent_{uuid.uuid4().hex[:6]}",
            display_name="Non Consented",
            default_item_visibility="public",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        consent = FederationConsent(
            user_id=user.id,
            federated_profile=True,
            federated_collection=False,
        )
        db.session.add(consent)
        db.session.commit()
        return user.id


def test_is_item_publicly_visible_respects_owner_privacy(app, private_user):
    """Verify is_item_publicly_visible returns False for items of private users."""
    with app.app_context():
        user = db.session.get(User, private_user)
        work = Work(title="Private Dune")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, publisher="Private Press")
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=user.id, collection_status="available")
        db.session.add(item)
        db.session.commit()

        assert not is_item_publicly_visible(item)


def test_is_item_publicly_visible_respects_federation_consent(app, non_consented_user):
    """Verify is_item_publicly_visible returns False when federated_collection is False."""
    with app.app_context():
        user = db.session.get(User, non_consented_user)
        work = Work(title="Non-Consented Book")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, publisher="Non-Consented Press")
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=user.id, collection_status="available")
        db.session.add(item)
        db.session.commit()

        assert not is_item_publicly_visible(item)


def test_build_graph_omits_private_item_from_anonymous_snapshot(app, private_user):
    """Verify private item is excluded from anonymous graph snapshot but included for owner."""
    with app.app_context():
        user = db.session.get(User, private_user)
        work = Work(title="Secret Manuscript")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, publisher="Secret Press")
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=user.id, collection_status="available")
        db.session.add(item)
        db.session.commit()

        # Anonymous snapshot
        anon_graph = build_graph(items=[item], user_id=None)
        anon_res = execute_sparql(anon_graph, "ASK { ?s a <http://purl.org/vocab/frbr/core#Item> }")
        assert not anon_res.askAnswer

        # Owner snapshot
        owner_graph = build_graph(items=[item], user_id=user.id)
        owner_res = execute_sparql(owner_graph, "ASK { ?s a <http://purl.org/vocab/frbr/core#Item> }")
        assert owner_res.askAnswer
