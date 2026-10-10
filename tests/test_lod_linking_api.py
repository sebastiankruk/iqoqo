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
"""API integration tests for LOD linking endpoints, lifecycle transitions, and audit logs."""

from unittest.mock import patch

import pytest

from app.core.tasks import cleanup_lod_links_task
from app.db import db
from app.db.core import EntityAuditLog, Expression, Manifestation, SemanticLink, Work


@pytest.fixture
def lod_manif_setup(app):
    """Seed database with an FRBR hierarchy and semantic links for API tests."""
    with app.app_context():
        work = Work(title="Dune", meta={"authors": ["Frank Herbert"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780441172719",
            meta={"publication_place": "Warsaw"},
        )
        db.session.add(manif)
        db.session.flush()

        # Link 1: suggested work link
        link_work_suggested = SemanticLink(
            entity_type="work",
            entity_id=work.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Dune_(novel)",
            pref_label="Dune (novel)",
            confidence=0.75,
            match_strategy="lookup",
            status="suggested",
            verified=False,
        )

        # Link 2: accepted manifestation link
        link_manif_accepted = SemanticLink(
            entity_type="manifestation",
            entity_id=manif.id,
            authority="geonames",
            external_uri="https://sws.geonames.org/756135/",
            pref_label="Warsaw",
            confidence=0.95,
            match_strategy="local_gazetteer",
            status="accepted",
            verified=True,
        )

        db.session.add_all([link_work_suggested, link_manif_accepted])
        db.session.commit()

        return {
            "work_id": work.id,
            "manif_id": manif.id,
            "work_link_id": link_work_suggested.id,
            "manif_link_id": link_manif_accepted.id,
        }


def test_get_manifestation_semantic_links_returns_status(client, lod_manif_setup):
    """Verify GET /api/manifestations/<id>/semantic-links returns link status in each group."""
    manif_id = lod_manif_setup["manif_id"]
    resp = client.get(f"/api/manifestations/{manif_id}/semantic-links")
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    # Check all links list includes status
    assert data["total"] == 2
    assert len(data["links"]) == 2
    statuses = {item["status"] for item in data["links"]}
    assert statuses == {"suggested", "accepted"}

    # Check authority grouping
    assert len(data["grouped"]["dbpedia"]) == 1
    assert data["grouped"]["dbpedia"][0]["status"] == "suggested"
    assert data["grouped"]["dbpedia"][0]["pref_label"] == "Dune (novel)"

    assert len(data["grouped"]["geonames"]) == 1
    assert data["grouped"]["geonames"][0]["status"] == "accepted"
    assert data["grouped"]["geonames"][0]["pref_label"] == "Warsaw"


def test_patch_semantic_link_accept(client, admin_headers, lod_manif_setup, app):
    """Verify PATCH endpoint accepts a suggested link and creates audit log."""
    manif_id = lod_manif_setup["manif_id"]
    link_id = lod_manif_setup["work_link_id"]

    resp = client.patch(
        f"/api/manifestations/{manif_id}/semantic-links/{link_id}",
        json={"status": "accepted"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    res_data = resp.get_json()["data"]
    assert res_data["status"] == "accepted"
    assert res_data["verified"] is True

    # Verify DB state & EntityAuditLog
    with app.app_context():
        link = db.session.get(SemanticLink, link_id)
        assert link is not None
        assert link.status == "accepted"
        assert link.verified is True

        audit = (
            EntityAuditLog.query.filter_by(
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                change_type="semantic_link_accepted",
            )
            .order_by(EntityAuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.diff["old_status"] == "suggested"
        assert audit.diff["new_status"] == "accepted"


def test_patch_semantic_link_reject(client, admin_headers, lod_manif_setup, app):
    """Verify PATCH endpoint rejects a link and logs the audit event."""
    manif_id = lod_manif_setup["manif_id"]
    link_id = lod_manif_setup["work_link_id"]

    resp = client.patch(
        f"/api/manifestations/{manif_id}/semantic-links/{link_id}",
        json={"status": "rejected"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    res_data = resp.get_json()["data"]
    assert res_data["status"] == "rejected"

    with app.app_context():
        link = db.session.get(SemanticLink, link_id)
        assert link is not None
        assert link.status == "rejected"

        audit = (
            EntityAuditLog.query.filter_by(
                entity_type=link.entity_type,
                entity_id=link.entity_id,
                change_type="semantic_link_rejected",
            )
            .order_by(EntityAuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.diff["new_status"] == "rejected"


def test_patch_semantic_link_unauthorized(client, normal_user_headers, lod_manif_setup):
    """Verify normal user without write:metadata gets 403."""
    manif_id = lod_manif_setup["manif_id"]
    link_id = lod_manif_setup["work_link_id"]

    resp = client.patch(
        f"/api/manifestations/{manif_id}/semantic-links/{link_id}",
        json={"status": "accepted"},
        headers=normal_user_headers,
    )
    assert resp.status_code == 403


def test_patch_semantic_link_invalid_status(client, admin_headers, lod_manif_setup):
    """Verify invalid status string returns 400."""
    manif_id = lod_manif_setup["manif_id"]
    link_id = lod_manif_setup["work_link_id"]

    resp = client.patch(
        f"/api/manifestations/{manif_id}/semantic-links/{link_id}",
        json={"status": "invalid_state"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_delete_semantic_link_audit_log(client, admin_headers, lod_manif_setup, app):
    """Verify DELETE /api/manifestations/<id>/semantic-links/<link_id> creates audit log."""
    manif_id = lod_manif_setup["manif_id"]
    link_id = lod_manif_setup["manif_link_id"]

    resp = client.delete(
        f"/api/manifestations/{manif_id}/semantic-links/{link_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 204

    with app.app_context():
        assert db.session.get(SemanticLink, link_id) is None
        audit = (
            EntityAuditLog.query.filter_by(
                entity_type="manifestation",
                entity_id=manif_id,
                change_type="semantic_link_deleted",
            )
            .order_by(EntityAuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.diff["link_id"] == link_id


def test_admin_lod_cleanup_endpoint(client, admin_headers, normal_user_headers):
    """Verify POST /api/admin/lod/cleanup triggers cleanup task or returns 403 for non-admin."""
    # Forbidden for normal user
    resp = client.post("/api/admin/lod/cleanup", json={"dry_run": True}, headers=normal_user_headers)
    assert resp.status_code == 403

    # Permitted for admin
    resp = client.post("/api/admin/lod/cleanup", json={"dry_run": True, "batch_size": 50}, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["dry_run"] is True
    assert "total_evaluated" in data
    assert "demoted" in data


def test_cleanup_lod_links_task_dry_run_and_apply(app):
    """Verify cleanup_lod_links_task re-scores and demotes links in dry_run and apply modes."""
    with app.app_context():
        work = Work(title="Weak Work Match", meta={"authors": ["Author X"]})
        db.session.add(work)
        db.session.flush()

        # Create an accepted link with low confidence (< 0.82)
        link = SemanticLink(
            entity_type="work",
            entity_id=work.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Weak_Work",
            pref_label="Weak Work",
            confidence=0.60,
            match_strategy="lookup",
            status="accepted",
        )
        db.session.add(link)
        db.session.commit()
        link_id = link.id

        # Dry run: should count candidate demotion without changing DB
        res_dry = cleanup_lod_links_task(dry_run=True, batch_size=50)
        assert res_dry["total_evaluated"] >= 1
        assert res_dry["demoted"] == 1

        db.session.expire_all()
        reloaded_link = db.session.get(SemanticLink, link_id)
        assert reloaded_link.status == "accepted"

        # Apply mode: should demote to 'suggested' and write audit log
        res_apply = cleanup_lod_links_task(dry_run=False, batch_size=50)
        assert res_apply["demoted"] == 1

        db.session.expire_all()
        demoted_link = db.session.get(SemanticLink, link_id)
        assert demoted_link.status == "suggested"

        audit = EntityAuditLog.query.filter_by(
            entity_type="work",
            entity_id=work.id,
            change_type="semantic_link_demoted",
        ).first()
        assert audit is not None
        assert audit.diff["link_id"] == link_id
        assert audit.diff["old_status"] == "accepted"
        assert audit.diff["new_status"] == "suggested"
