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
            assert result["confidence"] == 0.85
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

        # Mock _resolve_local to None to specifically verify remote resolution and caching
        with patch.object(GeoNamesClient, "_resolve_local", return_value=None), patch("requests.get", return_value=mock_resp) as mock_get:
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


def test_geonames_client_local_gazetteer_resolution(app):
    """Test GeoNamesClient resolving places directly from local offline SQLite gazetteer."""
    with app.app_context():
        cache.delete("lod:geonames:warsaw")
        cache.delete("lod:geonames:warszawa")
        cache.delete("lod:geonames:new york")

        with patch("requests.get") as mock_get:
            res_warsaw = GeoNamesClient.resolve_location("Warsaw")
            assert res_warsaw is not None
            assert res_warsaw["uri"] == "https://sws.geonames.org/756135/"
            assert res_warsaw["label"] == "Warsaw"
            assert res_warsaw["confidence"] == 0.95
            assert res_warsaw["strategy"] == "local_gazetteer"
            assert res_warsaw["attributes"]["country_code"] == "PL"
            assert mock_get.call_count == 0  # Zero network calls!

            # Test multilingual alternate name (Warszawa -> Warsaw)
            res_warszawa = GeoNamesClient.resolve_location("Warszawa")
            assert res_warszawa is not None
            assert res_warszawa["uri"] == "https://sws.geonames.org/756135/"
            assert mock_get.call_count == 0

            # Test NYC / New York
            res_ny = GeoNamesClient.resolve_location("New York")
            assert res_ny is not None
            assert res_ny["uri"] == "https://sws.geonames.org/5128581/"
            assert mock_get.call_count == 0


def test_geonames_client_missing_database_graceful_fallback(app):
    """Test GeoNamesClient gracefully falls back to remote API when database is absent."""
    with app.app_context():
        cache.delete("lod:geonames:remoteville")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"geonames": [{"geonameId": 999999, "name": "Remoteville", "countryCode": "US"}]}

        with (
            patch.dict("os.environ", {"GEONAMES_DB_PATH": "/tmp/nonexistent_geonames.db"}),
            patch("requests.get", return_value=mock_resp) as mock_get,
        ):
            res = GeoNamesClient.resolve_location("Remoteville")
            assert res is not None
            assert res["uri"] == "https://sws.geonames.org/999999/"
            assert res["strategy"] == "lookup"
            assert mock_get.call_count == 1


def test_geonames_client_remote_auth_error_resilience(app):
    """Test GeoNamesClient cleanly handles remote HTTP 401 / error 10 without raising exceptions."""
    with app.app_context():
        cache.delete("lod:geonames:authfailcity")
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"status": {"message": "<!DOCTYPE html>", "value": 10}}

        with patch.object(GeoNamesClient, "_resolve_local", return_value=None), patch("requests.get", return_value=mock_resp):
            res = GeoNamesClient.resolve_location("AuthFailCity")
            assert res is None


def test_wordnet_mapper_resolution(app):
    """Test WordNetMapper local dictionary mapping and fallback."""
    with app.app_context():
        # Local dictionary hit
        res_local = WordNetMapper.resolve_tag("science fiction")
        assert res_local is not None
        assert res_local["uri"] == "http://wordnet-rdf.princeton.edu/id/06363630-n"
        assert res_local["authority"] == "wordnet"
        assert res_local["strategy"] == "synset"
        assert res_local["attributes"]["source"] == "local_dictionary"

        # Fallback for novel concept when DBpedia category is valid
        mock_valid = MagicMock()
        mock_valid.status_code = 200
        with patch("requests.get", return_value=mock_valid):
            res_fallback = WordNetMapper.resolve_tag("cyberpunk")
            assert res_fallback is not None
            assert res_fallback["uri"] == "http://dbpedia.org/resource/Category:Cyberpunk"
            assert res_fallback["authority"] == "dbpedia"
            assert res_fallback["strategy"] == "dbpedia_category"
            assert res_fallback["confidence"] == 0.70

        # Non-existent DBpedia category returns None without persisting fake category
        mock_invalid = MagicMock()
        mock_invalid.status_code = 404
        with patch("requests.get", return_value=mock_invalid):
            res_invalid = WordNetMapper.resolve_tag("nonexistent_tag_xyz")
            assert res_invalid is None


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
                                "comment": ["Neuromancer is a 1984 science fiction novel by William Gibson."],
                                "typeName": ["dbo:Book", "dbo:Work"],
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
                                "comment": ["William Ford Gibson is an American-Canadian speculative fiction writer."],
                                "typeName": ["dbo:Person", "dbo:Writer"],
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
            work_links = work.get_semantic_links(status=None)
            assert any(link.authority == "dbpedia" and "Neuromancer" in link.external_uri for link in work_links)
            assert any(link.authority == "dbpedia" and "William_Gibson" in link.external_uri for link in work_links)
            assert any(link.authority == "wordnet" for link in work_links)
            assert not any(link.authority == "wordnet" and "dbpedia.org" in link.external_uri for link in work_links)
            assert any(link.authority == "dbpedia" and "Category:Cyberpunk" in link.external_uri for link in work_links)

            # Verify Manifestation-level links (GeoNames New York)
            manif_direct = manif.get_semantic_links(include_work=False, status=None)
            assert len(manif_direct) == 1
            assert manif_direct[0].authority == "geonames"
            assert "5128581" in manif_direct[0].external_uri

            # Verify scoped retrieval
            all_links = manif.get_semantic_links(include_work=True, status=None)
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


