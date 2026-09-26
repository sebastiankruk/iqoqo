#!/usr/bin/env python3
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
"""
Ontology Sync Script.

Introspects SQLAlchemy models and compares them against explicit OWL property
and SHACL shape contracts in docs/ontology/iqoqo.ttl and
docs/ontology/iqoqo-shapes.ttl. The manifest is intentionally curated: it
tracks semantic properties used by mapped entities rather than attempting to
infer an RDF contract for every SQL column.

Usage:
    python scripts/sync_ontology.py [--check] [--ontology-path PATH] [--shapes-path PATH]

Options:
    --check            Only report drift and syntax; exit 1 if syntax invalid or drift detected.
    --ontology-path    Path to the OWL ontology Turtle file (default: docs/ontology/iqoqo.ttl).
    --shapes-path      Path to the SHACL shapes Turtle file (default: docs/ontology/iqoqo-shapes.ttl).
"""

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "docs" / "ontology" / "iqoqo.ttl"
SHAPES_PATH = Path(__file__).resolve().parent.parent / "docs" / "ontology" / "iqoqo-shapes.ttl"
IQOQO = Namespace("https://iqoqo.org/ontology#")
SH = Namespace("http://www.w3.org/ns/shacl#")
FRBR = Namespace("http://purl.org/vocab/frbr/core#")

# Mapping of SQLAlchemy model class names to ontology class local names
MODEL_CLASS_MAP: dict[str, str] = {
    # FRBR Core
    "Work": "Work",
    "Expression": "Expression",
    "Manifestation": "Manifestation",
    "Item": "Item",
    # Contributions & Events
    "Contributor": "Contributor",
    "WorkContribution": "WorkContribution",
    "ExpressionContribution": "ExpressionContribution",
    "ManifestationContribution": "ManifestationContribution",
    "WorkPart": "WorkPart",
    # Complex works & Expansions
    "ContainerAggregation": "ContainerAggregation",
    "WorkExpansionLink": "WorkExpansionLink",
    # Post-v0.7.18 domain models
    "UserWorkIntent": "UserWorkIntent",
    "ItemCustodyEvent": "ItemCustodyEvent",
    "LoanRequest": "LoanRequest",
    "ReadingRoadmap": "ReadingRoadmap",
    "RoadmapItem": "RoadmapItem",
    "Tag": "Tag",
    "ItemTag": "ItemTag",
    "SocialNote": "SocialNote",
    "EscalationRequest": "EscalationRequest",
    "EntityAuditLog": "EntityAuditLog",
    # System / Social / Catalog additions
    "ImageScan": "ImageScan",
    "UserCollection": "UserCollection",
    "BoardgameMechanic": "BoardgameMechanic",
    "FeedbackItem": "FeedbackItem",
    "FeedbackComment": "FeedbackComment",
    "User": "User",
}

