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


def test_admin_lod_stats_rbac_and_data(client, normal_user_headers, admin_headers, lod_manif_setup):
    """Verify GET /api/admin/lod/stats enforces RBAC and returns statistics breakdown."""
    # 1. Unauthenticated -> 401
    assert client.get("/api/admin/lod/stats").status_code == 401

    # 2. Regular user -> 403
    assert client.get("/api/admin/lod/stats", headers=normal_user_headers).status_code == 403

    # 3. Admin user -> 200 with stats
    resp = client.get("/api/admin/lod/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert "total_manifestations" in data
    assert "linked_manifestations" in data
    assert "unlinked_manifestations" in data
    assert "total_links" in data
    assert "suggested_links" in data
    assert "by_authority" in data
    assert "dbpedia" in data["by_authority"]


def test_admin_v1_lod_cleanup_endpoint(client, normal_user_headers, admin_headers, app):
    """Verify POST /api/v1/admin/lod/cleanup enforces RBAC and triggers cleanup task."""
    # 1. Unauthenticated -> 401
    assert client.post("/api/v1/admin/lod/cleanup").status_code == 401

    # 2. Regular user -> 403
    assert client.post("/api/v1/admin/lod/cleanup", headers=normal_user_headers).status_code == 403

    # 3. Admin user -> 200 with task execution result
    resp = client.post(
        "/api/v1/admin/lod/cleanup",
        headers=admin_headers,
        json={"dry_run": True, "batch_size": 25},
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    assert "total_evaluated" in payload["data"]
    assert "demoted" in payload["data"]


def test_contributor_and_expression_semantic_links_api_filter_stats_cleanup(client, admin_headers, app):
    """Verify contributor/expression curation, catalog LOD filtering, admin stats, and cleanup task."""
    from app.api.filters import CatalogFilterBuilder
    from app.core.lod_linking_service import get_manifestation_semantic_links_dict
    from app.db.contributions import Contributor, WorkContribution

    with app.app_context():
        author_linked = Contributor(name="Ursula K. Le Guin", type="person")
        unrelated_contrib = Contributor(name="Unrelated Creator", type="person")
        work_a = Work(title="The Dispossessed", meta={"authors": ["Ursula K. Le Guin"]})
        work_b = Work(title="Standalone Book", meta={})
        db.session.add_all([author_linked, unrelated_contrib, work_a, work_b])
        db.session.flush()

        db.session.add(WorkContribution(work_id=work_a.id, contributor_id=author_linked.id, role="author", sequence=0))
        expr_a = Expression(work_id=work_a.id, content_type="text", language="en")
        expr_b = Expression(work_id=work_b.id, content_type="text", language="en")
        db.session.add_all([expr_a, expr_b])
        db.session.flush()

        manif_a = Manifestation(expression_id=expr_a.id, isbn13="9780061054884")
        manif_b = Manifestation(expression_id=expr_b.id, isbn13="9780000000002")
        db.session.add_all([manif_a, manif_b])
        db.session.flush()

        contrib_link = SemanticLink(
            entity_type="contributor",
            entity_id=author_linked.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Ursula_K._Le_Guin",
            pref_label="Ursula K. Le Guin",
            confidence=0.92,
            status="suggested",
            attributes={"dbo_type": "dbo:Person", "comment": "Ursula Kroeber Le Guin was an American author."},
            verified=False,
        )
        expr_link = SemanticLink(
            entity_type="expression",
            entity_id=expr_a.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/The_Dispossessed_EN",
            pref_label="The Dispossessed (English)",
            confidence=0.9,
            status="suggested",
            verified=False,
        )
        stranger_link = SemanticLink(
            entity_type="contributor",
            entity_id=unrelated_contrib.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Unrelated_Creator",
            pref_label="Unrelated Creator",
            confidence=0.88,
            status="accepted",
            verified=True,
        )
        db.session.add_all([contrib_link, expr_link, stranger_link])
        db.session.commit()

        manif_a_id, manif_b_id = manif_a.id, manif_b.id
        contrib_link_id, expr_link_id, stranger_link_id = contrib_link.id, expr_link.id, stranger_link.id

        # Manifestation links dictionary surfaces contributor + expression links
        grouped = get_manifestation_semantic_links_dict(manif_a_id)
        assert {item["id"] for item in grouped["links"]} == {contrib_link_id, expr_link_id}

    # PATCH accept contributor and expression links; reject unrelated contributor link
    resp_patch_c = client.patch(
        f"/api/manifestations/{manif_a_id}/semantic-links/{contrib_link_id}",
        json={"status": "accepted"},
        headers=admin_headers,
    )
    assert resp_patch_c.status_code == 200
    assert resp_patch_c.get_json()["data"]["verified"] is True

    resp_patch_e = client.patch(
        f"/api/manifestations/{manif_a_id}/semantic-links/{expr_link_id}",
        json={"status": "accepted"},
        headers=admin_headers,
    )
    assert resp_patch_e.status_code == 200

    resp_bad = client.patch(
        f"/api/manifestations/{manif_a_id}/semantic-links/{stranger_link_id}",
        json={"status": "accepted"},
        headers=admin_headers,
    )
    assert resp_bad.status_code == 400

    with app.app_context():
        # Filter builder matches contributor/expression links via lod_authority & lod_status
        base_q = Manifestation.query.join(Expression, Manifestation.expression_id == Expression.id).join(
            Work, Expression.work_id == Work.id
        )
        linked_ids = {
            m.id for m in CatalogFilterBuilder(base_q, root="manifestation").apply(lod_authority="dbpedia", lod_status="linked").all()
        }
        assert manif_a_id in linked_ids
        assert manif_b_id not in linked_ids

        unlinked_q = Manifestation.query.join(Expression, Manifestation.expression_id == Expression.id).join(
            Work, Expression.work_id == Work.id
        )
        unlinked_ids = {m.id for m in CatalogFilterBuilder(unlinked_q, root="manifestation").apply(lod_status="unlinked").all()}
        assert manif_b_id in unlinked_ids
        assert manif_a_id not in unlinked_ids

        # Cleanup task evaluates contributor-tier links without crashing or false-demoting valid authors
        cleanup_res = cleanup_lod_links_task(dry_run=True)
        assert cleanup_res["total_evaluated"] >= 2

    # Admin LOD stats include contributor-linked manifestations
    stats_resp = client.get("/api/admin/lod/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    assert stats_resp.get_json()["data"]["linked_manifestations"] >= 1

    # DELETE contributor-tier link succeeds via manifestation route
    del_resp = client.delete(
        f"/api/manifestations/{manif_a_id}/semantic-links/{contrib_link_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 204