def test_trigger_semantic_relink_api(client, custodian_headers, app):
    """Test POST /api/manifestations/<id>/semantic-links/relink returns 202 with task_id.

    Uses `custodian_headers` rather than `normal_user_headers`: the endpoint is
    gated on `write:metadata` because the task performs outbound authority
    lookups. `test_trigger_semantic_relink_rejects_a_standard_user` covers the
    refusal; this test covers the happy path.
    """
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

        resp = client.post(f"/api/manifestations/{manif_id}/semantic-links/relink", headers=custodian_headers)
        assert resp.status_code == 202
        data = resp.json
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert data["data"]["task_id"] == "task-lod-12345"


def test_delete_semantic_link_api(client, custodian_headers, app):
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

    resp = client.delete(f"/api/manifestations/{manif_id}/semantic-links/{link_id}", headers=custodian_headers)
    assert resp.status_code == 204

    with app.app_context():
        assert db.session.get(SemanticLink, link_id) is None


@pytest.mark.parametrize(
    ("method", "needs_link_id"),
    [("post", False), ("delete", True)],
)
def test_semantic_link_mutation_rejects_a_standard_user(client, normal_user_headers, app, method, needs_link_id):
    """Both semantic-link mutations are custodian-only.

    `normal_user_headers` holds `write:item` and nothing else, so a 403 here
    proves the permission is actually enforced rather than merely present in the
    decorator list. Both routes are covered by one parametrised test because they
    failed for the same reason: they were declared `@require_auth` with no
    permission gate at all, so any signed-in user could enqueue outbound
    authority lookups for any manifestation, or delete links the reconciler had
    established. Asserting the refusal is what stops a later hardening from
    reading as a regression.
    """
    with app.app_context():
        work = Work(title="Neuromancer")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9780441007462")
        db.session.add(manif)
        db.session.flush()

        link = SemanticLink(
            entity_type="manifestation",
            entity_id=manif.id,
            authority="geonames",
            external_uri="https://sws.geonames.org/999999/",
            pref_label="Somewhere",
        )
        db.session.add(link)
        db.session.commit()
        manif_id = manif.id
        link_id = link.id

    # The relink route takes no link id; the delete route requires one.
    tail = f"{link_id}" if needs_link_id else "relink"
    url = f"/api/manifestations/{manif_id}/semantic-links/{tail}"
    with patch("app.core.tasks.link_manifestation_lod_task.delay") as mock_delay:
        resp = getattr(client, method)(url, headers=normal_user_headers)
        mock_delay.assert_not_called()

    assert resp.status_code == 403, f"{method.upper()} {url} should require write:metadata"

    # The refusal must be a refusal, not a partial write.
    with app.app_context():
        assert db.session.get(SemanticLink, link_id) is not None


def test_dbpedia_silmarillion_lookup_parameters_and_tags(app):
    """Test that DBpedia lookup passes format=json, short typeName, and cleans HTML tags."""
    with app.app_context():
        cache.delete("lod:dbpedia:work:the silmarillion:dbo:Book")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "docs": [
                {
                    "resource": ["http://dbpedia.org/resource/The_Silmarillion"],
                    "label": ["<B>The</B> <B>Silmarillion</B>"],
                    "score": [7090.79],
                    "comment": ["<B>The</B> <B>Silmarillion</B> is a collection of mythopoeic works by J.R.R. Tolkien"],
                    "typeName": ["Book", "WrittenWork", "Work"],
                }
            ]
        }

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = DBpediaClient.resolve_work("The Silmarillion", media_category="text")
            assert result is not None
            assert result["uri"] == "http://dbpedia.org/resource/The_Silmarillion"
            assert result["label"] == "The Silmarillion"
            assert "<B>" not in result["label"]
            assert "<B>" not in result["attributes"]["comment"]
            assert result["confidence"] == 0.85

            # Assert request params
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["params"]["format"] == "json"
            assert call_kwargs["params"]["typeName"] == "Book"
            assert call_kwargs["params"]["query"] == "The Silmarillion"