# Curated semantic contract for properties used by mapped entities. Each entry
# declares the expected OWL property kind, exact rdfs:domain, and exact
# rdfs:range. This is deliberately not generated from SQLAlchemy columns.
MAPPED_PROPERTY_CONTRACT: dict[str, tuple[URIRef, URIRef, URIRef]] = {
    "is_expansion_of": (OWL.ObjectProperty, IQOQO.Work, IQOQO.Work),
    "baseWork": (OWL.ObjectProperty, IQOQO.WorkExpansionLink, IQOQO.Work),
    "expansionWork": (OWL.ObjectProperty, IQOQO.WorkExpansionLink, IQOQO.Work),
    "link_type": (OWL.DatatypeProperty, IQOQO.WorkExpansionLink, XSD.string),
    "containerWork": (OWL.ObjectProperty, IQOQO.ContainerAggregation, IQOQO.Work),
    "aggregatedWork": (OWL.ObjectProperty, IQOQO.ContainerAggregation, IQOQO.Work),
    "aggregatedItem": (OWL.ObjectProperty, IQOQO.ContainerAggregation, IQOQO.Item),
    "status": (OWL.DatatypeProperty, IQOQO.Item, XSD.string),
    "collection_status": (OWL.DatatypeProperty, IQOQO.Item, XSD.string),
    "condition": (OWL.DatatypeProperty, IQOQO.Item, XSD.string),
    "has_mechanic": (OWL.ObjectProperty, IQOQO.Work, IQOQO.BoardgameMechanic),
    "intentWork": (OWL.ObjectProperty, IQOQO.UserWorkIntent, IQOQO.Work),
    "intentUser": (OWL.ObjectProperty, IQOQO.UserWorkIntent, IQOQO.User),
    "intentStatus": (OWL.DatatypeProperty, IQOQO.UserWorkIntent, XSD.string),
    "custodyItem": (OWL.ObjectProperty, IQOQO.ItemCustodyEvent, IQOQO.Item),
    "custodyActor": (OWL.ObjectProperty, IQOQO.ItemCustodyEvent, IQOQO.User),
    "eventType": (OWL.DatatypeProperty, IQOQO.ItemCustodyEvent, XSD.string),
    "eventNotes": (OWL.DatatypeProperty, IQOQO.ItemCustodyEvent, XSD.string),
    "recordedAt": (OWL.DatatypeProperty, IQOQO.ItemCustodyEvent, XSD.dateTime),
    "loanItem": (OWL.ObjectProperty, IQOQO.LoanRequest, IQOQO.Item),
    "loanRequester": (OWL.ObjectProperty, IQOQO.LoanRequest, IQOQO.User),
    "loanStatus": (OWL.DatatypeProperty, IQOQO.LoanRequest, XSD.string),
    "loanNotes": (OWL.DatatypeProperty, IQOQO.LoanRequest, XSD.string),
    "roadmapUser": (OWL.ObjectProperty, IQOQO.ReadingRoadmap, IQOQO.User),
    "roadmapTitle": (OWL.DatatypeProperty, IQOQO.ReadingRoadmap, XSD.string),
    "roadmapDescription": (OWL.DatatypeProperty, IQOQO.ReadingRoadmap, XSD.string),
    "is_public": (OWL.DatatypeProperty, IQOQO.ReadingRoadmap, XSD.boolean),
    "inRoadmap": (OWL.ObjectProperty, IQOQO.RoadmapItem, IQOQO.ReadingRoadmap),
    "roadmapWork": (OWL.ObjectProperty, IQOQO.RoadmapItem, IQOQO.Work),
    "roadmapManifestation": (OWL.ObjectProperty, IQOQO.RoadmapItem, IQOQO.Manifestation),
    "roadmapPosition": (OWL.DatatypeProperty, IQOQO.RoadmapItem, XSD.integer),
    "roadmapItemStatus": (OWL.DatatypeProperty, IQOQO.RoadmapItem, XSD.string),
    "tagName": (OWL.DatatypeProperty, IQOQO.Tag, XSD.string),
    "taggedItem": (OWL.ObjectProperty, IQOQO.ItemTag, IQOQO.Item),
    "hasTag": (OWL.ObjectProperty, IQOQO.ItemTag, IQOQO.Tag),
    "tagAddedBy": (OWL.ObjectProperty, IQOQO.ItemTag, IQOQO.User),
    "noteUser": (OWL.ObjectProperty, IQOQO.SocialNote, IQOQO.User),
    "noteTargetWork": (OWL.ObjectProperty, IQOQO.SocialNote, IQOQO.Work),
    "noteTargetExpression": (OWL.ObjectProperty, IQOQO.SocialNote, IQOQO.Expression),
    "noteTargetManifestation": (OWL.ObjectProperty, IQOQO.SocialNote, IQOQO.Manifestation),
    "noteTargetItem": (OWL.ObjectProperty, IQOQO.SocialNote, IQOQO.Item),
    "noteText": (OWL.DatatypeProperty, IQOQO.SocialNote, XSD.string),
    "escalationUser": (OWL.ObjectProperty, IQOQO.EscalationRequest, IQOQO.User),
    "escalationResolver": (OWL.ObjectProperty, IQOQO.EscalationRequest, IQOQO.User),
    "escalationWork": (OWL.ObjectProperty, IQOQO.EscalationRequest, IQOQO.Work),
    "escalationExpression": (OWL.ObjectProperty, IQOQO.EscalationRequest, IQOQO.Expression),
    "escalationManifestation": (OWL.ObjectProperty, IQOQO.EscalationRequest, IQOQO.Manifestation),
    "escalationItem": (OWL.ObjectProperty, IQOQO.EscalationRequest, IQOQO.Item),
    "escalationStatus": (OWL.DatatypeProperty, IQOQO.EscalationRequest, XSD.string),
    "fieldName": (OWL.DatatypeProperty, IQOQO.EscalationRequest, XSD.string),
    "suggestedValue": (OWL.DatatypeProperty, IQOQO.EscalationRequest, XSD.string),
    "auditActor": (OWL.ObjectProperty, IQOQO.EntityAuditLog, IQOQO.User),
    "auditEntityType": (OWL.DatatypeProperty, IQOQO.EntityAuditLog, XSD.string),
    "auditEntityId": (OWL.DatatypeProperty, IQOQO.EntityAuditLog, XSD.integer),
    "auditChangeType": (OWL.DatatypeProperty, IQOQO.EntityAuditLog, XSD.string),
    "auditLoggedAt": (OWL.DatatypeProperty, IQOQO.EntityAuditLog, XSD.dateTime),
}

