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
"""Automated test suite for SHACL service and sync_ontology script."""

import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from app.core.shacl_service import (
    _get_ontology_graph,
    _get_shapes_graph,
    clear_cache,
    validate_graph,
    validate_rdf_string,
)
from scripts import sync_ontology
from scripts.sync_ontology import (
    MAPPED_PROPERTY_CONTRACT,
    MODEL_CLASS_MAP,
    REQUIRED_SHAPE_CONTRACT,
    check_drift,
    get_db_model_classes,
    get_ontology_classes,
    validate_turtle_syntax,
)

IQOQO = Namespace("https://iqoqo.org/ontology#")
ROOT_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def reset_shacl_cache():
    """Ensure shacl_service cache is reset before and after each test."""
    clear_cache()
    yield
    clear_cache()


# ===========================================================================
# 1. SHACL Service Tests
# ===========================================================================


class TestSHACLService:
    """Test suite verifying app/core/shacl_service.py caching and validation."""

    def test_cache_loading_and_reset(self) -> None:
        """Verify shapes and ontology graphs are cached and cleared."""
        shapes1 = _get_shapes_graph()
        shapes2 = _get_shapes_graph()
        assert shapes1 is shapes2

        ont1 = _get_ontology_graph()
        ont2 = _get_ontology_graph()
        assert ont1 is ont2

        clear_cache()
        shapes3 = _get_shapes_graph()
        assert shapes3 is not shapes1

    def test_validate_graph_conforming(self) -> None:
        """Verify a valid RDF graph conforms using default shapes and ontology."""
        g = Graph()
        g.bind("iqoqo", IQOQO)

        u = URIRef("https://iqoqo.org/users/1")
        w = URIRef("https://iqoqo.org/works/1")
        g.add((u, RDF.type, IQOQO.User))
        g.add((w, RDF.type, IQOQO.Work))

        # Valid UserWorkIntent
        intent = URIRef("https://iqoqo.org/intents/1")
        g.add((intent, RDF.type, IQOQO.UserWorkIntent))
        g.add((intent, IQOQO.intentWork, w))
        g.add((intent, IQOQO.intentUser, u))
        g.add((intent, IQOQO.intentStatus, Literal("want_to_read")))

        conforms, res_graph, report = validate_graph(g)
        assert conforms is True, f"Expected conforming graph, got violations: {report}"
        assert isinstance(res_graph, Graph)

    def test_validate_graph_non_conforming(self) -> None:
        """Verify invalid properties violate SHACL shapes."""
        g = Graph()
        g.bind("iqoqo", IQOQO)

        # Missing required intentWork and intentUser
        intent = URIRef("https://iqoqo.org/intents/bad")
        g.add((intent, RDF.type, IQOQO.UserWorkIntent))
        g.add((intent, IQOQO.intentStatus, Literal("want_to_read")))

        conforms, _, report = validate_graph(g)
        assert conforms is False
        assert "UserWorkIntent" in report

    def test_validate_rdf_string_turtle(self) -> None:
        """Verify validate_rdf_string with valid Turtle syntax."""
        turtle_data = """
        @prefix iqoqo: <https://iqoqo.org/ontology#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        <https://iqoqo.org/tags/1> a iqoqo:Tag ;
            iqoqo:tagName "science-fiction" .
        """
        conforms, report = validate_rdf_string(turtle_data, rdf_format="turtle")
        assert conforms is True, f"Expected valid tag turtle to conform: {report}"

    def test_validate_rdf_string_json_ld(self) -> None:
        """Verify validate_rdf_string with valid JSON-LD syntax."""
        jsonld_data = """
        {
            "@context": {
                "iqoqo": "https://iqoqo.org/ontology#"
            },
            "@id": "https://iqoqo.org/tags/2",
            "@type": "iqoqo:Tag",
            "iqoqo:tagName": "cyberpunk"
        }
        """
        conforms, report = validate_rdf_string(jsonld_data, rdf_format="json-ld")
        assert conforms is True, f"Expected valid tag JSON-LD to conform: {report}"

    def test_validate_rdf_string_return_graph(self) -> None:
        """Verify validate_rdf_string with return_graph=True returns 3-tuple."""
        turtle_data = """
        @prefix iqoqo: <https://iqoqo.org/ontology#> .
        <https://iqoqo.org/tags/3> a iqoqo:Tag ;
            iqoqo:tagName "fantasy" .
        """
        result = validate_rdf_string(turtle_data, rdf_format="turtle", return_graph=True)
        assert len(result) == 3
        conforms, res_graph, report = result
        assert conforms is True, report
        assert isinstance(res_graph, Graph)

    def test_social_note_exactly_one_target_constraint(self) -> None:
        """Verify SocialNote must link to exactly one FRBR tier (sh:xone constraint)."""
        g = Graph()
        g.bind("iqoqo", IQOQO)

        u = URIRef("https://iqoqo.org/users/1")
        w = URIRef("https://iqoqo.org/works/1")
        m = URIRef("https://iqoqo.org/manifestations/1")
        g.add((u, RDF.type, IQOQO.User))
        g.add((w, RDF.type, IQOQO.Work))
        g.add((m, RDF.type, IQOQO.Manifestation))

        note = URIRef("https://iqoqo.org/notes/1")
        g.add((note, RDF.type, IQOQO.SocialNote))
        g.add((note, IQOQO.noteUser, u))
        g.add((note, IQOQO.noteText, Literal("Great work!")))

        # Violates: links to both work and manifestation
        g.add((note, IQOQO.noteTargetWork, w))
        g.add((note, IQOQO.noteTargetManifestation, m))

        conforms, _, report = validate_graph(g)
        assert conforms is False
        assert "SocialNote" in report

    def test_item_custody_event_shape(self) -> None:
        """Verify ItemCustodyEvent requires item, eventType, and recordedAt."""
        g = Graph()
        g.bind("iqoqo", IQOQO)

        it = URIRef("https://iqoqo.org/items/1")
        g.add((it, RDF.type, IQOQO.Item))

        event = URIRef("https://iqoqo.org/custody/1")
        g.add((event, RDF.type, IQOQO.ItemCustodyEvent))
        g.add((event, IQOQO.custodyItem, it))
        g.add((event, IQOQO.eventType, Literal("transfer")))
        g.add((event, IQOQO.recordedAt, Literal("2026-09-17T12:00:00Z", datatype=XSD.dateTime)))

        conforms, _, report = validate_graph(g)
        assert conforms is True, report