def test_dbpedia_subtitle_fallback_resolution(app):
    """Test that creative works with subtitles fall back to main title on DBpedia lookup."""
    with app.app_context():
        cache.delete("lod:dbpedia:work:the silmarillion: illustrated edition:dbo:Book")

        mock_empty = MagicMock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = {"docs": []}

        mock_hit = MagicMock()
        mock_hit.status_code = 200
        mock_hit.json.return_value = {
            "docs": [
                {
                    "resource": ["http://dbpedia.org/resource/The_Silmarillion"],
                    "label": ["The Silmarillion"],
                    "score": [100.0],
                }
            ]
        }

        with patch("requests.get", side_effect=[mock_empty, mock_hit]) as mock_get:
            result = DBpediaClient.resolve_work("The Silmarillion: Illustrated Edition", media_category="book")
            assert result is not None
            assert result["uri"] == "http://dbpedia.org/resource/The_Silmarillion"
            assert mock_get.call_count == 2
            # Second call should query main title
            second_call_params = mock_get.call_args_list[1][1]["params"]
            assert second_call_params["query"] == "The Silmarillion"


def test_geonames_resolve_location_with_qualifiers(app):
    """Test that locations with qualifiers (commas, parentheses) resolve correctly."""
    with app.app_context():
        res_cph = GeoNamesClient.resolve_location("Copenhagen (denmark)")
        assert res_cph is not None
        assert res_cph["label"] == "Copenhagen"
        assert res_cph["attributes"]["country_code"] == "DK"

        res_berk = GeoNamesClient.resolve_location("Berkeley, Calif")
        assert res_berk is not None
        assert res_berk["label"] == "Berkeley"
        assert res_berk["attributes"]["country_code"] == "US"

        res_pohang = GeoNamesClient.resolve_location("Pohang, Korea")
        assert res_pohang is not None
        assert res_pohang["label"] == "Pohang"
        assert res_pohang["attributes"]["country_code"] == "KR"


def test_geonames_extract_locations_from_title_and_publisher(app):
    """Test high-precision extraction from title and publisher strings."""
    with app.app_context():
        hits_cph = GeoNamesClient.extract_locations_from_text("Time Out Copenhagen")
        assert len(hits_cph) == 1
        assert hits_cph[0]["label"] == "Copenhagen"
        assert hits_cph[0]["attributes"]["geoname_id"] == 2618425

        hits_krk = GeoNamesClient.extract_locations_from_text("Wydawnictwo Literackie, Kraków")
        assert len(hits_krk) == 1
        assert hits_krk[0]["label"] == "Kraków"
        assert hits_krk[0]["attributes"]["country_code"] == "PL"

        hits_stopwords = GeoNamesClient.extract_locations_from_text("A Tale of Two Cities")
        assert len(hits_stopwords) == 0


