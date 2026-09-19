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

Introspects SQLAlchemy models and compares them against docs/ontology/iqoqo.ttl
and docs/ontology/iqoqo-shapes.ttl to detect drift between the DB schema and the
OWL ontology and validate Turtle syntax.

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
from rdflib.namespace import OWL, RDF

ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "docs" / "ontology" / "iqoqo.ttl"
SHAPES_PATH = Path(__file__).resolve().parent.parent / "docs" / "ontology" / "iqoqo-shapes.ttl"
IQOQO = Namespace("https://iqoqo.org/ontology#")

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


def validate_turtle_syntax(path: Path) -> tuple[bool, str | None]:
    """Validate that a Turtle file parses without syntax errors."""
    if not path.exists():
        return False, f"File not found: {path}"
    g = Graph()
    try:
        g.parse(str(path), format="turtle")
        return True, None
    except Exception as e:  # pylint: disable=broad-exception-caught
        return False, str(e)


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
    g = Graph()
    g.parse(str(ontology_path), format="turtle")

    classes: set[str] = set()
    for s in g.subjects(RDF.type, OWL.Class):
        if isinstance(s, URIRef) and str(s).startswith(str(IQOQO)):
            local_name = str(s).replace(str(IQOQO), "")
            classes.add(local_name)
    return classes


def check_drift(
    ontology_path: Path = ONTOLOGY_PATH,
    shapes_path: Path = SHAPES_PATH,
) -> dict[str, Any]:
    """Compare DB models against ontology and validate Turtle syntax."""
    syntax_errors: list[str] = []

    ont_valid, ont_err = validate_turtle_syntax(ontology_path)
    if not ont_valid:
        syntax_errors.append(f"Ontology syntax error ({ontology_path}): {ont_err}")

    shapes_valid, shapes_err = validate_turtle_syntax(shapes_path)
    if not shapes_valid:
        syntax_errors.append(f"Shapes syntax error ({shapes_path}): {shapes_err}")

    if not ont_valid:
        return {
            "syntax_valid": False,
            "syntax_errors": syntax_errors,
            "db_models": [],
            "ontology_classes": [],
            "missing_in_ontology": [],
            "extra_in_ontology": [],
            "in_sync": False,
        }

    db_models = get_db_model_classes()
    ontology_classes = get_ontology_classes(ontology_path)

    # Map DB models to expected ontology names
    expected_in_ontology = {MODEL_CLASS_MAP[m] for m in db_models if m in MODEL_CLASS_MAP}

    missing_in_ontology = expected_in_ontology - ontology_classes
    extra_in_ontology = ontology_classes - expected_in_ontology

    in_sync = ont_valid and shapes_valid and len(missing_in_ontology) == 0

    return {
        "syntax_valid": ont_valid and shapes_valid,
        "syntax_errors": syntax_errors,
        "db_models": sorted(db_models),
        "ontology_classes": sorted(ontology_classes),
        "missing_in_ontology": sorted(missing_in_ontology),
        "extra_in_ontology": sorted(extra_in_ontology),
        "in_sync": in_sync,
    }


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
            print(f"ERROR: {err}", file=sys.stderr)
        print()

    print(f"DB Models (FRBR-related):   {len(report['db_models'])}")
    print(f"Ontology Classes:           {len(report['ontology_classes'])}")
    print()

    if report["missing_in_ontology"]:
        print("MISSING in ontology (present in DB but not in iqoqo.ttl):", file=sys.stderr)
        for name in report["missing_in_ontology"]:
            print(f"  - {name}", file=sys.stderr)
        print(file=sys.stderr)

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
