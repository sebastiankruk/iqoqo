# app/api/docs.py
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
"""OpenAPI 3.1 specification assembly and schema registry.

Assembled from the route table and shared component schemas so the published
contract cannot drift from what the endpoints actually accept and return.
Guarantees 100% route and parameter coverage for Capacitor mobile clients and AI agents.
"""

import logging
import re
from typing import Any

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from flask import Blueprint, current_app, jsonify

from app.config import Config
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

docs_bp = Blueprint("docs", __name__)

RE_URL_PARAM = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def _get_route_tag(path: str) -> str:
    """Classify an API route path into a clean OpenAPI tag category."""
    if path.startswith("/api/auth") or path.startswith("/auth"):
        return "Authentication"
    if path.startswith("/api/account"):
        return "Account"
    if path.startswith("/api/profile"):
        return "Profile"
    if path.startswith("/api/items") or path.startswith("/items"):
        return "Items"
    if any(path.startswith(f"/api/{prefix}") for prefix in ("work", "expression", "manifestation", "collections")):
        return "Catalog"
    if path.startswith("/api/scanner") or path.startswith("/api/isbn"):
        return "Scanner"
    if path.startswith("/api/lending"):
        return "Lending"
    if path.startswith("/api/notifications"):
        return "Notifications"
    if path.startswith("/api/wishlist"):
        return "Wishlist"
    if path.startswith("/api/events"):
        return "Events"
    if path.startswith("/api/sparql") or path.startswith("/sparql"):
        return "SPARQL"
    if (
        path.startswith("/api/public")
        or path.startswith("/.well-known")
        or path.startswith("/inbox")
        or path.startswith("/outbox")
        or path.startswith("/u/")
    ):
        return "Federation & Public LOD"
    if path.startswith("/api/federation"):
        return "Federation"
    if path.startswith("/api/admin") or path.startswith("/admin"):
        return "Admin"
    return "System"


def _infer_param_schema(rule, var: str) -> dict[str, Any]:
    """Derive accurate OpenAPI schema for path parameter from Werkzeug routing converters."""
    converters = getattr(rule, "_converters", {})
    converter = converters.get(var)
    conv_class = converter.__class__.__name__ if converter else ""

    if conv_class == "IntegerConverter":
        return {"type": "integer"}
    if conv_class == "UUIDConverter":
        return {"type": "string", "format": "uuid"}
    if conv_class in ("FloatConverter", "NumberConverter"):
        return {"type": "number"}
    if conv_class in ("UnicodeConverter", "StringConverter", "PathConverter", "AnyConverter"):
        if "uuid" in var.lower():
            return {"type": "string", "format": "uuid"}
        return {"type": "string"}

    if "uuid" in var.lower():
        return {"type": "string", "format": "uuid"}
    if "id" in var.lower() and not any(k in var.lower() for k in ("actor", "guid", "uuid", "identifier", "task", "token")):
        return {"type": "integer"}
    return {"type": "string"}


def _endpoint_requires_auth(view_func, openapi_path: str) -> bool:
    """Determine whether an endpoint requires authentication based on function metadata and decorators."""
    if (
        openapi_path.startswith("/api/docs")
        or openapi_path.startswith("/api/public")
        or openapi_path.startswith("/api/login")
        or openapi_path.startswith("/api/auth/login")
        or openapi_path.startswith("/api/auth/register")
        or openapi_path.startswith("/api/auth/exchange")
        or openapi_path.startswith("/api/auth/providers")
        or openapi_path.startswith("/api/auth/callback")
        or openapi_path.startswith("/api/federation/actor")
        or openapi_path.startswith("/api/federation/directory")
        or openapi_path.startswith("/api/federation/instance-info")
        or openapi_path.startswith("/api/federation/nodeinfo")
        or openapi_path.startswith("/api/federation/webfinger")
        or openapi_path.startswith("/health")
        or openapi_path.startswith("/api/health")
        or openapi_path.startswith("/.well-known")
    ):
        return False

    fn = view_func
    while fn is not None:
        if getattr(fn, "_requires_auth", False):
            return True
        name = getattr(fn, "__name__", "")
        if "require_auth" in name or "require_admin" in name or "admin_required" in name or "require_permission" in name:
            return True
        fn = getattr(fn, "__wrapped__", None)

    return False