# Required shape identifier -> exact target class. This is selective: a shape
# requirement is only asserted where the vocabulary has a declared contract.
REQUIRED_SHAPE_CONTRACT: dict[str, URIRef] = {
    "WorkShape": FRBR.Work,
    "WorkExpansionLinkShape": IQOQO.WorkExpansionLink,
    "ContainerAggregationShape": IQOQO.ContainerAggregation,
    "BoardgameMechanicShape": IQOQO.BoardgameMechanic,
    "FeedbackItemShape": IQOQO.FeedbackItem,
    "FeedbackCommentShape": IQOQO.FeedbackComment,
    "FRBRExpressionShape": FRBR.Expression,
    "FRBRManifestationShape": FRBR.Manifestation,
    "FRBRItemShape": FRBR.Item,
    "FRBRWorkShape": FRBR.Work,
    "UserWorkIntentShape": IQOQO.UserWorkIntent,
    "ItemCustodyEventShape": IQOQO.ItemCustodyEvent,
    "LoanRequestShape": IQOQO.LoanRequest,
    "ReadingRoadmapShape": IQOQO.ReadingRoadmap,
    "RoadmapItemShape": IQOQO.RoadmapItem,
    "TagShape": IQOQO.Tag,
    "ItemTagShape": IQOQO.ItemTag,
    "SocialNoteShape": IQOQO.SocialNote,
    "EscalationRequestShape": IQOQO.EscalationRequest,
    "EntityAuditLogShape": IQOQO.EntityAuditLog,
}


def _parse_turtle(path: Path) -> tuple[Graph | None, str | None]:
    """Parse Turtle once, returning a useful error instead of raising."""
    if not path.exists():
        return None, f"File not found: {path}"
    g = Graph()
    try:
        g.parse(str(path), format="turtle")
        return g, None
    except Exception as e:  # pylint: disable=broad-exception-caught
        return None, str(e)


def validate_turtle_syntax(path: Path) -> tuple[bool, str | None]:
    """Validate that a Turtle file parses without syntax errors."""
    graph, error = _parse_turtle(path)
    return graph is not None, error


def get_db_model_classes() -> set[str]:
    """Get the set of FRBR-related model class names from SQLAlchemy."""
    from app import create_app
    from app.db.models import db

    app = create_app()
    with app.app_context():
        model_names: set[str] = set()
        registry = getattr(db.Model, "registry", None)
        if registry is not None:
            for mapper in registry.mappers:
                cls = mapper.class_
                name = cls.__name__
                if name in MODEL_CLASS_MAP:
                    model_names.add(name)
        return model_names


def get_ontology_classes(ontology_path: Path = ONTOLOGY_PATH) -> set[str]:
    """Get the set of class local names defined in iqoqo.ttl."""
    graph, error = _parse_turtle(ontology_path)
    if graph is None:
        raise ValueError(f"Could not parse ontology {ontology_path}: {error}")

    classes: set[str] = set()
    for s in graph.subjects(RDF.type, OWL.Class):
        if isinstance(s, URIRef) and str(s).startswith(str(IQOQO)):
            local_name = str(s).replace(str(IQOQO), "")
            classes.add(local_name)
    return classes


