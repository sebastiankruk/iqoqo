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
from flask import Blueprint, Response, jsonify

api_bp = Blueprint("api", __name__, url_prefix="/api")


def invalid_json_payload_response() -> tuple[Response, int]:
    """Return a standardized 400 response for absent/invalid JSON payloads."""
    return jsonify({"success": False, "data": None, "error": "Invalid or missing JSON payload"}), 400