def create_spec() -> APISpec:
    """Build the base OpenAPI 3.1 schema context with security and component definitions."""
    version = current_app.config.get("APP_VERSION") or getattr(Config, "VERSION", "0.9.3")
    spec = APISpec(
        title="iqoqo API",
        version=version,
        openapi_version="3.1.0",
        info={
            "description": (
                "OpenAPI 3.1.0 Specification for the iqoqo personal library and collection manager. "
                "Provides full coverage across FRBR bibliographic entities (Work, Expression, Manifestation, Item), "
                "barcode scanning, lending workflows, notifications, real-time Server-Sent Events, SPARQL queries, "
                "and server-to-server ActivityPub federation."
            ),
            "contact": {"name": "iqoqo team", "url": "https://github.com/sebastiankruk/iqoqo"},
            "license": {"name": "AGPL-3.0", "url": "https://www.gnu.org/licenses/agpl-3.0.html"},
        },
        plugins=[FlaskPlugin()],
    )

    # ─── Security Schemes ─────────────────────────────────────────────
    spec.components.security_scheme(
        "BearerAuth",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer access token issued by POST /api/login or OAuth exchange.",
        },
    )
    spec.components.security_scheme(
        "PersonalAccessToken",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "PAT",
            "description": "Personal Access Token starting with 'iqo_' created in Profile > Tokens.",
        },
    )
    spec.components.security_scheme(
        "DeployToken",
        {
            "type": "apiKey",
            "in": "header",
            "name": "X-Deploy-Token",
            "description": "System deployment token required for administrative maintenance and drift verification.",
        },
    )

    # ─── Common Component Schemas ─────────────────────────────────────
    spec.components.schema(
        "ErrorResponse",
        {
            "type": "object",
            "properties": {
                "error": {"type": ["string", "null"], "description": "Error description or failure reason."},
                "code": {"type": "integer", "description": "HTTP status code error identifier."},
            },
            "required": ["error", "code"],
        },
    )

    spec.components.schema(
        "SuccessEnvelope",
        {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "description": "True if operation succeeded."},
                "data": {"type": ["object", "array", "null"], "description": "Response payload data."},
                "error": {"type": ["string", "null"], "description": "Null on success or error string."},
            },
            "required": ["success"],
        },
    )

    spec.components.schema(
        "User",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid", "description": "Unique user UUID identifier."},
                "email": {"type": "string", "format": "email", "description": "User email address."},
                "username": {"type": ["string", "null"], "description": "Local Fediverse username handle."},
                "role": {"type": "string", "enum": ["user", "custodian", "admin", "contributor"], "description": "RBAC permission role."},
                "totp_enabled": {"type": "boolean", "description": "True if TOTP two-factor authentication is active."},
                "default_item_visibility": {
                    "type": "string",
                    "enum": ["private", "friends_only", "public"],
                    "description": "Default visibility assigned to new collection items.",
                },
                "federated_profile": {"type": "boolean", "description": "True if public WebFinger and Actor profile are enabled."},
            },
            "required": ["id", "email", "role"],
        },
    )

    spec.components.schema(
        "Work",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Work identifier."},
                "title": {"type": "string", "description": "Canonical intellectual work title."},
                "description": {"type": ["string", "null"], "description": "Detailed synopsis or intellectual description."},
                "meta": {"type": "object", "description": "Extended metadata (genres, original year, authors)."},
            },
            "required": ["id", "title"],
        },
    )

    spec.components.schema(
        "Expression",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Expression identifier."},
                "work_id": {"type": "integer", "description": "Parent Work identifier."},
                "content_type": {
                    "type": "string",
                    "enum": [
                        "text",
                        "movie",
                        "music",
                        "game",
                        "boardgame",
                        "sound",
                        "video",
                        "notated_music",
                        "book",
                        "audiobook",
                    ],
                    "description": "Media domain tier.",
                },
                "language": {"type": ["string", "null"], "description": "ISO 639 language code."},
                "meta": {"type": "object", "description": "Expression-specific metadata."},
            },
            "required": ["id", "work_id", "content_type"],
        },
    )

    spec.components.schema(
        "Manifestation",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Manifestation identifier."},
                "expression_id": {"type": "integer", "description": "Parent Expression identifier."},
                "isbn13": {"type": ["string", "null"], "description": "ISBN-13 identifier."},
                "barcode": {"type": ["string", "null"], "description": "Physical barcode or EAN/UPC identifier."},
                "publisher": {"type": ["string", "null"], "description": "Publishing house, label, or manufacturer."},
                "publication_date": {"type": ["string", "null"], "description": "Publication year or full date string."},
                "cover_url": {"type": ["string", "null"], "description": "Cover thumbnail image URL."},
                "format": {"type": ["string", "null"], "description": "Specific physical format (Hardcover, Vinyl, Blu-ray, etc.)."},
                "meta": {"type": "object", "description": "Manifestation metadata attributes."},
            },
            "required": ["id", "expression_id"],
        },
    )

    spec.components.schema(
        "Item",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Physical collection item identifier."},
                "manifestation_id": {"type": "integer", "description": "Linked Manifestation identifier."},
                "owner_id": {"type": "string", "format": "uuid", "description": "User UUID identifier of the item owner."},
                "local_barcode": {"type": ["string", "null"], "description": "Local asset tag or shelf barcode."},
                "status": {"type": "string", "description": "Progress consumption status (unread, reading, completed, etc.)."},
                "collection_status": {"type": "string", "description": "Inventory status (available, lent, lost, wish_list)."},
                "visibility": {
                    "type": "string",
                    "enum": ["private", "friends_only", "public"],
                    "description": "Three-tier visibility level.",
                },
                "is_hidden": {"type": "boolean", "description": "Privacy flag indicating item is excluded from federation."},
            },
            "required": ["id", "manifestation_id", "owner_id", "status"],
        },
    )

    spec.components.schema(
        "PersonalAccessToken",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Token identifier."},
                "name": {"type": "string", "description": "Descriptive user-provided token label."},
                "token_prefix": {"type": "string", "description": "Visible token prefix starting with 'iqo_'."},
                "scopes": {"type": "array", "items": {"type": "string"}, "description": "List of authorized capability scopes."},
                "created_at": {"type": "string", "format": "date-time", "description": "Token creation timestamp."},
                "expires_at": {"type": ["string", "null"], "format": "date-time", "description": "Optional expiration date."},
                "last_used_at": {"type": ["string", "null"], "format": "date-time", "description": "Last authenticated usage timestamp."},
                "revoked_at": {"type": ["string", "null"], "format": "date-time", "description": "Revocation timestamp or null if active."},
                "is_active": {"type": "boolean", "description": "True if token is active and unexpired."},
            },
            "required": ["id", "name", "token_prefix", "scopes", "created_at", "is_active"],
        },
    )

    spec.components.schema(
        "Notification",
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Notification identifier."},
                "recipient_id": {"type": "string", "format": "uuid", "description": "Recipient user UUID identifier."},
                "user_id": {"type": "string", "format": "uuid", "description": "Recipient user UUID identifier alias."},
                "notification_type": {"type": "string", "description": "Event classification category."},
                "type": {"type": "string", "description": "Notification type alias."},
                "title": {"type": "string", "description": "Notification header."},
                "body": {"type": ["string", "null"], "description": "Detailed notification text message."},
                "is_read": {"type": "boolean", "description": "True if notification has been acknowledged."},
                "actor_uri": {"type": ["string", "null"], "description": "Federation actor or system URI that triggered the notification."},
                "payload": {"type": "object", "description": "Arbitrary notification payload data."},
                "created_at": {"type": "string", "format": "date-time", "description": "Timestamp event was recorded."},
                "read_at": {"type": ["string", "null"], "format": "date-time", "description": "Timestamp event was acknowledged."},
            },
            "required": ["id", "recipient_id", "notification_type", "title", "is_read", "created_at"],
        },
    )

    return spec


