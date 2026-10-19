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
"""Tests verifying FRBR entity merge tombstones, owl:sameAs triples, and ActivityStreams Move redirection."""

from __future__ import annotations

import json

import pytest

from app.core.frbr_merge import get_entity_tombstone, record_merge_tombstone
from app.core.frbr_service import merge_frbr_entities
from app.core.iri import canonical_frbr_iri, get_lod_base_url
from app.db import db
from app.db.models import Expression, Manifestation, Work


@pytest.fixture
def sample_frbr_hierarchy(app):
    """Create two Works, each with an Expression and Manifestation for merge tests."""
    with app.app_context():
        work1 = Work(title="Surviving Work", meta={"edition": "first"})
        work2 = Work(title="Duplicate Work to Merge", meta={"edition": "second"})
        db.session.add_all([work1, work2])
        db.session.flush()

        expr1 = Expression(work_id=work1.id, content_type="book", language="en")
        expr2 = Expression(work_id=work2.id, content_type="book", language="en")
        db.session.add_all([expr1, expr2])
        db.session.flush()

        manif1 = Manifestation(expression_id=expr1.id, publisher="Target Press", isbn13="9780000000001")
        manif2 = Manifestation(expression_id=expr2.id, publisher="Source Press", isbn13="9780000000002")
        db.session.add_all([manif1, manif2])
        db.session.commit()

        w1_id, w2_id = work1.id, work2.id
        m1_id, m2_id = manif1.id, manif2.id
        e1_id, e2_id = expr1.id, expr2.id

    return {
        "work_target": w1_id,
        "work_source": w2_id,
        "manif_target": m1_id,
        "manif_source": m2_id,
        "expr_target": e1_id,
        "expr_source": e2_id,
    }


def test_record_merge_tombstone_creates_valid_audit_record(app):
    """Verify record_merge_tombstone builds expected owl:sameAs and ActivityStreams structures."""
    with app.app_context():
        record_merge_tombstone(
            entity_type="manifestation",
            source_id=1001,
            target_id=1002,
            actor_id=None,
            repointed={"Item.manifestation_id": 3},
            base_url="https://test.iqoqo.cc",
        )
        db.session.commit()

        tombstone = get_entity_tombstone("manifestation", 1001)
        assert tombstone is not None
        assert tombstone.entity_type == "manifestation"
        assert tombstone.entity_id == 1001
        assert tombstone.diff["target_id"] == 1002
        assert tombstone.diff["owl_same_as"] == "https://test.iqoqo.cc/manifestations/1002"
        assert tombstone.diff["source_iri"] == "https://test.iqoqo.cc/manifestations/1001"
        assert tombstone.diff["target_iri"] == "https://test.iqoqo.cc/manifestations/1002"

        move = tombstone.diff["activitystreams_move"]
        assert move["type"] == "Move"
        assert move["object"] == "https://test.iqoqo.cc/manifestations/1001"
        assert move["target"] == "https://test.iqoqo.cc/manifestations/1002"

        tombstone_payload = tombstone.diff["tombstone"]
        assert tombstone_payload["type"] == "Tombstone"
        assert tombstone_payload["formerType"] == "Manifestation"
        assert tombstone_payload["movedTo"] == "https://test.iqoqo.cc/manifestations/1002"


def test_frbr_merge_service_records_tombstone(app, sample_frbr_hierarchy):
    """Verify merge_frbr_entities creates a discoverable tombstone audit entry."""
    with app.app_context():
        source_id = sample_frbr_hierarchy["work_source"]
        target_id = sample_frbr_hierarchy["work_target"]

        # Merge Work 2 into Work 1
        merge_frbr_entities(
            entity_type="work",
            source_id=source_id,
            target_id=target_id,
        )

        # Source work must be deleted from DB
        assert db.session.get(Work, source_id) is None
        # Target work survives
        assert db.session.get(Work, target_id) is not None

        # Tombstone exists in EntityAuditLog
        tombstone = get_entity_tombstone("work", source_id)
        assert tombstone is not None
        assert tombstone.diff["target_id"] == target_id
        assert "owl_same_as" in tombstone.diff
        assert "activitystreams_move" in tombstone.diff


