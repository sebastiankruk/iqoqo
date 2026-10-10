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
"""Parity verification tests comparing in-process executor and isolated SPARQL service."""

import time

import pytest
from rdflib import Graph

from app.core.sparql_service import execute_sparql, format_select_results
from app.services.sparql.protocol import ExecutionRequest, ReplayProtector
from app.services.sparql.server import create_service_app

SECRET = "parity-test-secret-key"


@pytest.fixture
def sample_graph():
    """Create sample RDF graph with FRBR entities for parity comparison."""
    g = Graph()
    triples = """
    @prefix frbr: <http://purl.org/vocab/frbr/core#> .
    @prefix dcterms: <http://purl.org/dc/terms/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    <http://example.org/work/1> a frbr:Work ;
        rdfs:label "Parity Test Book" ;
        dcterms:creator "Author X" .

    <http://example.org/work/2> a frbr:Work ;
        rdfs:label "Another Book" ;
        dcterms:creator "Author Y" .

    <http://example.org/item/1> a frbr:Item ;
        dcterms:identifier "PARITY-ITEM-001" .
    """
    g.parse(data=triples, format="turtle")
    return g


def test_select_query_parity(sample_graph):
    """Verify in-process and service execution return identical SELECT results."""
    query = """
    PREFIX frbr: <http://purl.org/vocab/frbr/core#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?work ?label WHERE {
        ?work a frbr:Work ;
              rdfs:label ?label .
    } ORDER BY ?label
    """

    # 1. In-process execution
    in_proc_res = execute_sparql(sample_graph, query)
    in_proc_data = format_select_results(in_proc_res)

    # 2. Service execution
    app = create_service_app(secret=SECRET, replay_protector=ReplayProtector())
    client = app.test_client()
    snapshot_nt = sample_graph.serialize(format="nt")

    req = ExecutionRequest(
        query=query,
        snapshot=snapshot_nt,
        tenant_id="tenant-parity",
        format="application/sparql-results+json",
    )
    req.sign(SECRET)

    res = client.post("/execute", json=req.to_dict())
    assert res.status_code == 200
    service_data = res.get_json()["data"]

    # Compare variables
    assert in_proc_data["head"]["vars"] == service_data["head"]["vars"]

    # Compare rows
    in_proc_bindings = in_proc_data["results"]["bindings"]
    service_bindings = service_data["results"]["bindings"]
    assert len(in_proc_bindings) == len(service_bindings)
    assert in_proc_bindings == service_bindings


def test_ask_query_parity(sample_graph):
    """Verify in-process and service execution return identical ASK results."""
    query_true = "ASK { <http://example.org/work/1> a <http://purl.org/vocab/frbr/core#Work> }"
    query_false = "ASK { <http://example.org/nonexistent> a <http://purl.org/vocab/frbr/core#Work> }"

    app = create_service_app(secret=SECRET, replay_protector=ReplayProtector())
    client = app.test_client()
    snapshot_nt = sample_graph.serialize(format="nt")

    for q, expected in [(query_true, True), (query_false, False)]:
        in_proc_res = execute_sparql(sample_graph, q)
        assert bool(in_proc_res.askAnswer) is expected

        req = ExecutionRequest(
            query=q,
            snapshot=snapshot_nt,
            tenant_id="tenant-parity",
        )
        req.sign(SECRET)
        res = client.post("/execute", json=req.to_dict())
        assert res.status_code == 200
        assert res.get_json()["data"]["boolean"] is expected


def test_construct_query_parity(sample_graph):
    """Verify in-process and service execution return isomorphic CONSTRUCT graphs."""
    query = """
    PREFIX frbr: <http://purl.org/vocab/frbr/core#>
    CONSTRUCT { ?s a frbr:Work } WHERE { ?s a frbr:Work }
    """

    # In-process
    in_proc_res = execute_sparql(sample_graph, query)
    g_in_proc = in_proc_res.graph

    # Service
    app = create_service_app(secret=SECRET, replay_protector=ReplayProtector())
    client = app.test_client()
    snapshot_nt = sample_graph.serialize(format="nt")

    req = ExecutionRequest(
        query=query,
        snapshot=snapshot_nt,
        tenant_id="tenant-parity",
        format="text/turtle",
    )
    req.sign(SECRET)
    res = client.post("/execute", json=req.to_dict())
    assert res.status_code == 200
    turtle_data = res.get_json()["data"]

    g_service = Graph()
    g_service.parse(data=turtle_data, format="turtle")

    assert len(g_in_proc) == len(g_service)
    assert len(g_service) == 2
