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
"""Tests for Linked Open Data (LOD) entity linking and ETL pipelines."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.cache import cache
from app.core.lod_linking_service import (
    DBpediaClient,
    GeoNamesClient,
    WordNetMapper,
    get_manifestation_semantic_links_dict,
    resolve_manifestation_links,
)
from app.db import db
from app.db.core import Expression, Manifestation, SemanticLink, Work


def test_semantic_link_model_and_frbr_scoping(app):
    """Test SemanticLink model persistence and FRBR relationship scoping."""
    with app.app_context():
        # Create FRBR hierarchy: Work -> Expression -> Manifestation
        work = Work(title="The Hobbit", meta={"authors": ["J.R.R. Tolkien"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780048231475",
            meta={"publisher": "George Allen & Unwin", "publication_place": "London"},
        )
        db.session.add(manif)
        db.session.flush()

        # Work-level semantic links: DBpedia book & WordNet fantasy
        link_work_dbpedia = SemanticLink(
            entity_type="work",
            entity_id=work.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/The_Hobbit",
            pref_label="The Hobbit",
            confidence=0.98,
            match_strategy="lookup",
            attributes={"dbo_type": "dbo:Book"},
            verified=True,
        )
        link_work_wordnet = SemanticLink(
            entity_type="work",
            entity_id=work.id,
            authority="wordnet",
            external_uri="http://wordnet-rdf.princeton.edu/id/06382980-n",
            pref_label="fantasy",
            confidence=0.90,
            match_strategy="synset",
            attributes={"synset_offset": "06382980"},
            verified=False,
        )
        db.session.add_all([link_work_dbpedia, link_work_wordnet])

        # Manifestation-level semantic link: GeoNames London
        link_manif_geonames = SemanticLink(
            entity_type="manifestation",
            entity_id=manif.id,
            authority="geonames",
            external_uri="https://sws.geonames.org/2643743/",
            pref_label="London",
            confidence=0.95,
            match_strategy="lookup",
            attributes={"geoname_id": 2643743, "country_code": "GB", "lat": 51.50853, "lng": -0.12574},
            verified=True,
        )
        db.session.add(link_manif_geonames)
        db.session.commit()

        # Verify Work-level links
        work_links = work.get_semantic_links()
        assert len(work_links) == 2
        assert {link.authority for link in work_links} == {"dbpedia", "wordnet"}
        assert len(work.get_semantic_links(authority="dbpedia")) == 1
        assert len(work.get_semantic_links(authority="geonames")) == 0

        # Verify Manifestation direct links
        assert len(manif.semantic_links) == 1
        assert manif.semantic_links[0].authority == "geonames"

        # Verify Manifestation FRBR scoped links (direct + inherited from Work)
        scoped_all = manif.get_semantic_links(include_work=True)
        assert len(scoped_all) == 3
        assert {link.authority for link in scoped_all} == {"dbpedia", "wordnet", "geonames"}

        scoped_manif_only = manif.get_semantic_links(include_work=False)
        assert len(scoped_manif_only) == 1
        assert scoped_manif_only[0].authority == "geonames"

        # Test filtering by authority
        geonames_links = manif.get_semantic_links(include_work=True, authority="geonames")
        assert len(geonames_links) == 1
        assert geonames_links[0].external_uri == "https://sws.geonames.org/2643743/"

        # Test to_dict serialization
        link_dict = link_manif_geonames.to_dict()
        assert link_dict["authority"] == "geonames"
        assert link_dict["attributes"]["country_code"] == "GB"
        assert link_dict["verified"] is True


def test_dbpedia_client_lookup_and_sparql_fallback(app):
    """Test DBpediaClient Lookup API and SPARQL fallback with caching."""
    with app.app_context():
        # Clear cache for isolated testing
        cache.delete("lod:dbpedia:work:dune:dbo:Book")
        cache.delete("lod:dbpedia:person:frank herbert")

        # 1. Lookup success
        mock_resp_lookup = MagicMock()
        mock_resp_lookup.status_code = 200
        mock_resp_lookup.json.return_value = {
            "docs": [
                {
                    "resource": ["http://dbpedia.org/resource/Dune_(novel)"],
                    "label": ["Dune (novel)"],
                    "score": [95.0],
                    "comment": ["Dune is a 1965 sci-fi novel by Frank Herbert."],
                }
            ]
        }

        with patch("requests.get", return_value=mock_resp_lookup) as mock_get:
            result = DBpediaClient.resolve_work("Dune", media_category="book")
            assert result is not None
            assert result["uri"] == "http://dbpedia.org/resource/Dune_(novel)"
            assert result["confidence"] == 0.95
            assert result["strategy"] == "lookup"
            assert mock_get.call_count == 1

            # Second call should hit cache without calling requests.get again
            cached_result = DBpediaClient.resolve_work("Dune", media_category="book")
            assert cached_result == result
            assert mock_get.call_count == 1

        # 2. Lookup returns empty -> fallback to SPARQL
        cache.delete("lod:dbpedia:work:solaris:dbo:Book")
        mock_resp_empty = MagicMock()
        mock_resp_empty.status_code = 200
        mock_resp_empty.json.return_value = {"docs": []}

        mock_resp_sparql = MagicMock()
        mock_resp_sparql.status_code = 200
        mock_resp_sparql.json.return_value = {
            "results": {
                "bindings": [
                    {
                        "res": {"value": "http://dbpedia.org/resource/Solaris_(novel)"},
                        "label": {"value": "Solaris"},
                    }
                ]
            }
        }

        with patch("requests.get", side_effect=[mock_resp_empty, mock_resp_sparql]) as mock_get:
            result_sparql = DBpediaClient.resolve_work("Solaris", media_category="book")
            assert result_sparql is not None
            assert result_sparql["uri"] == "http://dbpedia.org/resource/Solaris_(novel)"
            assert result_sparql["strategy"] == "sparql"
            assert mock_get.call_count == 2

        # 3. Person resolution
        mock_resp_person = MagicMock()
        mock_resp_person.status_code = 200
        mock_resp_person.json.return_value = {
            "docs": [
                {
                    "resource": ["http://dbpedia.org/resource/Frank_Herbert"],
                    "label": ["Frank Herbert"],
                    "score": [98.0],
                }
            ]
        }
        with patch("requests.get", return_value=mock_resp_person):
            person_result = DBpediaClient.resolve_person("Frank Herbert")
            assert person_result is not None
            assert person_result["uri"] == "http://dbpedia.org/resource/Frank_Herbert"


def test_geonames_client_resolution_and_caching(app):
    """Test GeoNamesClient resolving place names to canonical URIs with caching."""
    with app.app_context():
        cache.delete("lod:geonames:oxford")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "geonames": [
                {
                    "geonameId": 2640729,
                    "name": "Oxford",
                    "countryCode": "GB",
                    "lat": "51.75222",
                    "lng": "-1.25596",
                    "fcode": "PPLA2",
                }
            ]
        }

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = GeoNamesClient.resolve_location("Oxford")
            assert result is not None
            assert result["uri"] == "https://sws.geonames.org/2640729/"
            assert result["label"] == "Oxford"
            assert result["confidence"] == 0.90
            assert result["attributes"]["country_code"] == "GB"
            assert result["attributes"]["lat"] == 51.75222
            assert result["attributes"]["lng"] == -1.25596
            assert mock_get.call_count == 1

            # Verify caching
            cached_result = GeoNamesClient.resolve_location("Oxford")
            assert cached_result == result
            assert mock_get.call_count == 1


def test_wordnet_mapper_resolution(app):
    """Test WordNetMapper local dictionary mapping and fallback."""
    with app.app_context():
        # Local dictionary hit
        res_local = WordNetMapper.resolve_tag("science fiction")
        assert res_local is not None
        assert res_local["uri"] == "http://wordnet-rdf.princeton.edu/id/06363630-n"
        assert res_local["strategy"] == "synset"
        assert res_local["attributes"]["source"] == "local_dictionary"

        # Fallback for novel concept
        res_fallback = WordNetMapper.resolve_tag("cyberpunk")
        assert res_fallback is not None
        assert res_fallback["uri"] == "http://dbpedia.org/resource/Category:Cyberpunk"
        assert res_fallback["strategy"] == "dbpedia_category"
        assert res_fallback["confidence"] == 0.70


def test_resolve_manifestation_links_pipeline(app):
    """Test full resolution pipeline with strict FRBR scoping and deduplication."""
    with app.app_context():
        work = Work(
            title="Neuromancer",
            meta={
                "authors": ["William Gibson"],
                "genres": ["science fiction"],
                "tags": ["cyberpunk"],
            },
        )
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780441569595",
            meta={
                "publisher": "Ace Books",
                "publication_place": "New York",
            },
        )
        db.session.add(manif)
        db.session.commit()

        # Mock DBpedia and GeoNames API responses
        def mock_requests_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "lookup.dbpedia.org" in url:
                params = kwargs.get("params", {})
                q = params.get("query", "")
                if "Neuromancer" in q:
                    resp.json.return_value = {
                        "docs": [
                            {
                                "resource": ["http://dbpedia.org/resource/Neuromancer"],
                                "label": ["Neuromancer"],
                                "score": [97.0],
                            }
                        ]
                    }
                elif "William Gibson" in q:
                    resp.json.return_value = {
                        "docs": [
                            {
                                "resource": ["http://dbpedia.org/resource/William_Gibson"],
                                "label": ["William Gibson"],
                                "score": [95.0],
                            }
                        ]
                    }
                else:
                    resp.json.return_value = {"docs": []}
            elif "geonames.org" in url:
                resp.json.return_value = {
                    "geonames": [
                        {
                            "geonameId": 5128581,
                            "name": "New York City",
                            "countryCode": "US",
                            "lat": "40.71427",
                            "lng": "-74.00597",
                        }
                    ]
                }
            return resp

        with patch("requests.get", side_effect=mock_requests_get):
            created = resolve_manifestation_links(manif.id)
            assert len(created) > 0

            # Verify Work-level links (DBpedia Work, DBpedia Author, WordNet genres/tags)
            work_links = work.get_semantic_links()
            assert any(link.authority == "dbpedia" and "Neuromancer" in link.external_uri for link in work_links)
            assert any(link.authority == "dbpedia" and "William_Gibson" in link.external_uri for link in work_links)
            assert any(link.authority == "wordnet" for link in work_links)

            # Verify Manifestation-level links (GeoNames New York)
            manif_direct = manif.get_semantic_links(include_work=False)
            assert len(manif_direct) == 1
            assert manif_direct[0].authority == "geonames"
            assert "5128581" in manif_direct[0].external_uri

            # Verify scoped retrieval
            all_links = manif.get_semantic_links(include_work=True)
            assert len(all_links) >= 4

            # Verify dictionary grouping
            grouped_dict = get_manifestation_semantic_links_dict(manif.id)
            assert grouped_dict["manifestation_id"] == manif.id
            assert "dbpedia" in grouped_dict["grouped"]
            assert "geonames" in grouped_dict["grouped"]
            assert "wordnet" in grouped_dict["grouped"]

            # Verify idempotency (calling again should not insert duplicates)
            second_run = resolve_manifestation_links(manif.id)
            assert len(second_run) == 0


def test_link_manifestation_lod_task_execution(app):
    """Test Celery task link_manifestation_lod_task execution and state update."""
    from app.core.tasks import link_manifestation_lod_task

    with app.app_context():
        work = Work(title="Foundation", meta={"authors": ["Isaac Asimov"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780553293357")
        db.session.add(manif)
        db.session.commit()

        with (
            patch.object(link_manifestation_lod_task, "update_state") as mock_update_state,
            patch("app.core.lod_linking_service.resolve_manifestation_links", return_value=[]) as mock_resolve,
        ):
            res = link_manifestation_lod_task(manif.id)
            assert res["status"] == "completed"
            assert res["manifestation_id"] == manif.id
            assert mock_update_state.called
            mock_resolve.assert_called_once_with(manif.id)


def test_batch_link_catalog_lod_task_chunking(app):
    """Test batch_link_catalog_lod_task chunking and throttling."""
    from app.core.tasks import batch_link_catalog_lod_task

    with app.app_context():
        manifestation_ids = list(range(1, 26))  # 25 items

        with (
            patch.object(batch_link_catalog_lod_task, "update_state") as mock_update_state,
            patch("app.core.lod_linking_service.resolve_manifestation_links", return_value=[]) as mock_resolve,
            patch("time.sleep") as mock_sleep,
        ):
            res = batch_link_catalog_lod_task(manifestation_ids, chunk_size=10, throttle_delay=0.1)

            assert res["status"] == "completed"
            assert res["total"] == 25
            assert res["processed"] == 25
            assert mock_update_state.called
            assert mock_resolve.call_count == 25
            # 3 chunks (10, 10, 5), sleeps between chunks 1->2 and 2->3 (twice)
            assert mock_sleep.call_count == 2


def test_manifestation_creation_triggers_lod_task(app):
    """Test that creating a manifestation via frbr_service enqueues a background LOD task."""
    from app.core.frbr_service import create_expression, create_manifestation, create_work

    with app.app_context():
        work = create_work(title="Solaris")
        expr = create_expression(work_id=work.id, content_type="text", language="en")

        with patch("app.core.tasks.link_manifestation_lod_task.delay") as mock_delay:
            manif = create_manifestation(expression_id=expr.id, isbn13="9780156027601", format_type="book")
            assert manif.id is not None
            mock_delay.assert_called_once_with(manif.id)


def test_get_semantic_links_api(client, app):
    """Test GET /api/manifestations/<id>/semantic-links returns grouped LOD links."""
    with app.app_context():
        work = Work(title="Hyperion", meta={"authors": ["Dan Simmons"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780553283686")
        db.session.add(manif)
        db.session.flush()

        link = SemanticLink(
            entity_type="work",
            entity_id=work.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Hyperion_(Simmons_novel)",
            pref_label="Hyperion",
            confidence=0.96,
            match_strategy="lookup",
        )
        db.session.add(link)
        db.session.commit()
        manif_id = manif.id

    resp = client.get(f"/api/manifestations/{manif_id}/semantic-links")
    assert resp.status_code == 200
    data = resp.json
    assert data["success"] is True
    assert data["data"]["manifestation_id"] == manif_id
    assert data["data"]["total"] >= 1
    assert "dbpedia" in data["data"]["grouped"]
    assert data["data"]["grouped"]["dbpedia"][0]["pref_label"] == "Hyperion"


def test_trigger_semantic_relink_api(client, normal_user_headers, app):
    """Test POST /api/manifestations/<id>/semantic-links/relink returns 202 with task_id."""
    with app.app_context():
        work = Work(title="Snow Crash")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780553380958")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    with patch("app.core.tasks.link_manifestation_lod_task.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "task-lod-12345"
        mock_delay.return_value = mock_task

        resp = client.post(f"/api/manifestations/{manif_id}/semantic-links/relink", headers=normal_user_headers)
        assert resp.status_code == 202
        data = resp.json
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert data["data"]["task_id"] == "task-lod-12345"


def test_delete_semantic_link_api(client, normal_user_headers, app):
    """Test DELETE /api/manifestations/<id>/semantic-links/<link_id> returns 204."""
    with app.app_context():
        work = Work(title="Cryptonomicon")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780060512804")
        db.session.add(manif)
        db.session.flush()

        link = SemanticLink(
            entity_type="manifestation",
            entity_id=manif.id,
            authority="geonames",
            external_uri="https://sws.geonames.org/999999/",
            pref_label="Wrong Place",
        )
        db.session.add(link)
        db.session.commit()
        manif_id = manif.id
        link_id = link.id

    resp = client.delete(f"/api/manifestations/{manif_id}/semantic-links/{link_id}", headers=normal_user_headers)
    assert resp.status_code == 204

    with app.app_context():
        assert db.session.get(SemanticLink, link_id) is None