def check_drift(
    ontology_path: Path = ONTOLOGY_PATH,
    shapes_path: Path = SHAPES_PATH,
) -> dict[str, Any]:
    """Compare mapped DB classes and the explicit OWL/SHACL contract."""
    syntax_errors: list[str] = []
    ontology_graph, ont_err = _parse_turtle(ontology_path)
    shapes_graph, shapes_err = _parse_turtle(shapes_path)
    if ontology_graph is None:
        syntax_errors.append(f"Ontology syntax error ({ontology_path}): {ont_err}")
    if shapes_graph is None:
        syntax_errors.append(f"Shapes syntax error ({shapes_path}): {shapes_err}")

    if ontology_graph is None or shapes_graph is None:
        return {
            "syntax_valid": False,
            "syntax_errors": syntax_errors,
            "db_models": [],
            "ontology_classes": [],
            "missing_in_ontology": [],
            "extra_in_ontology": [],
            "missing_properties": [],
            "changed_property_types": [],
            "missing_property_domains": [],
            "changed_property_domains": [],
            "missing_property_ranges": [],
            "changed_property_ranges": [],
            "missing_shapes": [],
            "changed_shape_targets": [],
            "diagnostics": [{"key": "syntax_errors", "message": error} for error in syntax_errors],
            "in_sync": False,
        }

    db_models = get_db_model_classes()
    ontology_classes = {
        str(subject).replace(str(IQOQO), "")
        for subject in ontology_graph.subjects(RDF.type, OWL.Class)
        if isinstance(subject, URIRef) and str(subject).startswith(str(IQOQO))
    }

    # Map DB models to expected ontology names
    expected_in_ontology = {MODEL_CLASS_MAP[m] for m in db_models if m in MODEL_CLASS_MAP}

    missing_in_ontology = expected_in_ontology - ontology_classes
    extra_in_ontology = ontology_classes - expected_in_ontology

    missing_properties: list[str] = []
    changed_property_types: list[dict[str, str]] = []
    missing_property_domains: list[str] = []
    changed_property_domains: list[dict[str, Any]] = []
    missing_property_ranges: list[str] = []
    changed_property_ranges: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []

    for local_name, (expected_type, expected_domain, expected_range) in MAPPED_PROPERTY_CONTRACT.items():
        prop = IQOQO[local_name]
        if (prop, None, None) not in ontology_graph:
            missing_properties.append(local_name)
            diagnostics.append({"key": "missing_properties", "message": f"Missing mapped property iqoqo:{local_name}."})
            continue

        property_types = set(ontology_graph.objects(prop, RDF.type)) & {OWL.ObjectProperty, OWL.DatatypeProperty}
        if property_types != {expected_type}:
            actual = ", ".join(sorted(_term_name(value) for value in property_types)) or "none"
            changed_property_types.append({"property": local_name, "expected": _term_name(expected_type), "actual": actual})
            diagnostics.append(
                {"key": "changed_property_types", "message": f"iqoqo:{local_name} must be {_term_name(expected_type)} (found {actual})."}
            )

        _check_exact_term_contract(
            graph=ontology_graph,
            subject=prop,
            predicate=RDFS.domain,
            expected=expected_domain,
            local_name=local_name,
            label="domain",
            missing=missing_property_domains,
            changed=changed_property_domains,
            diagnostics=diagnostics,
        )
        _check_exact_term_contract(
            graph=ontology_graph,
            subject=prop,
            predicate=RDFS.range,
            expected=expected_range,
            local_name=local_name,
            label="range",
            missing=missing_property_ranges,
            changed=changed_property_ranges,
            diagnostics=diagnostics,
        )

    missing_shapes: list[str] = []
    changed_shape_targets: list[dict[str, Any]] = []
    for local_name, expected_target in REQUIRED_SHAPE_CONTRACT.items():
        shape = IQOQO[local_name]
        if (shape, RDF.type, SH.NodeShape) not in shapes_graph:
            missing_shapes.append(local_name)
            diagnostics.append({"key": "missing_shapes", "message": f"Missing required SHACL NodeShape iqoqo:{local_name}."})
            continue
        actual_targets = set(shapes_graph.objects(shape, SH.targetClass))
        if actual_targets != {expected_target}:
            changed_shape_targets.append(
                {
                    "shape": local_name,
                    "expected": _term_name(expected_target),
                    "actual": sorted(_term_name(target) for target in actual_targets),
                }
            )
            diagnostics.append(
                {
                    "key": "changed_shape_targets",
                    "message": f"iqoqo:{local_name} must target {_term_name(expected_target)} (found {_format_terms(actual_targets)}).",
                }
            )

    for class_name in sorted(missing_in_ontology):
        diagnostics.append({"key": "missing_in_ontology", "message": f"Missing mapped ontology class iqoqo:{class_name}."})

    in_sync = not (
        syntax_errors
        or missing_in_ontology
        or missing_properties
        or changed_property_types
        or missing_property_domains
        or changed_property_domains
        or missing_property_ranges
        or changed_property_ranges
        or missing_shapes
        or changed_shape_targets
    )

    return {
        "syntax_valid": True,
        "syntax_errors": syntax_errors,
        "db_models": sorted(db_models),
        "ontology_classes": sorted(ontology_classes),
        "missing_in_ontology": sorted(missing_in_ontology),
        "extra_in_ontology": sorted(extra_in_ontology),
        "missing_properties": missing_properties,
        "changed_property_types": changed_property_types,
        "missing_property_domains": missing_property_domains,
        "changed_property_domains": changed_property_domains,
        "missing_property_ranges": missing_property_ranges,
        "changed_property_ranges": changed_property_ranges,
        "missing_shapes": missing_shapes,
        "changed_shape_targets": changed_shape_targets,
        "diagnostics": diagnostics,
        "in_sync": in_sync,
    }