def test_resolve_manifestation_links_copenhagen_and_frbr_scoping(app):
    """Test full pipeline: manifestation 'Time Out Copenhagen' gets Work-level GeoNames link, and publish_places get Manifestation-level link."""
    with app.app_context():
        work = Work(title="Time Out Copenhagen", meta={"authors": ["Michael Booth"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(
            expression_id=expr.id,
            isbn13="9780141008394",
            publisher="Penguin Group USA",
            meta={
                "publish_places": [{"name": "Berkeley, Calif"}],
            },
        )
        db.session.add(manif)
        db.session.flush()

        links = resolve_manifestation_links(manif.id, fast_mode=True)
        assert len(links) >= 2

        # Verify Work-level GeoNames link for Copenhagen
        work_geo_links = [link_obj for link_obj in links if link_obj.entity_type == "work" and link_obj.authority == "geonames"]
        assert len(work_geo_links) == 1
        assert work_geo_links[0].pref_label == "Copenhagen"
        assert work_geo_links[0].attributes["role"] == "subject_place"

        # Verify Manifestation-level GeoNames link for Berkeley
        manif_geo_links = [link_obj for link_obj in links if link_obj.entity_type == "manifestation" and link_obj.authority == "geonames"]
        assert len(manif_geo_links) == 1
        assert manif_geo_links[0].pref_label == "Berkeley"
        assert manif_geo_links[0].attributes["role"] == "publication_place"
        assert manif_geo_links[0].status == "accepted"


def test_compute_composite_score_precision():
    """Verify composite scoring incorporating label similarity, author corroboration, year proximity, and rank margin."""
    from app.core.lod_linking_service import compute_composite_score

    # Perfect match with corroboration
    score_full = compute_composite_score(
        candidate_label="Dune (novel)",
        target_title="Dune",
        author="Frank Herbert",
        candidate_comment="Dune is a 1965 sci-fi novel by Frank Herbert.",
        year=1965,
        rank_margin=0.8,
        has_class_match=True,
    )
    assert score_full >= 0.85

    # Disambiguation page rejected
    score_disambig = compute_composite_score(
        candidate_label="Dune (disambiguation)",
        target_title="Dune",
        author="Frank Herbert",
        candidate_comment="Dune may refer to:",
        year=1965,
        rank_margin=0.8,
        has_class_match=True,
    )
    assert score_disambig == 0.0

    # Wrong class rejected
    score_wrong_class = compute_composite_score(
        candidate_label="Dune",
        target_title="Dune",
        has_class_match=False,
    )
    assert score_wrong_class == 0.0

    # False positive candidate (different work, wrong author) rejected below suggestion threshold
    score_rejected = compute_composite_score(
        candidate_label="Dune: Part Two",
        target_title="Dune",
        author="Frank Herbert",
        candidate_comment="Dune: Part Two is a film directed by Denis Villeneuve.",
        year=1965,
        rank_margin=0.1,
        has_class_match=True,
    )
    assert score_rejected < 0.55

    # Title match without author corroboration produces suggestion score in [0.55, 0.82)
    score_suggested = compute_composite_score(
        candidate_label="Dune",
        target_title="Dune",
        author="Uncorroborated Author",
        candidate_comment="Dune is an epic science fiction universe.",
        year=None,
        rank_margin=0.5,
        has_class_match=True,
    )
    assert 0.55 <= score_suggested < 0.82


def test_dbpedia_client_class_and_disambiguation_filtering(app):
    """Verify DBpediaClient filters out disambiguation pages and incompatible ontology classes."""
    with app.app_context():
        cache.delete("lod:dbpedia:work:dune:dbo:Book::")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "docs": [
                {
                    "resource": ["http://dbpedia.org/resource/Dune_(disambiguation)"],
                    "label": ["Dune (disambiguation)"],
                    "score": [120.0],
                    "comment": ["Dune may refer to:"],
                    "typeName": ["Work"],
                },
                {
                    "resource": ["http://dbpedia.org/resource/Dune_Band"],
                    "label": ["Dune"],
                    "score": [110.0],
                    "comment": ["Dune is a German electronic music group."],
                    "typeName": ["Band", "MusicalArtist"],
                },
                {
                    "resource": ["http://dbpedia.org/resource/Dune_(novel)"],
                    "label": ["Dune (novel)"],
                    "score": [95.0],
                    "comment": ["Dune is a 1965 sci-fi novel by Frank Herbert."],
                    "typeName": ["dbo:Book", "dbo:Work"],
                },
            ]
        }

        with patch("requests.get", return_value=mock_resp):
            result = DBpediaClient.resolve_work("Dune", media_category="book")
            assert result is not None
            assert result["uri"] == "http://dbpedia.org/resource/Dune_(novel)"
            assert result["confidence"] >= 0.80


def test_dual_threshold_status_tagging(app):
    """Verify dual thresholds tag links as accepted (>=0.82) or suggested (>=0.55)."""
    with app.app_context():
        work = Work(title="Test Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780000000001", meta={"publication_place": "Warsaw"})
        db.session.add(manif)
        db.session.flush()

        # Mock resolve_work to return 0.70 (suggested)
        mock_work_match = {
            "uri": "http://dbpedia.org/resource/Test_Work",
            "label": "Test Work",
            "confidence": 0.70,
            "strategy": "lookup",
            "attributes": {"dbo_type": "dbo:Book"},
        }

        with (
            patch.object(DBpediaClient, "resolve_work", return_value=mock_work_match),
            patch.object(
                GeoNamesClient,
                "resolve_location",
                return_value={
                    "uri": "https://sws.geonames.org/756135/",
                    "label": "Warsaw",
                    "confidence": 0.95,
                    "strategy": "local_gazetteer",
                    "attributes": {"role": "publication_place"},
                },
            ),
        ):
            links = resolve_manifestation_links(manif.id, fast_mode=True)
            work_links = [lnk for lnk in links if lnk.entity_type == "work"]
            manif_links = [lnk for lnk in links if lnk.entity_type == "manifestation"]

            assert len(work_links) == 1
            assert work_links[0].status == "suggested"

            assert len(manif_links) == 1
            assert manif_links[0].status == "accepted"
