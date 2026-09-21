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
"""Tests for SPARQL operation classification and validation."""

import pytest

from app.core.sparql_service import (
    SPARQLSyntaxError,
    SPARQLWriteRejected,
    classify_operation,
    validate_query,
)


class TestOperationClassification:
    """Test operation-aware query classification."""

    def test_classify_select(self):
        """SELECT queries should be classified correctly."""
        assert classify_operation("SELECT ?s WHERE { ?s ?p ?o }") == "SELECT"
        assert classify_operation("SELECT ?s ?p WHERE { ?s ?p ?o } LIMIT 10") == "SELECT"
        assert classify_operation("SELECT DISTINCT ?s WHERE { ?s ?p ?o }") == "SELECT"

    def test_classify_ask(self):
        """ASK queries should be classified correctly."""
        assert classify_operation("ASK { ?s ?p ?o }") == "ASK"
        assert classify_operation("ASK WHERE { ?s ?p ?o }") == "ASK"

    def test_classify_construct(self):
        """CONSTRUCT queries should be classified correctly."""
        assert classify_operation("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }") == "CONSTRUCT"
        assert classify_operation("CONSTRUCT { ?s <http://example.org/p> ?o } WHERE { ?s ?p ?o }") == "CONSTRUCT"

    def test_classify_describe(self):
        """DESCRIBE queries should be classified correctly."""
        assert classify_operation("DESCRIBE <http://example.org/resource>") == "DESCRIBE"
        assert classify_operation("DESCRIBE ?s WHERE { ?s ?p ?o }") == "DESCRIBE"

    def test_reject_insert(self):
        """INSERT operations should be rejected."""
        with pytest.raises(SPARQLWriteRejected):
            classify_operation("INSERT DATA { <http://example.org/s> <http://example.org/p> 'value' }")

        with pytest.raises(SPARQLWriteRejected):
            classify_operation("INSERT { ?s ?p ?o } WHERE { ?s ?p ?o }")

    def test_reject_delete(self):
        """DELETE operations should be rejected."""
        with pytest.raises(SPARQLWriteRejected):
            classify_operation("DELETE WHERE { ?s ?p ?o }")

        with pytest.raises(SPARQLWriteRejected):
            classify_operation("DELETE DATA { <http://example.org/s> <http://example.org/p> 'value' }")

    def test_reject_drop(self):
        """DROP operations should be rejected."""
        with pytest.raises(SPARQLWriteRejected):
            classify_operation("DROP GRAPH <http://example.org/graph>")

        with pytest.raises(SPARQLWriteRejected):
            classify_operation("DROP ALL")

    def test_reject_clear(self):
        """CLEAR operations should be rejected."""
        with pytest.raises(SPARQLWriteRejected):
            classify_operation("CLEAR GRAPH <http://example.org/graph>")

        with pytest.raises(SPARQLWriteRejected):
            classify_operation("CLEAR ALL")

    def test_reject_load(self):
        """LOAD operations should be rejected."""
        with pytest.raises(SPARQLWriteRejected):
            classify_operation("LOAD <http://example.org/data.ttl>")

    def test_select_with_insert_in_literal(self):
        """SELECT with INSERT in a literal should be accepted."""
        query = """
        SELECT ?s WHERE {
            ?s <http://example.org/description> "This is an INSERT operation example"
        }
        """
        assert classify_operation(query) == "SELECT"

    def test_select_with_delete_in_literal(self):
        """SELECT with DELETE in a literal should be accepted."""
        query = """
        SELECT ?s WHERE {
            ?s <http://example.org/action> "DELETE this record"
        }
        """
        assert classify_operation(query) == "SELECT"

    def test_select_with_update_keywords_in_comments(self):
        """SELECT with update keywords in comments should be accepted."""
        query = """
        # This is a comment with INSERT DELETE DROP
        SELECT ?s WHERE {
            ?s ?p ?o
        }
        """
        assert classify_operation(query) == "SELECT"

    def test_select_with_mixed_case_keywords(self):
        """SELECT with mixed case keywords should be accepted."""
        assert classify_operation("select ?s where { ?s ?p ?o }") == "SELECT"
        assert classify_operation("Select ?s Where { ?s ?p ?o }") == "SELECT"
        assert classify_operation("SELECT ?s WHERE { ?s ?p ?o }") == "SELECT"

    def test_malformed_query_syntax_error(self):
        """Malformed queries should raise SPARQLSyntaxError in validate_query."""
        # classify_operation may not catch all syntax errors (it has fallback logic)
        # but validate_query should catch them
        with pytest.raises(SPARQLSyntaxError):
            validate_query("SELECT ?s WHERE { ?s ?p }")  # Missing object

        with pytest.raises(SPARQLSyntaxError):
            validate_query("SELECT ?s WHERE")  # Incomplete WHERE clause

    def test_empty_query(self):
        """Empty queries should raise SPARQLSyntaxError in validate_query."""
        with pytest.raises(SPARQLSyntaxError):
            validate_query("")

        with pytest.raises(SPARQLSyntaxError):
            validate_query("   ")

    def test_query_with_prefixes(self):
        """Queries with PREFIX declarations should be classified correctly."""
        query = """
        PREFIX ex: <http://example.org/>
        SELECT ?s WHERE { ?s ex:predicate ?o }
        """
        assert classify_operation(query) == "SELECT"

    def test_query_with_base(self):
        """Queries with BASE declarations should be classified correctly."""
        query = """
        BASE <http://example.org/>
        SELECT ?s WHERE { ?s <predicate> ?o }
        """
        assert classify_operation(query) == "SELECT"


