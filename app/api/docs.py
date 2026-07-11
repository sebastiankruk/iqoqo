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
import logging

from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from flask import Blueprint, current_app, jsonify

from app.core.limiter import limiter

logger = logging.getLogger(__name__)

docs_bp = Blueprint("docs", __name__)


def create_spec() -> APISpec:
    """Build the base OpenAPI schema context."""
    return APISpec(
        title="iqoqo API",
        version=current_app.config.get("APP_VERSION", "0.7.9"),
        openapi_version="3.0.3",
        info={"description": "OpenAPI / Swagger Specification for the iqoqo API ecosystem."},
        plugins=[FlaskPlugin()],
    )


@docs_bp.route("/openapi.json", methods=["GET"])
@limiter.limit("20 per minute")
def openapi_spec():
    """
    Generate and return the OpenAPI specification.
    ---
    get:
      summary: Get OpenAPI Schema
      description: Returns the auto-generated OpenAPI (Swagger) JSON specification.
      responses:
        200:
          description: OpenAPI JSON payload.
    """
    spec = create_spec()

    # Register explicitly evaluated operations inside application context
    with current_app.test_request_context():
        # Register the self-documenting route
        spec.path(view=openapi_spec)

        # Iterate over all application routes and append to spec
        for rule in current_app.url_map.iter_rules():
            if rule.endpoint != "static":
                view_func = current_app.view_functions.get(rule.endpoint)
                if view_func:
                    try:
                        spec.path(view=view_func)
                    except (ValueError, TypeError, AttributeError, RuntimeError):
                        logger.debug("Could not auto-document endpoint %s", rule.endpoint)

    return jsonify(spec.to_dict())
