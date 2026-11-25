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
"""Tests for cross-media FRBR Work linking and reconciliation (C144)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core import frbr_service, work_linking_service
from app.core.graph_service import GraphService
from app.db import db
from app.db.auth import User
from app.db.contributions import Contributor, WorkContribution
from app.db.core import Expression, Item, Manifestation, Work, WorkLinkCandidate, WorkRelation


def _seed_lotr_and_hp(app) -> dict[str, int]:
    """Seed LotR and Harry Potter book + movie Works with disjoint creators."""
    with app.app_context():
        owner = db.session.query(User).first()
        if owner is None:
            owner = User(email="seed-owner@example.com", password_hash="x", is_active=True)
            db.session.add(owner)
            db.session.flush()

        tolkien = Contributor(name="J.R.R. Tolkien", type="person")
        jackson = Contributor(name="Peter Jackson", type="person")
        rowling = Contributor(name="J.K. Rowling", type="person")
        columbus = Contributor(name="Chris Columbus", type="person")
        db.session.add_all([tolkien, jackson, rowling, columbus])
        db.session.flush()

        lotr_book = Work(title="The Lord of the Rings")
        lotr_movie = Work(title="The Lord of the Rings: The Fellowship of the Ring")
        hp_book = Work(title="Harry Potter and the Philosopher's Stone")
        hp_movie = Work(title="Harry Potter and the Sorcerer's Stone")
        db.session.add_all([lotr_book, lotr_movie, hp_book, hp_movie])
        db.session.flush()

        db.session.add_all(
            [
                WorkContribution(work_id=lotr_book.id, contributor_id=tolkien.id, role="author"),
                WorkContribution(work_id=lotr_movie.id, contributor_id=jackson.id, role="director"),
                WorkContribution(work_id=hp_book.id, contributor_id=rowling.id, role="author"),
                WorkContribution(work_id=hp_movie.id, contributor_id=columbus.id, role="director"),
            ]
        )

        e_lotr_b = Expression(work_id=lotr_book.id, content_type="book", language="en")
        e_lotr_m = Expression(work_id=lotr_movie.id, content_type="movie", language="en")
        e_hp_b = Expression(work_id=hp_book.id, content_type="book", language="en")
        e_hp_m = Expression(work_id=hp_movie.id, content_type="movie", language="en")
        db.session.add_all([e_lotr_b, e_lotr_m, e_hp_b, e_hp_m])
        db.session.flush()

        m_lotr_b = Manifestation(expression_id=e_lotr_b.id, format="hardcover")
        m_lotr_m = Manifestation(expression_id=e_lotr_m.id, format="blu-ray")
        db.session.add_all([m_lotr_b, m_lotr_m])
        db.session.flush()

        db.session.add_all(
            [
                Item(manifestation_id=m_lotr_b.id, owner_id=owner.id, visibility="public", is_hidden=False),
                Item(manifestation_id=m_lotr_m.id, owner_id=owner.id, visibility="public", is_hidden=False),
            ]
        )
        db.session.commit()
        return {
            "lotr_book": lotr_book.id,
            "lotr_movie": lotr_movie.id,
            "hp_book": hp_book.id,
            "hp_movie": hp_movie.id,
        }


def test_heuristic_scan_detects_cross_media_and_skips_dismissed(app):
    """Heuristic scan detects LotR and HP book+movie with disjoint creators and skips dismissed pairs."""
    ids = _seed_lotr_and_hp(app)
    with app.app_context():
        report = work_linking_service.scan_cross_media_links(engine="heuristic", dry_run=False)
        assert report.created >= 2

        candidates, total = work_linking_service.list_work_link_candidates(status="pending")
        assert total >= 2
        pairs = {(c.source_work_id, c.target_work_id) for c in candidates}
        assert (ids["lotr_movie"], ids["lotr_book"]) in pairs
        assert (ids["hp_movie"], ids["hp_book"]) in pairs

        # Dismiss one candidate and re-scan -> must not re-queue it
        hp_cand = next(c for c in candidates if c.source_work_id == ids["hp_movie"])
        work_linking_service.dismiss_candidate(hp_cand.id)

        rescan = work_linking_service.scan_cross_media_links(engine="heuristic", dry_run=False)
        assert rescan.created == 0
        assert rescan.already_known >= 2


def test_llama_engine_adjudication_and_ssrf_guard(app, monkeypatch):
    """ENGINE_LLAMA validates OLLAMA_URL and persists LLM reasoning."""
    _seed_lotr_and_hp(app)

    with app.app_context():
        monkeypatch.setattr(work_linking_service, "_is_llm_enabled", lambda: True)
        monkeypatch.setenv("OLLAMA_URL", "http://169.254.169.254/latest")
        with pytest.raises(work_linking_service.WorkLinkPrerequisiteError):
            work_linking_service.scan_cross_media_links(engine="llama", dry_run=False)

        monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
        mock_tags = MagicMock()
        mock_tags.json.return_value = {"models": [{"name": "llama3.1:latest"}]}
        mock_tags.raise_for_status.return_value = None

        mock_gen = MagicMock()
        mock_gen.json.return_value = {
            "response": '{"is_related": true, "relation_type": "is_adaptation_of", "confidence": 0.96, "reasoning": "Film adaptation of novel"}'
        }
        mock_gen.raise_for_status.return_value = None

        monkeypatch.setattr(work_linking_service.requests, "get", lambda *a, **kw: mock_tags)
        monkeypatch.setattr(work_linking_service.requests, "post", lambda *a, **kw: mock_gen)

        report = work_linking_service.scan_cross_media_links(engine="llama", dry_run=False)
        assert report.llm_evaluations >= 1
        assert report.created >= 1
        cands, _ = work_linking_service.list_work_link_candidates(status="pending")
        assert any(c.resolution_source == "llm" and c.llm_reasoning == "Film adaptation of novel" for c in cands)


def test_dag_cycle_and_self_link_rejected(app):
    """Self-links and directed cycles in WorkRelation are rejected."""
    ids = _seed_lotr_and_hp(app)
    with app.app_context():
        with pytest.raises(work_linking_service.WorkLinkCycleError):
            work_linking_service.create_work_relation(
                source_work_id=ids["lotr_book"],
                target_work_id=ids["lotr_book"],
                relation_type="is_adaptation_of",
            )

        work_linking_service.create_work_relation(
            source_work_id=ids["lotr_movie"],
            target_work_id=ids["lotr_book"],
            relation_type="is_adaptation_of",
        )
        with pytest.raises(work_linking_service.WorkLinkCycleError):
            work_linking_service.create_work_relation(
                source_work_id=ids["lotr_book"],
                target_work_id=ids["lotr_movie"],
                relation_type="is_derivative_of",
            )


def test_graph_and_rdf_emit_confirmed_only(app):
    """GraphService and RDF serialization emit confirmed WorkRelations only."""
    ids = _seed_lotr_and_hp(app)
    with app.app_context():
        # Pending candidate MUST NOT appear in graph or RDF
        db.session.add(
            WorkLinkCandidate(
                source_work_id=ids["hp_movie"],
                target_work_id=ids["hp_book"],
                proposed_relation_type="is_adaptation_of",
                confidence=0.9,
                resolution_source="heuristic",
                status="pending",
            )
        )
        # Confirmed WorkRelation MUST appear
        db.session.add(
            WorkRelation(
                source_work_id=ids["lotr_movie"],
                target_work_id=ids["lotr_book"],
                relation_type="is_adaptation_of",
            )
        )
        db.session.commit()

        graph = GraphService.build_neighborhood(
            entity_type="work",
            entity_id=ids["lotr_book"],
            depth=1,
            edge_categories={"derivatives"},
        )
        edge_types = {(e["source"], e["target"], e["category"]) for e in graph["edges"]}
        assert (f"work:{ids['lotr_movie']}", f"work:{ids['lotr_book']}", "derivatives") in edge_types
        assert not any(f"work:{ids['hp_movie']}" in (e["source"], e["target"]) for e in graph["edges"])

        items = db.session.query(Item).all()
        rdf_graph = frbr_service.build_collection_rdf_graph(items, base_url="https://example.org")
        turtle = rdf_graph.serialize(format="turtle")
        assert "R2_is_derivative_of" in turtle
        assert "isBasedOn" in turtle
        assert f"work/{ids['hp_movie']}" not in turtle


def test_admin_api_rbac_and_federation_head_guard(app, client, admin_headers, normal_user_headers, monkeypatch):
    """Endpoints enforce READ_METADATA/WRITE_METADATA RBAC and Federation Head 403 guard."""
    ids = _seed_lotr_and_hp(app)

    # Standard user lacks WRITE_METADATA -> 403 on mutations
    res_scan_forbidden = client.post("/api/v1/admin/work-links/scan", json={}, headers=normal_user_headers)
    assert res_scan_forbidden.status_code == 403

    # Admin can scan, list, accept, create, and delete
    res_scan = client.post("/api/v1/admin/work-links/scan", json={"engine": "heuristic", "dry_run": False}, headers=admin_headers)
    assert res_scan.status_code == 200
    assert res_scan.get_json()["data"]["created"] >= 2

    res_list = client.get("/api/v1/admin/work-links/candidates?status=pending", headers=admin_headers)
    assert res_list.status_code == 200
    cands = res_list.get_json()["data"]
    assert len(cands) >= 2

    cand_id = cands[0]["id"]
    res_accept = client.post(f"/api/v1/admin/work-links/candidates/{cand_id}/accept", json={}, headers=admin_headers)
    assert res_accept.status_code == 200
    rel_id = res_accept.get_json()["data"]["relation"]["id"]

    # Both Works still exist (never merged)
    with app.app_context():
        assert db.session.get(Work, ids["lotr_book"]) is not None
        assert db.session.get(Work, ids["lotr_movie"]) is not None

    # Federation Head Mode blocks mutations with 403
    monkeypatch.setattr("app.api.admin.is_federation_head_mode", lambda: True)
    res_fed = client.post(
        "/api/v1/admin/work-links",
        json={"source_work_id": ids["hp_movie"], "target_work_id": ids["hp_book"], "relation_type": "is_adaptation_of"},
        headers=admin_headers,
    )
    assert res_fed.status_code == 403

    monkeypatch.setattr("app.api.admin.is_federation_head_mode", lambda: False)
    res_del = client.delete(f"/api/v1/admin/work-links/{rel_id}", headers=admin_headers)
    assert res_del.status_code == 200


def test_frbr_merge_reversed_candidate_collision_and_etl_merge(app):
    """ORM repoint_references and ETL apply_work_merge_plan prune reversed/third-party collisions."""
    from app.core.frbr_merge import delete_source_row, repoint_references
    from scripts.etl.merge import apply_work_merge_plan, generate_work_merge_plan

    with app.app_context():
        w_src = Work(title="Source Novel")
        w_tgt = Work(title="Target Novel")
        w_peer = Work(title="Film Adaptation")
        w_etl_src = Work(title="ETL Source")
        w_etl_tgt = Work(title="ETL Target")
        db.session.add_all([w_src, w_tgt, w_peer, w_etl_src, w_etl_tgt])
        db.session.flush()

        # Reversed unordered pair: (src, peer) and (peer, tgt)
        db.session.add_all(
            [
                WorkLinkCandidate(
                    source_work_id=w_src.id,
                    target_work_id=w_peer.id,
                    proposed_relation_type="is_adaptation_of",
                    confidence=0.85,
                    resolution_source="heuristic",
                    status="pending",
                ),
                WorkLinkCandidate(
                    source_work_id=w_peer.id,
                    target_work_id=w_tgt.id,
                    proposed_relation_type="is_adaptation_of",
                    confidence=0.90,
                    resolution_source="heuristic",
                    status="pending",
                ),
                # ETL third-party WorkRelation + WorkLinkCandidate collision
                WorkRelation(source_work_id=w_etl_src.id, target_work_id=w_peer.id, relation_type="is_adaptation_of"),
                WorkRelation(source_work_id=w_etl_tgt.id, target_work_id=w_peer.id, relation_type="is_adaptation_of"),
                WorkLinkCandidate(
                    source_work_id=w_etl_src.id,
                    target_work_id=w_peer.id,
                    proposed_relation_type="is_adaptation_of",
                    confidence=0.8,
                    resolution_source="heuristic",
                    status="pending",
                ),
                WorkLinkCandidate(
                    source_work_id=w_peer.id,
                    target_work_id=w_etl_tgt.id,
                    proposed_relation_type="is_adaptation_of",
                    confidence=0.85,
                    resolution_source="heuristic",
                    status="pending",
                ),
            ]
        )
        db.session.commit()

        repoint_references("work", w_src.id, w_tgt.id)
        delete_source_row(w_src)
        db.session.commit()
        assert db.session.get(Work, w_src.id) is None
        assert db.session.get(Work, w_tgt.id) is not None

        etl_src_id = w_etl_src.id
        plan = generate_work_merge_plan(w_etl_tgt, w_etl_src)
        stats = apply_work_merge_plan(plan, dry_run=False)
        db.session.expire_all()
        assert stats["reparented_work_relations"] >= 1
        assert db.session.get(Work, etl_src_id) is None


def test_c152_llm_governance_derivation_rank_and_atomic_accept(app, client, admin_headers, monkeypatch):
    """ALLOW_LLM=false skips Ollama, taxonomy 'text' ranks original, and accept enforces 400/409."""
    from sqlalchemy import select

    ids = _seed_lotr_and_hp(app)
    with app.app_context():
        # Taxonomy 'text' book vs 'movie' film -> movie is source, book ('text') is target
        w_text = Work(title="The Silmarillion")
        w_film = Work(title="The Silmarillion (Film)")
        db.session.add_all([w_text, w_film])
        db.session.flush()
        db.session.add_all(
            [
                Expression(work_id=w_text.id, content_type="text", language="en"),
                Expression(work_id=w_film.id, content_type="movie", language="en"),
            ]
        )
        db.session.commit()

        # ALLOW_LLM=false -> raises WorkLinkPrerequisiteError and sends zero Ollama requests
        monkeypatch.setattr(work_linking_service, "_is_llm_enabled", lambda: False)
        called = False

        def _boom(*_args, **_kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr(work_linking_service, "_adjudicate_with_ollama", _boom)
        with pytest.raises(work_linking_service.WorkLinkPrerequisiteError, match="ALLOW_LLM"):
            work_linking_service.scan_cross_media_links(engine="llama", dry_run=False)
        assert not called

        report = work_linking_service.scan_cross_media_links(engine="heuristic", dry_run=False)
        assert report.created >= 1

        sil_cand = db.session.execute(
            select(WorkLinkCandidate).where(
                ((WorkLinkCandidate.source_work_id == w_film.id) & (WorkLinkCandidate.target_work_id == w_text.id))
                | ((WorkLinkCandidate.source_work_id == w_text.id) & (WorkLinkCandidate.target_work_id == w_film.id))
            )
        ).scalar_one()
        assert sil_cand.source_work_id == w_film.id
        assert sil_cand.target_work_id == w_text.id
        cand_id = sil_cand.id

    # Invalid override work ID -> 400
    res_bad = client.post(
        f"/api/v1/admin/work-links/candidates/{cand_id}/accept",
        json={"source_work_id": ids["lotr_book"], "target_work_id": ids["hp_book"]},
        headers=admin_headers,
    )
    assert res_bad.status_code == 400

    # Valid swap override -> 200
    res_ok = client.post(
        f"/api/v1/admin/work-links/candidates/{cand_id}/accept",
        json={"source_work_id": w_text.id, "target_work_id": w_film.id},
        headers=admin_headers,
    )
    assert res_ok.status_code == 200

    # Re-accepting non-pending candidate -> 409
    res_dup = client.post(
        f"/api/v1/admin/work-links/candidates/{cand_id}/accept",
        json={},
        headers=admin_headers,
    )
    assert res_dup.status_code == 409


def test_c152_library_graph_derivatives_and_balanced_root_search(app, client):
    """build_library_graph emits derivatives edges and search_root_candidates balances quotas."""
    from app.core.graph_service import GraphService

    with app.app_context():
        w_book = Work(title="BalancedSearchBook")
        w_film = Work(title="BalancedSearchFilm")
        w_series = Work(title="BalancedSearchSeries", work_kind="series")
        db.session.add_all([w_book, w_film, w_series])
        db.session.flush()
        db.session.add(WorkRelation(source_work_id=w_film.id, target_work_id=w_book.id, relation_type="is_adaptation_of"))
        # Add 6 person contributors + 1 org contributor matching "BalancedSearch"
        for i in range(6):
            db.session.add(Contributor(name=f"BalancedSearch Person {i}", type="person"))
        db.session.add(Contributor(name="BalancedSearch Org", type="organization"))
        db.session.commit()

        lib_graph = GraphService.build_library_graph(edge_categories={"derivatives"})
        assert any(
            e["category"] == "derivatives" and e["source"] == f"work:{w_film.id}" and e["target"] == f"work:{w_book.id}"
            for e in lib_graph["edges"]
        )

    res = client.get("/api/catalog/graph/search?q=BalancedSearch&types=person,series,work&limit=6")
    assert res.status_code == 200
    rows = res.get_json()["data"]
    types_present = {r["entity_type"] for r in rows}
    assert types_present == {"person", "series", "work"}
    assert all("Org" not in r["label"] for r in rows if r["entity_type"] == "person")
    work_ids = [r["entity_id"] for r in rows if r["entity_type"] == "work"]
    series_ids = [r["entity_id"] for r in rows if r["entity_type"] == "series"]
    assert set(work_ids).isdisjoint(set(series_ids))

    # Order-independent deduplication when work precedes series
    res_rev = client.get("/api/catalog/graph/search?q=BalancedSearch&types=work,series&limit=6")
    assert res_rev.status_code == 200
    rows_rev = res_rev.get_json()["data"]
    work_ids_rev = [r["entity_id"] for r in rows_rev if r["entity_type"] == "work"]
    series_ids_rev = [r["entity_id"] for r in rows_rev if r["entity_type"] == "series"]
    assert series_ids_rev
    assert set(work_ids_rev).isdisjoint(set(series_ids_rev))
