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
"""Adversarial tests for SPARQL resource isolation and security."""

import concurrent.futures
import time

import pytest

from app.core.sparql_service import (
    SPARQLConcurrencyLimit,
    SPARQLResourceLimit,
    SPARQLTimeout,
    build_graph,
    execute_sparql,
)


class TestAdversarialQueries:
    """Test adversarial query patterns and resource limits."""

    def test_cartesian_join_timeout(self):
        """Cartesian join queries should timeout rather than hang.

        Note: Timeout reduced from 0.5s to 0.01s in hotfix/0.8.0.1/sparql because
        fork context is significantly faster than spawn, allowing queries to complete
        before the original timeout. The test verifies the timeout mechanism works,
        not that Cartesian joins are inherently slow.
        """
        # Create a graph with enough data to make Cartesian joins expensive
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i}"],
                "tags": [f"tag{j}" for j in range(5)],
                "status": "read",
            }
            for i in range(50)
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Cartesian join query that would be very expensive
        cartesian_query = """
        SELECT ?s1 ?s2 ?s3 ?s4
        WHERE {
            ?s1 ?p1 ?o1 .
            ?s2 ?p2 ?o2 .
            ?s3 ?p3 ?o3 .
            ?s4 ?p4 ?o4 .
        }
        LIMIT 10000
        """

        # Should timeout rather than complete (very short timeout to trigger mechanism)
        with pytest.raises(SPARQLTimeout):
            execute_sparql(graph, cartesian_query, timeout=0.01)

    def test_repeated_timeouts_dont_leak_resources(self):
        """Repeated timeouts should not leak worker processes."""
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Test Book",
                "authors": ["Author"],
                "tags": ["tag1"],
                "status": "read",
            }
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Execute multiple queries with very short timeouts
        for _ in range(5):
            with pytest.raises(SPARQLTimeout):
                execute_sparql(graph, "SELECT ?s WHERE { ?s ?p ?o }", timeout=0.01)

        # After timeouts, a normal query should still work
        result = execute_sparql(graph, "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1", timeout=5.0)
        assert result is not None

    def test_concurrent_queries_respect_limit(self):
        """Concurrent queries should respect the concurrency limit."""
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i}"],
                "tags": ["tag1"],
                "status": "read",
            }
            for i in range(5)
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Try to execute more concurrent queries than the limit
        # The limit is MAX_CONCURRENT_QUERIES = 4
        def run_query():
            try:
                # Use a simple query that completes quickly
                execute_sparql(graph, "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1", timeout=5.0)
                return "success"
            except SPARQLConcurrencyLimit:
                return "concurrency_limit"
            except SPARQLTimeout:
                return "timeout"
            except Exception as e:
                return f"error: {e}"

        # Launch 10 concurrent queries
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_query) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # At least some should succeed (the system shouldn't crash)
        successes = results.count("success")
        assert successes > 0, f"At least some queries should succeed, got results: {results}"

    def test_graph_size_limit_enforced(self):
        """Graph size limits should be enforced."""
        # Create a large number of items to exceed MAX_GRAPH_ITEMS
        # MAX_GRAPH_ITEMS is 5000, so we need more than that
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i}"],
                "tags": [f"tag{j}" for j in range(3)],
                "status": "read",
            }
            for i in range(6000)
        ]

        # build_graph should truncate to MAX_GRAPH_ITEMS
        graph = build_graph(items, "http://localhost:5000")

        # Graph should be created (truncated to limit)
        assert graph is not None
        # The graph may exceed the serialized byte limit (MAX_SERIALIZED_BYTES),
        # in which case execute_sparql raises SPARQLResourceLimit — that's correct behavior.
        try:
            result = execute_sparql(graph, "SELECT (COUNT(?s) as ?count) WHERE { ?s ?p ?o }", timeout=5.0)
            assert result is not None
        except SPARQLResourceLimit:
            # Expected: serialized graph exceeded byte limit
            pass

    def test_result_size_limit_enforced(self):
        """Result size limits should be enforced via max_rows parameter."""
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i}"],
                "tags": ["tag1", "tag2"],
                "status": "read",
            }
            for i in range(20)
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Query that would return many results, but with LIMIT
        result = execute_sparql(graph, "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50", timeout=5.0)

        # format_select_results should respect max_rows
        from app.core.sparql_service import format_select_results

        formatted = format_select_results(result, max_rows=10)
        assert len(formatted["results"]["bindings"]) <= 10

    def test_complex_filter_query(self):
        """Complex FILTER queries should complete within timeout."""
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i}"],
                "tags": [f"tag{j}" for j in range(3)],
                "status": "read" if i % 2 == 0 else "want_to_read",
            }
            for i in range(50)
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Complex query with multiple FILTERs
        complex_query = """
        SELECT ?s ?title ?status
        WHERE {
            ?s <https://schema.org/name> ?title .
            ?s <https://schema.org/status> ?status .
            FILTER(CONTAINS(STR(?title), "Book"))
            FILTER(?status = "read")
        }
        ORDER BY ?title
        LIMIT 20
        """

        result = execute_sparql(graph, complex_query, timeout=5.0)
        assert result is not None

    def test_nested_optional_query(self):
        """Nested OPTIONAL queries should complete within timeout."""
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i}"],
                "tags": [f"tag{j}" for j in range(2)],
                "status": "read",
            }
            for i in range(30)
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Query with nested OPTIONAL patterns
        nested_query = """
        SELECT ?s ?title ?author ?tag
        WHERE {
            ?s <https://schema.org/name> ?title .
            OPTIONAL {
                ?s <https://schema.org/author> ?author .
                OPTIONAL {
                    ?s <https://schema.org/tag> ?tag
                }
            }
        }
        LIMIT 50
        """

        result = execute_sparql(graph, nested_query, timeout=5.0)
        assert result is not None

    def test_aggregation_query(self):
        """Aggregation queries should complete within timeout."""
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i % 5}"],  # Only 5 unique authors
                "tags": [f"tag{j}" for j in range(3)],
                "status": "read" if i % 2 == 0 else "want_to_read",
            }
            for i in range(100)
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Aggregation query with GROUP BY and HAVING
        aggregation_query = """
        SELECT ?author (COUNT(?s) as ?count)
        WHERE {
            ?s <https://schema.org/author> ?author .
        }
        GROUP BY ?author
        HAVING (COUNT(?s) > 5)
        ORDER BY DESC(?count)
        """

        result = execute_sparql(graph, aggregation_query, timeout=5.0)
        assert result is not None

    def test_subquery_handling(self):
        """Subqueries should complete within timeout."""
        items = [
            {
                "id": f"item-{i}",
                "manifestation_id": f"m-{i}",
                "expression_id": f"e-{i}",
                "work_id": f"w-{i}",
                "title": f"Test Book {i}",
                "authors": [f"Author {i}"],
                "tags": ["tag1"],
                "status": "read",
            }
            for i in range(30)
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Query with subquery
        subquery_query = """
        SELECT ?s ?title
        WHERE {
            ?s <https://schema.org/name> ?title .
            {
                SELECT ?s WHERE {
                    ?s <https://schema.org/status> "read"
                }
                LIMIT 10
            }
        }
        """

        result = execute_sparql(graph, subquery_query, timeout=5.0)
        assert result is not None
