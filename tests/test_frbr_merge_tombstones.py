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
"""Tests for recursive multi-hop FRBR merge tombstone resolution and redirection."""

from __future__ import annotations

import json

import pytest

from app.core.frbr_merge import get_entity_tombstone, record_merge_tombstone
from app.core.frbr_service import merge_frbr_entities
from app.core.iri import canonical_frbr_iri, get_lod_base_url
from app.db import db
from app.db.models import Expression, Manifestation, Work


@pytest.fixture
def three_way_work_hierarchy(app):
    """Seed three works A, B, C for chained merge verification."""
    with app.app_context():
        work_a = Work(title="First Draft Work A", meta={"edition": "alpha"})
        work_b = Work(title="Intermediate Work B", meta={"edition": "beta"})
        work_c = Work(title="Final Canonical Work C", meta={"edition": "release"})
        db.session.add_all([work_a, work_b, work_c])
        db.session.flush()

        expr_a = Expression(work_id=work_a.id, content_type="book", language="en")
        expr_b = Expression(work_id=work_b.id, content_type="book", language="en")
        expr_c = Expression(work_id=work_c.id, content_type="book", language="en")
        db.session.add_all([expr_a, expr_b, expr_c])
        db.session.flush()

        manif_a = Manifestation(expression_id=expr_a.id, publisher="Publisher A")
        manif_b = Manifestation(expression_id=expr_b.id, publisher="Publisher B")
        manif_c = Manifestation(expression_id=expr_c.id, publisher="Publisher C")
        db.session.add_all([manif_a, manif_b, manif_c])
        db.session.commit()

        ids = {
            "work_a": work_a.id,
            "work_b": work_b.id,
            "work_c": work_c.id,
        }
    return ids


def test_chained_tombstone_resolution(app, three_way_work_hierarchy):
    """Verify get_entity_tombstone follows merge chain A -> B -> C to target C."""
    work_a = three_way_work_hierarchy["work_a"]
    work_b = three_way_work_hierarchy["work_b"]
    work_c = three_way_work_hierarchy["work_c"]

    with app.app_context():
        # First merge: A into B
        merge_frbr_entities(entity_type="work", source_id=work_a, target_id=work_b)
        # Second merge: B into C
        merge_frbr_entities(entity_type="work", source_id=work_b, target_id=work_c)

        # Lookup tombstone for A: should resolve to C
        tombstone_a = get_entity_tombstone("work", work_a)
        assert tombstone_a is not None
        assert tombstone_a.diff["target_id"] == work_c
        base_url = get_lod_base_url()
        canonical_c = canonical_frbr_iri("work", work_c, base_url)
        assert canonical_c in tombstone_a.diff["target_iri"]


def test_chained_tombstone_public_rdf_activitystreams(client, app, three_way_work_hierarchy):
    """Verify public endpoint for A returns 410 pointing to C in ActivityStreams Move payload."""
    work_a = three_way_work_hierarchy["work_a"]
    work_b = three_way_work_hierarchy["work_b"]
    work_c = three_way_work_hierarchy["work_c"]

    with app.app_context():
        merge_frbr_entities(entity_type="work", source_id=work_a, target_id=work_b)
        merge_frbr_entities(entity_type="work", source_id=work_b, target_id=work_c)

    headers = {"Accept": "application/activity+json"}
    resp = client.get(f"/api/public/works/{work_a}", headers=headers)
    assert resp.status_code == 410
    data = resp.get_json()
    assert data["type"] == "Move"

    with app.app_context():
        canonical_c = canonical_frbr_iri("work", work_c, get_lod_base_url())
    assert canonical_c in data["target"]


def test_chained_tombstone_redirect_param(client, app, three_way_work_hierarchy):
    """Verify ?redirect=1 on chained tombstone entity redirects directly to canonical C IRI."""
    work_a = three_way_work_hierarchy["work_a"]
    work_b = three_way_work_hierarchy["work_b"]
    work_c = three_way_work_hierarchy["work_c"]

    with app.app_context():
        merge_frbr_entities(entity_type="work", source_id=work_a, target_id=work_b)
        merge_frbr_entities(entity_type="work", source_id=work_b, target_id=work_c)
        canonical_c = canonical_frbr_iri("work", work_c, get_lod_base_url())

    resp = client.get(f"/api/public/works/{work_a}?redirect=1")
    assert resp.status_code == 301
    assert resp.headers["Location"] == canonical_c


def test_chained_tombstone_browser_html_redirect(client, app, three_way_work_hierarchy):
    """Verify HTML request on chained tombstone 301-redirects to final entity page /work/<id>."""
    work_a = three_way_work_hierarchy["work_a"]
    work_b = three_way_work_hierarchy["work_b"]
    work_c = three_way_work_hierarchy["work_c"]

    with app.app_context():
        merge_frbr_entities(entity_type="work", source_id=work_a, target_id=work_b)
        merge_frbr_entities(entity_type="work", source_id=work_b, target_id=work_c)

    headers = {"Accept": "text/html,application/xhtml+xml"}
    resp = client.get(f"/api/public/works/{work_a}", headers=headers)
    assert resp.status_code == 301
    assert resp.headers["Location"] == f"/work/{work_c}"
