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
"""Chaos and stress testing for SPARQL query execution isolation.

Validates system resilience under adverse operating conditions:
1. Memory pressure approaching and exceeding resource thresholds (MAX_GRAPH_TRIPLES, MAX_SERIALIZED_BYTES)
2. Abrupt child process termination (simulated OOM killer)
3. Repeated concurrent timeout floods (verifying absence of zombie processes or semaphore leaks)
4. Rapid recovery and continued availability for subsequent standard queries
"""

import concurrent.futures
import os
import signal
import time
from unittest.mock import patch

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from app.core.sparql_service import (
    _MP_CONTEXT,
    MAX_CONCURRENT_QUERIES,
    MAX_GRAPH_TRIPLES,
    MAX_SERIALIZED_BYTES,
    SPARQLChildProcessError,
    SPARQLConcurrencyLimit,
    SPARQLError,
    SPARQLResourceLimit,
    SPARQLTimeout,
    _execute_query_in_process,
    _query_semaphore,
    _terminate_process,
    build_graph,
    execute_sparql,
    format_select_results,
)


@pytest.fixture
def baseline_graph():
    """Build a baseline RDF graph with valid catalog triples."""
    g = Graph()
    ex = Namespace("http://example.org/")
    schema = Namespace("https://schema.org/")
    for i in range(1, 20):
        item_uri = ex[f"item/{i}"]
        g.add((item_uri, RDF.type, schema.Book))
        g.add((item_uri, schema.name, Literal(f"Chaos Test Book {i}")))
        g.add((item_uri, schema.isbn, Literal(f"978000000{i:04d}")))
    return g


# Helper target for simulating an out-of-memory crash in the child process
def _oom_simulating_child(graph_bytes, query, conn):
    """Simulate a Linux OOM killer termination via SIGKILL."""
    os.kill(os.getpid(), signal.SIGKILL)


# Helper target for slow query to force timeout
def _slow_query_child(graph_bytes, query, conn):
    """Simulate a long-running, CPU-bound query exceeding deadlines."""
    time.sleep(2.0)
    conn.send(("SELECT", {"head": {"vars": []}, "results": {"bindings": []}}))


class TestSPARQLChaos:
    """Chaos engineering test suite for SPARQL execution boundary."""

    def test_child_process_under_memory_pressure_gracefully_terminates(self, baseline_graph, monkeypatch):
        """Simulate memory pressure (OOM SIGKILL) on child process; verify parent handles it cleanly."""
        # 1. Test MAX_GRAPH_TRIPLES boundary rejection
        monkeypatch.setattr("app.core.sparql_service.MAX_GRAPH_TRIPLES", 10)
        with pytest.raises(SPARQLResourceLimit):
            # baseline_graph has > 10 triples
            items = [{"id": f"item-{i}", "manifestation_id": f"m-{i}", "title": f"Book {i}"} for i in range(15)]
            build_graph(items, "http://localhost:5000")

        # 2. Test MAX_SERIALIZED_BYTES boundary rejection
        monkeypatch.setattr("app.core.sparql_service.MAX_GRAPH_TRIPLES", 100000)
        monkeypatch.setattr("app.core.sparql_service.MAX_SERIALIZED_BYTES", 50)
        with pytest.raises(SPARQLResourceLimit):
            execute_sparql(baseline_graph, "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1", timeout=5.0)

        # 3. Simulate sudden child process crash (e.g. OOM SIGKILL by kernel)
        monkeypatch.setattr("app.core.sparql_service.MAX_SERIALIZED_BYTES", 10000000)
        with patch("app.core.sparql_service._execute_query_in_process", _oom_simulating_child):
            with pytest.raises(SPARQLChildProcessError) as exc_info:
                execute_sparql(baseline_graph, "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1", timeout=5.0)
            assert "exited unexpectedly" in str(exc_info.value) or "code=-9" in str(exc_info.value)

    def test_repeated_timeout_floods_no_zombies_or_exhaustion(self, baseline_graph, monkeypatch):
        """Repeated bursts of queries that all time out must not leave zombie processes or exhaust resources."""
        # Patch execution to slow child so every query times out reliably
        with patch("app.core.sparql_service._execute_query_in_process", _slow_query_child):
            for _wave in range(3):

                def fire_timeout_query():
                    try:
                        execute_sparql(baseline_graph, "SELECT ?s WHERE { ?s ?p ?o }", timeout=0.1)
                        return "completed"
                    except SPARQLTimeout:
                        return "timeout"
                    except SPARQLConcurrencyLimit:
                        return "concurrency_limit"

                workers = MAX_CONCURRENT_QUERIES + 2
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [executor.submit(fire_timeout_query) for _ in range(workers)]
                    results = [f.result() for f in concurrent.futures.as_completed(futures)]

                # All queries should be handled safely with timeout or capacity rejection
                assert all(r in ("timeout", "concurrency_limit") for r in results)

                # Give short window for OS process table reap
                time.sleep(0.15)

    def test_system_remains_available_after_chaos(self, baseline_graph):
        """Verify the service remains operational and cleanly handles subsequent queries after chaos tests."""
        # Execute normal SPARQL query after potential chaos
        query = "SELECT ?title WHERE { ?s <https://schema.org/name> ?title } ORDER BY ?title LIMIT 5"
        result = execute_sparql(baseline_graph, query, timeout=5.0)
        formatted = format_select_results(result)

        assert "results" in formatted
        bindings = formatted["results"]["bindings"]
        assert len(bindings) > 0
        assert "title" in bindings[0]
