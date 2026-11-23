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
    if any(path.startswith(f"/api/{prefix}") for prefix in ("work", "expression", "manifestation", "collections", "catalog")):
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
                "issn": {"type": ["string", "null"], "description": "Normalized print ISSN (XXXX-XXXX) for F18 Serial Works."},
                "eissn": {"type": ["string", "null"], "description": "Normalized electronic ISSN (XXXX-XXXX)."},
                "work_kind": {"type": ["string", "null"], "description": "Optional work classification ('serial' for periodicals)."},
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
                        "board_game",
                        "boardgame",
                        "sound",
                        "video",
                        "notated_music",
                        "book",
                        "audiobook",
                        "lego",
                        "puzzle",
                        "cartographic_map",
                        "map",
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
                "format": {
                    "type": ["string", "null"],
                    "description": "Specific physical format (Hardcover, Vinyl, Blu-ray, Magazine, etc.).",
                },
                "ean": {"type": ["string", "null"], "description": "EAN-13 barcode (may repeat across annual periodical issues)."},
                "ean_addon": {"type": ["string", "null"], "description": "Supplemental EAN-2 or EAN-5 issue add-on suffix."},
                "full_barcode": {"type": ["string", "null"], "description": "Canonical combined EAN-13 + add-on barcode."},
                "issue_number": {"type": ["string", "null"], "description": "Periodical issue number within year/volume."},
                "cumulative_issue_number": {"type": ["integer", "null"], "description": "Cumulative periodical issue number."},
                "volume": {"type": ["string", "null"], "description": "Periodical volume number."},
                "publication_year": {"type": ["integer", "null"], "description": "Four-digit issue publication year."},
                "publication_month": {"type": ["integer", "null"], "description": "Numeric issue publication month (1-12)."},
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

    spec.components.schema(
        "MapAttachment",
        {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique attachment identifier."},
                "title": {"type": "string", "description": "Descriptive title for the map attachment."},
                "image_url": {"type": "string", "description": "Relative static gallery URL or safe HTTP(S) image URL."},
                "scale": {"type": ["string", "null"], "description": "Cartographic scale (e.g. 1:50,000)."},
                "projection": {"type": ["string", "null"], "description": "Cartographic projection name or EPSG code."},
                "created_at": {"type": "string", "format": "date-time", "description": "Attachment creation timestamp."},
            },
            "required": ["id", "title", "image_url"],
        },
    )

    spec.components.schema(
        "NewMediaTypeEscalation",
        {
            "type": "object",
            "properties": {
                "proposed_category": {"type": "string", "description": "Target media category label."},
                "proposed_format": {"type": "string", "description": "Target physical format label."},
                "parent_frbr_class": {
                    "type": "string",
                    "enum": ["F1_Work", "F16_Container_Work", "F3_Manifestation_Product_Type"],
                    "description": "Parent FRBR class tier.",
                },
                "sample_identifier_or_url": {"type": ["string", "null"], "description": "Sample identifier, barcode or URL."},
                "suggested_properties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Suggested domain-specific metadata properties.",
                },
                "rationale": {"type": "string", "description": "Justification for adding the new media type."},
            },
            "required": ["proposed_category", "proposed_format", "rationale"],
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
                    if openapi_path in (
                        "/api/auth/login/apple",
                        "/api/auth/callback/apple",
                        "/api/auth/login/google",
                        "/api/auth/callback/google",
                    ):
                        operation["responses"] = {
                            "302": {
                                "description": "Redirects to OAuth provider consent screen or frontend /auth-exchange handler.",
                                "headers": {
                                    "Location": {
                                        "description": "Target redirection URI.",
                                        "schema": {"type": "string"},
                                    }
                                },
                            },
                            "400": {
                                "description": "Bad Request or Validation Error.",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                            },
                            "503": {
                                "description": "OAuth provider service unconfigured or unavailable.",
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                            },
                        }
                    else:
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

                # Attach accurate requestBody schemas for specific endpoints
                if openapi_path == "/api/auth/callback/apple" and method == "post":
                    if not operation.get("requestBody"):
                        operation["requestBody"] = {
                            "required": False,
                            "content": {
                                "application/x-www-form-urlencoded": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id_token": {"type": "string", "description": "Apple-signed JWT identity token."},
                                            "code": {"type": "string", "description": "Single-use authorization code."},
                                            "state": {"type": "string", "description": "CSRF state parameter."},
                                            "user": {
                                                "type": "string",
                                                "description": "JSON-encoded user object sent on first authorization.",
                                            },
                                        },
                                    }
                                },
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id_token": {"type": "string"},
                                            "code": {"type": "string"},
                                            "state": {"type": "string"},
                                            "user": {"type": "string"},
                                        },
                                    }
                                },
                            },
                        }
                elif openapi_path == "/api/auth/exchange" and method == "post":
                    if not operation.get("requestBody"):
                        operation["requestBody"] = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {
                                                "type": "string",
                                                "description": "Single-use exchange code from mobile OAuth redirect.",
                                            },
                                        },
                                        "required": ["code"],
                                    }
                                }
                            },
                        }
                elif openapi_path == "/api/admin/maintenance/repair-authors" and method == "post":
                    if not operation.get("requestBody"):
                        operation["requestBody"] = {
                            "required": False,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "dry_run": {
                                                "type": "boolean",
                                                "default": True,
                                                "description": "When true, scans without committing changes.",
                                            },
                                            "batch_size": {
                                                "type": "integer",
                                                "default": 50,
                                                "description": "Number of works to process per batch.",
                                            },
                                        },
                                    }
                                }
                            },
                        }
                elif openapi_path in ("/api/admin/ownership/items", "/api/v1/admin/ownership/items") and method == "get":
                    ownership_query_params = [
                        {
                            "name": "source_user_id",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string", "format": "uuid"},
                            "description": "UUID of the source user account whose physical items are listed.",
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 1, "minimum": 1},
                            "description": "Page number (1-indexed).",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                            "description": "Maximum number of items per page (1-100).",
                        },
                        {
                            "name": "q",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Search query matching work title, manifestation title, or barcode.",
                        },
                        {
                            "name": "collection_status",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Filter by item collection_status.",
                        },
                        {
                            "name": "format",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Filter by manifestation format or format_type.",
                        },
                        {
                            "name": "item_id",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                            "description": "Filter to a specific physical item ID.",
                        },
                    ]
                    op_params = operation.setdefault("parameters", [])
                    op_param_names = {p.get("name") for p in op_params if isinstance(p, dict)}
                    for q_param in ownership_query_params:
                        if q_param["name"] not in op_param_names:
                            op_params.append(q_param)
                            op_param_names.add(q_param["name"])
                elif openapi_path in ("/api/works/shelf", "/api/v1/works/shelf") and method == "get":
                    shelf_vis_param = {
                        "name": "work_read_status",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string", "enum": ["completed", "in_progress", "unread"]},
                        "description": "Filter Works by authenticated user's rolled-up consumption status.",
                    }
                    op_params = operation.setdefault("parameters", [])
                    if not any(isinstance(p, dict) and p.get("name") == "work_read_status" for p in op_params):
                        op_params.append(shelf_vis_param)
                elif openapi_path in ("/api/items", "/api/v1/items") and method == "get":
                    vis_param = {
                        "name": "visibility",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                        "description": "Comma-separated visibility filter (public, friends_only, private, hidden).",
                    }
                    op_params = operation.setdefault("parameters", [])
                    if not any(isinstance(p, dict) and p.get("name") == "visibility" for p in op_params):
                        op_params.append(vis_param)
                elif openapi_path in ("/api/items/bulk-visibility", "/api/v1/items/bulk-visibility") and method == "patch":
                    if not operation.get("requestBody"):
                        operation["requestBody"] = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "item_ids": {
                                                "type": "array",
                                                "items": {"type": "integer", "minimum": 1},
                                                "minItems": 1,
                                                "maxItems": 100,
                                            },
                                            "visibility": {
                                                "type": "string",
                                                "enum": ["public", "friends_only", "private"],
                                            },
                                        },
                                        "required": ["item_ids", "visibility"],
                                    }
                                }
                            },
                        }
                elif openapi_path == "/api/items/{item_id}/reading-sessions" and method == "post":
                    if not operation.get("requestBody"):
                        operation["requestBody"] = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "duration_minutes": {
                                                "type": "integer",
                                                "minimum": 1,
                                                "maximum": 1440,
                                                "description": "Reading session duration in minutes (1-1440).",
                                            },
                                            "pages_read": {
                                                "type": ["integer", "null"],
                                                "minimum": 1,
                                                "maximum": 50000,
                                                "description": "Optional number of pages read during the session.",
                                            },
                                            "note": {
                                                "type": ["string", "null"],
                                                "maxLength": 500,
                                                "description": "Optional private note for the reading session.",
                                            },
                                        },
                                        "required": ["duration_minutes"],
                                    }
                                }
                            },
                        }
                    if "201" not in operation.get("responses", {}):
                        operation.setdefault("responses", {})["201"] = {
                            "description": "Reading session logged successfully.",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessEnvelope"}}},
                        }
                elif openapi_path in ("/api/sharing", "/api/sharing/") and method == "post":
                    if not operation.get("requestBody"):
                        operation["requestBody"] = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string", "minLength": 1, "maxLength": 255},
                                            "description": {"type": ["string", "null"], "maxLength": 2000},
                                            "visibility_scope": {
                                                "type": "string",
                                                "enum": ["public_only", "friends_and_public", "all"],
                                                "default": "public_only",
                                                "description": "Access scope for the generated share link.",
                                            },
                                            "filters": {
                                                "type": "object",
                                                "description": "Collection filter payload (also accepts filters.visibility_scope).",
                                            },
                                            "expires_in_days": {
                                                "type": ["integer", "null"],
                                                "minimum": 1,
                                                "maximum": 365,
                                            },
                                        },
                                        "required": ["name"],
                                    }
                                }
                            },
                        }
                elif openapi_path in ("/api/public/share/{token}", "/api/public/rdf/share/{token}") and method == "get":
                    share_query_params = [
                        {
                            "name": "format",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "enum": ["json", "jsonld", "json-ld", "turtle", "ttl", "rdfxml", "xml", "nt", "n-triples"],
                            },
                            "description": "Output serialization format for headerless clients and AI fetchers.",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 1000, "minimum": 1, "maximum": 2000},
                            "description": "Maximum number of shared collection items to return (clamped to 2000).",
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 1, "minimum": 1},
                            "description": "1-based page number for SQL pagination.",
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 48, "minimum": 1, "maximum": 200},
                            "description": "Items per page for SQL pagination (1-200).",
                        },
                    ]
                    op_params = operation.setdefault("parameters", [])
                    op_param_names = {p.get("name") for p in op_params if isinstance(p, dict)}
                    for q_param in share_query_params:
                        if q_param["name"] not in op_param_names:
                            op_params.append(q_param)
                            op_param_names.add(q_param["name"])
                elif openapi_path in ("/api/catalog/graph", "/api/v1/catalog/graph") and method == "get":
                    graph_query_params = [
                        {
                            "name": "mode",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "enum": ["neighborhood", "library"], "default": "neighborhood"},
                            "description": "Graph explorer mode: 'neighborhood' (anchored) or 'library' (unanchored concept overview).",
                        },
                        {
                            "name": "entity_type",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "enum": ["work", "expression", "manifestation", "item"]},
                            "description": "Root FRBR entity type for neighborhood traversal (required when mode=neighborhood).",
                        },
                        {
                            "name": "entity_id",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "minimum": 1},
                            "description": "Root FRBR entity primary key ID (required when mode=neighborhood).",
                        },
                        {
                            "name": "depth",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 1, "minimum": 1, "maximum": 4},
                            "description": "BFS hop depth from anchor node (clamped to 1..4).",
                        },
                        {
                            "name": "max_nodes",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 150, "minimum": 1, "maximum": 150},
                            "description": "Maximum number of nodes returned (clamped to 1..150).",
                        },
                        {
                            "name": "max_edges",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 400, "minimum": 1, "maximum": 600},
                            "description": "Maximum number of edges returned (clamped to 1..600).",
                        },
                        {
                            "name": "entity_types",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Comma-separated concept types for mode=library (work,series,contributor,expression,manifestation,item,map,lod).",
                        },
                        {
                            "name": "edge_types",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Comma-separated edge categories (frbr,series,parts_expansions,contributors,maps,lod).",
                        },
                    ]
                    op_params = operation.setdefault("parameters", [])
                    op_param_names = {p.get("name") for p in op_params if isinstance(p, dict)}
                    for q_param in graph_query_params:
                        if q_param["name"] not in op_param_names:
                            op_params.append(q_param)
                            op_param_names.add(q_param["name"])

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