def test_tombstone_activitypub_move_response(client, app, sample_frbr_hierarchy):
    """Verify dereferencing merged entity with ActivityPub accept header returns 410 and Move payload."""
    with app.app_context():
        source_id = sample_frbr_hierarchy["manif_source"]
        target_id = sample_frbr_hierarchy["manif_target"]
        base_url = get_lod_base_url()
        target_iri = canonical_frbr_iri("manifestation", target_id, base_url)

        merge_frbr_entities(
            entity_type="manifestation",
            source_id=source_id,
            target_id=target_id,
        )

    # ActivityPub Accept Header
    headers = {"Accept": "application/activity+json"}
    resp = client.get(f"/api/public/manifestations/{source_id}", headers=headers)

    assert resp.status_code == 410
    assert "application/activity+json" in resp.content_type
    assert resp.headers["Location"] == target_iri

    data = resp.get_json()
    assert data["type"] == "Move"
    assert data["target"] == target_iri
    assert f"/manifestations/{source_id}" in data["object"]


def test_tombstone_rdf_same_as_response(client, app, sample_frbr_hierarchy):
    """Verify dereferencing merged entity returns 410 and owl:sameAs triple in negotiated RDF format."""
    with app.app_context():
        source_id = sample_frbr_hierarchy["work_source"]
        target_id = sample_frbr_hierarchy["work_target"]
        base_url = get_lod_base_url()
        source_iri = canonical_frbr_iri("work", source_id, base_url)
        target_iri = canonical_frbr_iri("work", target_id, base_url)

        merge_frbr_entities(
            entity_type="work",
            source_id=source_id,
            target_id=target_id,
        )

    # 1. JSON-LD format
    headers_jsonld = {"Accept": "application/ld+json"}
    resp_jsonld = client.get(f"/api/public/works/{source_id}", headers=headers_jsonld)
    assert resp_jsonld.status_code == 410
    assert "application/ld+json" in resp_jsonld.content_type
    assert resp_jsonld.headers["Location"] == target_iri
    data = json.loads(resp_jsonld.get_data(as_text=True))
    assert data["@id"] == source_iri
    assert data["owl:sameAs"]["@id"] == target_iri

    # 2. Turtle format
    headers_turtle = {"Accept": "text/turtle"}
    resp_turtle = client.get(f"/api/public/works/{source_id}", headers=headers_turtle)
    assert resp_turtle.status_code == 410
    assert "text/turtle" in resp_turtle.content_type
    turtle_text = resp_turtle.get_data(as_text=True)
    assert f"<{source_iri}> owl:sameAs <{target_iri}>" in turtle_text

    # 3. N-Triples format
    headers_nt = {"Accept": "application/n-triples"}
    resp_nt = client.get(f"/api/public/works/{source_id}", headers=headers_nt)
    assert resp_nt.status_code == 410
    nt_text = resp_nt.get_data(as_text=True)
    assert f"<{source_iri}> <http://www.w3.org/2002/07/owl#sameAs> <{target_iri}>" in nt_text


def test_tombstone_browser_and_explicit_redirect(client, app, sample_frbr_hierarchy):
    """Verify HTML requests 301-redirect to target UI page and ?redirect=1 redirects to target IRI."""
    with app.app_context():
        source_id = sample_frbr_hierarchy["manif_source"]
        target_id = sample_frbr_hierarchy["manif_target"]
        base_url = get_lod_base_url()
        target_iri = canonical_frbr_iri("manifestation", target_id, base_url)

        merge_frbr_entities(
            entity_type="manifestation",
            source_id=source_id,
            target_id=target_id,
        )

    # Browser HTML request
    html_headers = {"Accept": "text/html,application/xhtml+xml"}
    html_resp = client.get(f"/api/public/manifestations/{source_id}", headers=html_headers)
    assert html_resp.status_code == 301
    assert html_resp.headers["Location"] == f"/manifestation/{target_id}"

    # Explicit redirect query param
    redir_resp = client.get(f"/api/public/manifestations/{source_id}?redirect=1")
    assert redir_resp.status_code == 301
    assert redir_resp.headers["Location"] == target_iri


def test_nonexistent_entity_returns_404(client):
    """Verify non-existent entity with no tombstone returns 404."""
    resp = client.get("/api/public/works/999999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Work not found"