def _term_name(term: URIRef) -> str:
    """Format an RDF term as a readable, stable name for diagnostics."""
    value = str(term)
    for namespace, prefix in ((str(IQOQO), "iqoqo:"), (str(XSD), "xsd:"), (str(FRBR), "frbr:"), (str(OWL), "owl:")):
        if value.startswith(namespace):
            return prefix + value[len(namespace) :]
    return value


def _format_terms(terms: set[URIRef]) -> str:
    return ", ".join(sorted(_term_name(term) for term in terms)) or "none"


def _check_exact_term_contract(
    *,
    graph: Graph,
    subject: URIRef,
    predicate: URIRef,
    expected: URIRef,
    local_name: str,
    label: str,
    missing: list[str],
    changed: list[dict[str, Any]],
    diagnostics: list[dict[str, str]],
) -> None:
    actual = set(graph.objects(subject, predicate))
    if not actual:
        key = f"missing_property_{label}s"
        missing.append(local_name)
        diagnostics.append({"key": key, "message": f"iqoqo:{local_name} is missing its rdfs:{label} (expected {_term_name(expected)})."})
    elif actual != {expected}:
        key = f"changed_property_{label}s"
        changed.append({"property": local_name, "expected": _term_name(expected), "actual": sorted(_term_name(term) for term in actual)})
        diagnostics.append(
            {
                "key": key,
                "message": f"iqoqo:{local_name} must have exact rdfs:{label} {_term_name(expected)} (found {_format_terms(actual)}).",
            }
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize and validate iqoqo OWL ontology & SHACL shapes.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only report drift and validate syntax. Exit 1 if drift or syntax errors are detected.",
    )
    parser.add_argument(
        "--ontology-path",
        type=Path,
        default=ONTOLOGY_PATH,
        help="Path to ontology Turtle file (default: docs/ontology/iqoqo.ttl).",
    )
    parser.add_argument(
        "--shapes-path",
        type=Path,
        default=SHAPES_PATH,
        help="Path to SHACL shapes Turtle file (default: docs/ontology/iqoqo-shapes.ttl).",
    )

    args = parser.parse_args(argv)

    report = check_drift(ontology_path=args.ontology_path, shapes_path=args.shapes_path)

    print("=" * 60)
    print("ONTOLOGY SYNC REPORT")
    print("=" * 60)
    print()

    if not report["syntax_valid"]:
        for err in report["syntax_errors"]:
            print(f"ERROR [syntax_errors]: {err}", file=sys.stderr)
        print()
    else:
        for diagnostic in report["diagnostics"]:
            print(f"ERROR [{diagnostic['key']}]: {diagnostic['message']}", file=sys.stderr)

    print(f"DB Models (FRBR-related):   {len(report['db_models'])}")
    print(f"Ontology Classes:           {len(report['ontology_classes'])}")
    print(f"Mapped Properties:          {len(MAPPED_PROPERTY_CONTRACT)}")
    print(f"Required SHACL Shapes:       {len(REQUIRED_SHAPE_CONTRACT)}")
    print()

    if report["extra_in_ontology"]:
        print("EXTRA in ontology (not mapped to a DB model):")
        for name in report["extra_in_ontology"]:
            print(f"  - {name}")
        print()

    if report["in_sync"]:
        print("✓ Ontology and SHACL shapes are valid and in sync with DB models.")
        return 0

    print("✗ Drift or syntax errors detected between DB models and ontology.", file=sys.stderr)
    if args.check:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