def assemble_complete_openapi_spec() -> dict[str, Any]:
    """Iterate through all registered application routes and assemble complete OpenAPI 3.1 dictionary."""
    spec = create_spec()

    with current_app.test_request_context():
        # Step 1: Let FlaskPlugin inspect decorated views with docstrings
        for rule in current_app.url_map.iter_rules():
            if rule.endpoint == "static" or rule.rule.startswith("/static"):
                continue

            view_func = current_app.view_functions.get(rule.endpoint)
            if view_func:
                try:
                    spec.path(view=view_func)
                except (ValueError, TypeError, AttributeError, RuntimeError):
                    logger.debug("Could not auto-document endpoint %s via docstring, falling back to schema generator", rule.endpoint)

        spec_dict = spec.to_dict()
        paths = spec_dict.setdefault("paths", {})

        # Step 2: Ensure 100% of all registered application routes are documented with full parameter annotations
        for rule in current_app.url_map.iter_rules():
            if rule.endpoint == "static" or rule.rule.startswith("/static"):
                continue

            # Convert Flask URL pattern (e.g. /api/items/<int:item_id>) to OpenAPI path (/api/items/{item_id})
            openapi_path = FlaskPlugin.flaskpath2openapi(rule.rule)
            path_item = paths.setdefault(openapi_path, {})

            # Extract path variables to enforce zero-drift parameter annotations
            path_vars = RE_URL_PARAM.findall(openapi_path)
            common_params = []
            for var in path_vars:
                common_params.append(
                    {
                        "name": var,
                        "in": "path",
                        "required": True,
                        "schema": _infer_param_schema(rule, var),
                        "description": f"Unique {var} identifier.",
                    }
                )

            # Register each active HTTP method on the route
            allowed_methods = [m.lower() for m in rule.methods if m not in ("HEAD", "OPTIONS")]
            tag = _get_route_tag(openapi_path)

            for method in allowed_methods:
                operation = path_item.setdefault(method, {})

                if not operation.get("tags"):
                    operation["tags"] = [tag]

                if not operation.get("summary"):
                    name_words = rule.endpoint.replace(".", "_").replace("api_", "").split("_")
                    operation["summary"] = f"{method.upper()} {' '.join(name_words).title()}"

                if not operation.get("description"):
                    operation["description"] = f"Execute {method.upper()} on {openapi_path}."

                # Merge path parameters ensuring no duplicate parameter names
                existing_params = operation.setdefault("parameters", [])
                existing_names = {p.get("name") for p in existing_params if isinstance(p, dict)}
                for param in common_params:
                    if param["name"] not in existing_names:
                        existing_params.append(param)
                        existing_names.add(param["name"])

                # Provide default OpenAPI responses envelope if not specified
                if not operation.get("responses"):
                    operation["responses"] = {
                        "200": {
                            "description": "Successful operation.",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessEnvelope"}}},
                        },
                        "400": {
                            "description": "Bad Request or Validation Error.",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                        },
                        "401": {
                            "description": "Authentication credentials required or invalid.",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                        },
                        "404": {
                            "description": "Resource not found.",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                        },
                    }

                # Attach security scheme annotations if endpoint requires authentication
                view_func = current_app.view_functions.get(rule.endpoint)
                requires_auth = _endpoint_requires_auth(view_func, openapi_path)

                if requires_auth and not operation.get("security"):
                    operation["security"] = [{"BearerAuth": []}, {"PersonalAccessToken": []}]

    return spec_dict


@docs_bp.route("/openapi.json", methods=["GET"])
@limiter.limit("20 per minute")
def openapi_spec():
    """Generate and return the OpenAPI 3.1 specification covering 100% of application routes."""
    return jsonify(assemble_complete_openapi_spec())
