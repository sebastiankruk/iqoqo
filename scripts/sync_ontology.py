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
to detect drift between the DB schema and the OWL ontology.

Usage:
    python scripts/sync_ontology.py [--check]

Options:
    --check   Only report drift, do not modify files. Exit 1 if drift detected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "docs" / "ontology" / "iqoqo.ttl"
IQOQO = Namespace("https://iqoqo.org/ontology#")

# Mapping of SQLAlchemy model class names to ontology class local names
MODEL_CLASS_MAP = {
    "Work": "Work",
    "Expression": "Expression",
    "Manifestation": "Manifestation",
    "Item": "Item",
    "Contributor": "Contributor",
    "WorkContribution": "WorkContribution",
    "ExpressionContribution": "ExpressionContribution",
    "ManifestationContribution": "ManifestationContribution",
    "ImageScan": "ImageScan",
    "UserCollection": "UserCollection",
}


def get_db_model_classes() -> set[str]:
    """Get the set of FRBR-related model class names from SQLAlchemy."""
    from app import create_app
    from app.db.models import db

    app = create_app()
    with app.app_context():
        model_names = set()
        for mapper in db.Model.registry.mappers:
            cls = mapper.class_
            name = cls.__name__
            if name in MODEL_CLASS_MAP:
                model_names.add(name)
        return model_names


def get_ontology_classes() -> set[str]:
    """Get the set of class local names defined in iqoqo.ttl."""
    g = Graph()
    g.parse(str(ONTOLOGY_PATH), format="turtle")

    classes = set()
    for s in g.subjects(RDF.type, OWL.Class):
        if isinstance(s, URIRef) and str(s).startswith(str(IQOQO)):
            local_name = str(s).replace(str(IQOQO), "")
            classes.add(local_name)
    return classes


def check_drift() -> dict:
    """Compare DB models against ontology and report drift."""
    db_models = get_db_model_classes()
    ontology_classes = get_ontology_classes()

    # Map DB models to expected ontology names
    expected_in_ontology = {MODEL_CLASS_MAP[m] for m in db_models if m in MODEL_CLASS_MAP}

    missing_in_ontology = expected_in_ontology - ontology_classes
    extra_in_ontology = ontology_classes - expected_in_ontology

    return {
        "db_models": sorted(db_models),
        "ontology_classes": sorted(ontology_classes),
        "missing_in_ontology": sorted(missing_in_ontology),
        "extra_in_ontology": sorted(extra_in_ontology),
        "in_sync": len(missing_in_ontology) == 0,
    }


def main():
    check_only = "--check" in sys.argv

    report = check_drift()

    print("=" * 60)
    print("ONTOLOGY SYNC REPORT")
    print("=" * 60)
    print()
    print(f"DB Models (FRBR-related):   {len(report['db_models'])}")
    print(f"Ontology Classes:           {len(report['ontology_classes'])}")
    print()

    if report["missing_in_ontology"]:
        print("MISSING in ontology (present in DB but not in iqoqo.ttl):")
        for name in report["missing_in_ontology"]:
            print(f"  - {name}")
        print()

    if report["extra_in_ontology"]:
        print("EXTRA in ontology (not mapped to a DB model):")
        for name in report["extra_in_ontology"]:
            print(f"  - {name}")
        print()

    if report["in_sync"]:
        print("✓ Ontology is in sync with DB models.")
    else:
        print("✗ Drift detected between DB models and ontology.")
        if check_only:
            sys.exit(1)


if __name__ == "__main__":
    main()
