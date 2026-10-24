"""Tests for OpenAPI 3.1 contract completeness, zero parameter drift, and schema coverage."""

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

import re

from apispec_webframeworks.flask import FlaskPlugin

from app.api.docs import assemble_complete_openapi_spec
from app.config import Config

RE_PATH_VAR = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def test_openapi_version_and_info(app):
    """Verify OpenAPI 3.1.0 standard and application metadata."""
    with app.app_context():
        spec = assemble_complete_openapi_spec()

    assert spec["openapi"].startswith("3.1"), f"Expected OpenAPI 3.1.x, got {spec.get('openapi')}"
    assert spec["info"]["title"] == "iqoqo API"
    assert spec["info"]["version"] == Config.VERSION
    assert "description" in spec["info"]
    assert spec["info"]["license"]["name"] == "AGPL-3.0"


def test_openapi_security_schemes_registered(app):
    """Verify BearerAuth (JWT) and PersonalAccessToken (PAT) security schemes are defined."""
    with app.app_context():
        spec = assemble_complete_openapi_spec()

    security_schemes = spec.get("components", {}).get("securitySchemes", {})
    assert "BearerAuth" in security_schemes
    assert security_schemes["BearerAuth"]["type"] == "http"
    assert security_schemes["BearerAuth"]["scheme"] == "bearer"
    assert security_schemes["BearerAuth"]["bearerFormat"] == "JWT"

    assert "PersonalAccessToken" in security_schemes
    assert security_schemes["PersonalAccessToken"]["type"] == "http"
    assert security_schemes["PersonalAccessToken"]["scheme"] == "bearer"
    assert security_schemes["PersonalAccessToken"]["bearerFormat"] == "PAT"

    assert "DeployToken" in security_schemes


def test_openapi_core_component_schemas_registered(app):
    """Verify all core FRBR, auth, and system envelope schemas are registered."""
    with app.app_context():
        spec = assemble_complete_openapi_spec()

    schemas = spec.get("components", {}).get("schemas", {})
    expected_schemas = [
        "Work",
        "Expression",
        "Manifestation",
        "Item",
        "User",
        "PersonalAccessToken",
        "Notification",
        "ErrorResponse",
        "SuccessEnvelope",
    ]
    for expected in expected_schemas:
        assert expected in schemas, f"Missing required OpenAPI component schema: {expected}"
        assert schemas[expected].get("type") == "object"


def test_100_percent_routes_covered_without_drift(app):
    """Verify that 100% of non-static Flask routes are indexed in the OpenAPI specification."""
    with app.app_context():
        spec = assemble_complete_openapi_spec()
        paths = spec.get("paths", {})

        uncovered_rules = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint == "static" or rule.rule.startswith("/static"):
                continue

            openapi_path = FlaskPlugin.flaskpath2openapi(rule.rule)
            if openapi_path not in paths:
                uncovered_rules.append(f"{rule.endpoint} -> {openapi_path}")

        assert not uncovered_rules, "OpenAPI specification is missing routes:\n" + "\n".join(uncovered_rules)


def test_path_parameters_fully_annotated_zero_drift(app):
    """Scenario: CI validates zero contract drift.

    WHEN a route contains path parameters (e.g. {item_id}),
    THEN the parameter must be fully annotated with name, in='path', and required=True.
    """
    with app.app_context():
        spec = assemble_complete_openapi_spec()

    paths = spec.get("paths", {})
    missing_param_annotations = []

    for path, path_item in paths.items():
        expected_params = set(RE_PATH_VAR.findall(path))
        if not expected_params:
            continue

        for method, operation in path_item.items():
            if method in ("parameters", "summary", "description"):
                continue
            if not isinstance(operation, dict):
                continue

            annotated_params = {
                p.get("name")
                for p in operation.get("parameters", [])
                if isinstance(p, dict) and p.get("in") == "path" and p.get("required") is True
            }

            missing = expected_params - annotated_params
            if missing:
                missing_param_annotations.append(f"{method.upper()} {path} missing path parameter annotation(s): {missing}")

    assert not missing_param_annotations, "Path parameter contract drift detected:\n" + "\n".join(missing_param_annotations)


def test_every_operation_has_summary_and_responses(app):
    """Verify all operations define summaries and at least one HTTP response schema."""
    with app.app_context():
        spec = assemble_complete_openapi_spec()

    paths = spec.get("paths", {})
    invalid_ops = []

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ("parameters", "summary", "description"):
                continue
            if not isinstance(operation, dict):
                continue

            if not operation.get("summary"):
                invalid_ops.append(f"{method.upper()} {path} is missing 'summary'")

            responses = operation.get("responses")
            if not responses or not isinstance(responses, dict):
                invalid_ops.append(f"{method.upper()} {path} is missing 'responses' object")

    assert not invalid_ops, "Invalid OpenAPI operations found:\n" + "\n".join(invalid_ops)


def test_openapi_json_endpoint_live(client):
    """Test live GET /api/docs/openapi.json endpoint returns valid contract."""
    response = client.get("/api/docs/openapi.json")
    assert response.status_code == 200
    assert response.is_json

    data = response.json
    assert data["openapi"] == "3.1.0"
    assert "paths" in data
    assert len(data["paths"]) >= 30, f"Expected at least 30 paths, found {len(data['paths'])}"