class TestValidateQuery:
    """Test the validate_query function which combines size, operation, and syntax checks."""

    def test_valid_select_query(self):
        """Valid SELECT query should pass validation."""
        operation = validate_query("SELECT ?s WHERE { ?s ?p ?o }")
        assert operation == "SELECT"

    def test_valid_ask_query(self):
        """Valid ASK query should pass validation."""
        operation = validate_query("ASK { ?s ?p ?o }")
        assert operation == "ASK"

    def test_valid_construct_query(self):
        """Valid CONSTRUCT query should pass validation."""
        operation = validate_query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
        assert operation == "CONSTRUCT"

    def test_valid_describe_query(self):
        """Valid DESCRIBE query should pass validation."""
        operation = validate_query("DESCRIBE <http://example.org/resource>")
        assert operation == "DESCRIBE"

    def test_oversized_query_rejected(self):
        """Queries exceeding MAX_QUERY_LENGTH should be rejected."""
        from app.core.sparql_service import SPARQLQueryTooLarge

        large_query = "SELECT ?s WHERE { ?s ?p ?o } #" + "x" * 20000
        with pytest.raises(SPARQLQueryTooLarge):
            validate_query(large_query)

    def test_write_operation_rejected(self):
        """Write operations should be rejected."""
        with pytest.raises(SPARQLWriteRejected):
            validate_query("INSERT DATA { <http://example.org/s> <http://example.org/p> 'value' }")

    def test_syntax_error_rejected(self):
        """Syntax errors should be rejected."""
        with pytest.raises(SPARQLSyntaxError):
            validate_query("SELECT ?s WHERE { ?s ?p }")

    def test_query_with_literal_containing_update_keywords(self):
        """Queries with update keywords in literals should be accepted."""
        query = 'SELECT ?s WHERE { ?s ?p "INSERT DELETE DROP" }'
        operation = validate_query(query)
        assert operation == "SELECT"

    def test_query_with_comments_containing_update_keywords(self):
        """Queries with update keywords in comments should be accepted."""
        query = """
        # INSERT DELETE DROP are mentioned here
        SELECT ?s WHERE { ?s ?p ?o }
        """
        operation = validate_query(query)
        assert operation == "SELECT"

    def test_encoded_query_input(self):
        """URL-encoded queries should be handled correctly."""
        # This simulates what happens when Flask decodes URL parameters
        query = "SELECT ?s WHERE { ?s ?p ?o }"
        operation = validate_query(query)
        assert operation == "SELECT"

    def test_multiline_query(self):
        """Multiline queries should be handled correctly."""
        query = """
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o .
            FILTER(?o > 10)
        }
        LIMIT 100
        """
        operation = validate_query(query)
        assert operation == "SELECT"

    def test_query_with_unicode(self):
        """Queries with Unicode characters should be handled correctly."""
        query = 'SELECT ?s WHERE { ?s <http://example.org/名前> "テスト" }'
        operation = validate_query(query)
        assert operation == "SELECT"