# ===========================================================================
# 2. Sync Script Tests
# ===========================================================================


class TestSyncOntologyScript:
    """Test suite verifying scripts/sync_ontology.py parity and CLI checks."""

    def test_validate_turtle_syntax_valid(self) -> None:
        """Verify valid TTL file passes syntax validation."""
        ont_path = ROOT_DIR / "docs" / "ontology" / "iqoqo.ttl"
        valid, err = validate_turtle_syntax(ont_path)
        assert valid is True
        assert err is None

    def test_validate_turtle_syntax_missing_file(self, tmp_path: Path) -> None:
        """Verify non-existent file fails syntax validation."""
        missing = tmp_path / "does_not_exist.ttl"
        valid, err = validate_turtle_syntax(missing)
        assert valid is False
        assert "File not found" in str(err)

    def test_validate_turtle_syntax_corrupt(self, tmp_path: Path) -> None:
        """Verify malformed Turtle fails syntax validation."""
        corrupt = tmp_path / "corrupt.ttl"
        corrupt.write_text("THIS IS NOT TURTLE RDF {{{::;", encoding="utf-8")
        valid, err = validate_turtle_syntax(corrupt)
        assert valid is False
        assert err is not None

    def test_all_post_0718_models_mapped(self) -> None:
        """Verify all post-v0.7.18 domain models are included in MODEL_CLASS_MAP."""
        post_0718 = [
            "UserWorkIntent",
            "ItemCustodyEvent",
            "LoanRequest",
            "ReadingRoadmap",
            "RoadmapItem",
            "Tag",
            "ItemTag",
            "SocialNote",
            "EscalationRequest",
            "EntityAuditLog",
        ]
        for model_name in post_0718:
            assert model_name in MODEL_CLASS_MAP, f"{model_name} missing from MODEL_CLASS_MAP"

    def test_canonical_ontology_in_sync_with_db(self) -> None:
        """Verify that current DB models and docs/ontology/iqoqo.ttl are in sync."""
        report = check_drift()
        assert report["syntax_valid"] is True, f"Syntax errors: {report.get('syntax_errors')}"
        assert report["missing_in_ontology"] == [], f"Missing classes in ontology: {report['missing_in_ontology']}"
        assert report["in_sync"] is True

    def test_explicit_contract_manifest_is_curated(self) -> None:
        """Property and shape expectations are explicit, finite manifests."""
        assert "intentWork" in MAPPED_PROPERTY_CONTRACT
        assert "roadmapPosition" in MAPPED_PROPERTY_CONTRACT
        assert "UserWorkIntentShape" in REQUIRED_SHAPE_CONTRACT
        assert "ImageScanShape" not in REQUIRED_SHAPE_CONTRACT

    def test_check_drift_detects_missing_mapped_property(self, tmp_path: Path) -> None:
        """Missing mapped predicates report a stable diagnostic key."""
        ontology = (ROOT_DIR / "docs" / "ontology" / "iqoqo.ttl").read_text(encoding="utf-8")
        declaration = """:intentWork a owl:ObjectProperty ;
    rdfs:label "intent work" ;
    rdfs:comment "The Work targeted by the user work intent." ;
    rdfs:domain :UserWorkIntent ;
    rdfs:range :Work .
"""
        drift_path = tmp_path / "missing-property.ttl"
        drift_path.write_text(ontology.replace(declaration, ""), encoding="utf-8")

        report = check_drift(ontology_path=drift_path)
        assert "intentWork" in report["missing_properties"]
        assert any(item["key"] == "missing_properties" for item in report["diagnostics"])
        assert report["in_sync"] is False

    def test_check_drift_detects_changed_property_domain(self, tmp_path: Path) -> None:
        """Changed domains are compared to the exact declared contract."""
        ontology = (ROOT_DIR / "docs" / "ontology" / "iqoqo.ttl").read_text(encoding="utf-8")
        original = """:intentWork a owl:ObjectProperty ;
    rdfs:label "intent work" ;
    rdfs:comment "The Work targeted by the user work intent." ;
    rdfs:domain :UserWorkIntent ;
    rdfs:range :Work .
"""
        changed = original.replace("rdfs:domain :UserWorkIntent", "rdfs:domain :LoanRequest")
        drift_path = tmp_path / "changed-domain.ttl"
        drift_path.write_text(ontology.replace(original, changed), encoding="utf-8")

        report = check_drift(ontology_path=drift_path)
        assert report["changed_property_domains"][0]["property"] == "intentWork"
        assert any(item["key"] == "changed_property_domains" for item in report["diagnostics"])
        assert report["in_sync"] is False

    @pytest.mark.parametrize(
        ("replacement", "diagnostic_key"),
        [
            ("rdfs:domain :UserWorkIntent ;", "missing_property_domains"),
            ("rdfs:range :Work .", "missing_property_ranges"),
            ("a owl:ObjectProperty", "changed_property_types"),
        ],
    )
    def test_check_drift_detects_missing_domain_range_and_changed_property_type(
        self, tmp_path: Path, replacement: str, diagnostic_key: str
    ) -> None:
        """Missing endpoints and a changed OWL property kind are reported."""
        ontology = (ROOT_DIR / "docs" / "ontology" / "iqoqo.ttl").read_text(encoding="utf-8")
        start = ontology.index(":intentWork a owl:ObjectProperty ;")
        end = ontology.index("\n\n", start)
        declaration = ontology[start:end]
        if diagnostic_key == "missing_property_domains":
            changed = declaration.replace(replacement, 'rdfs:label "intent work" ;')
        elif diagnostic_key == "missing_property_ranges":
            changed = declaration.replace(replacement, 'rdfs:label "intent work" .')
        else:
            changed = declaration.replace(replacement, "a owl:DatatypeProperty", 1)
        drift_path = tmp_path / f"{diagnostic_key}.ttl"
        drift_path.write_text(ontology.replace(declaration, changed), encoding="utf-8")

        report = check_drift(ontology_path=drift_path)
        assert any(item["key"] == diagnostic_key for item in report["diagnostics"])
        assert report["in_sync"] is False

    def test_check_drift_detects_changed_property_range(self, tmp_path: Path) -> None:
        """Changed ranges are compared to the exact declared contract."""
        ontology = (ROOT_DIR / "docs" / "ontology" / "iqoqo.ttl").read_text(encoding="utf-8")
        original = """:intentWork a owl:ObjectProperty ;
    rdfs:label "intent work" ;
    rdfs:comment "The Work targeted by the user work intent." ;
    rdfs:domain :UserWorkIntent ;
    rdfs:range :Work .
"""
        changed = original.replace("rdfs:range :Work", "rdfs:range :Item")
        drift_path = tmp_path / "changed-range.ttl"
        drift_path.write_text(ontology.replace(original, changed), encoding="utf-8")

        report = check_drift(ontology_path=drift_path)
        assert report["changed_property_ranges"][0]["property"] == "intentWork"
        assert any(item["key"] == "changed_property_ranges" for item in report["diagnostics"])
        assert report["in_sync"] is False

    def test_check_drift_detects_missing_required_shape(self, tmp_path: Path) -> None:
        """A required NodeShape cannot be replaced by an unmanifested name."""
        shapes = (ROOT_DIR / "docs" / "ontology" / "iqoqo-shapes.ttl").read_text(encoding="utf-8")
        drift_path = tmp_path / "missing-shape.ttl"
        drift_path.write_text(
            shapes.replace("iqoqo:UserWorkIntentShape a sh:NodeShape", "iqoqo:LegacyIntentShape a sh:NodeShape"), encoding="utf-8"
        )

        report = check_drift(shapes_path=drift_path)
        assert "UserWorkIntentShape" in report["missing_shapes"]
        assert any(item["key"] == "missing_shapes" for item in report["diagnostics"])
        assert report["in_sync"] is False

    def test_check_drift_detects_changed_shape_target(self, tmp_path: Path) -> None:
        """Required shapes must target the exact expected entity class."""
        shapes = (ROOT_DIR / "docs" / "ontology" / "iqoqo-shapes.ttl").read_text(encoding="utf-8")
        original = """iqoqo:UserWorkIntentShape a sh:NodeShape ;
    sh:targetClass iqoqo:UserWorkIntent ;"""
        changed = original.replace("sh:targetClass iqoqo:UserWorkIntent", "sh:targetClass iqoqo:LoanRequest")
        drift_path = tmp_path / "changed-shape-target.ttl"
        drift_path.write_text(shapes.replace(original, changed), encoding="utf-8")

        report = check_drift(shapes_path=drift_path)
        assert report["changed_shape_targets"][0]["shape"] == "UserWorkIntentShape"
        assert any(item["key"] == "changed_shape_targets" for item in report["diagnostics"])
        assert report["in_sync"] is False

    def test_check_drift_detects_missing_class(self, tmp_path: Path) -> None:
        """Verify check_drift identifies missing classes and reports in_sync=False."""
        ont_path = ROOT_DIR / "docs" / "ontology" / "iqoqo.ttl"
        content = ont_path.read_text(encoding="utf-8")
        # Rename UserWorkIntent class to OldUserWorkIntent to simulate a missing DB model in ontology
        pruned_content = content.replace(":UserWorkIntent a owl:Class ;", ":OldUserWorkIntent a owl:Class ;")
        pruned_ont = tmp_path / "pruned_ontology.ttl"
        pruned_ont.write_text(pruned_content, encoding="utf-8")

        report = check_drift(ontology_path=pruned_ont)
        assert report["syntax_valid"] is True
        assert "UserWorkIntent" in report["missing_in_ontology"]
        assert report["in_sync"] is False

    def test_cli_check_success(self) -> None:
        """Verify main(['--check']) exits with 0 on synchronized ontology."""
        exit_code = sync_ontology.main(["--check"])
        assert exit_code == 0

    def test_cli_check_failure_on_corrupt_file(self, tmp_path: Path) -> None:
        """Verify main(['--check']) exits with 1 on invalid Turtle file."""
        corrupt = tmp_path / "corrupt.ttl"
        corrupt.write_text("INVALID RDF SYNTAX", encoding="utf-8")
        exit_code = sync_ontology.main(["--check", "--ontology-path", str(corrupt)])
        assert exit_code == 1

    def test_make_sync_ontology_enforces_check_mode_on_drift(self, tmp_path: Path) -> None:
        """The Make target adds strict mode even when callers only pass paths."""
        ontology = (ROOT_DIR / "docs" / "ontology" / "iqoqo.ttl").read_text(encoding="utf-8")
        drift_path = tmp_path / "make-drift.ttl"
        drift_path.write_text(ontology.replace("rdfs:range :Work .", "rdfs:range :Item .", 1), encoding="utf-8")
        result = subprocess.run(
            ["make", "sync-ontology", f"ARGS=--ontology-path={drift_path}", f"PYTHON_BIN={sys.executable}"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode != 0, result.stdout + result.stderr
        assert "changed_property_ranges" in result.stderr
