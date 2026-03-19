"""(Handles health, stats, and admin actions)"""

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
import json
from io import BytesIO

from flask import jsonify, request, send_file, send_from_directory
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import require_auth
from app.config import Config
from app.core.data_manager import DataManager
from app.db.models import Item, Manifestation, User, Work, db
from app.utils.covers import COVERS_DIR


@api_bp.route("/static/covers/<path:filename>", methods=["GET"])
def serve_cover(filename: str):
    return send_from_directory(COVERS_DIR, filename)


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "iqoqo-api", "version": Config.VERSION, "api_version": "v1"})


@api_bp.route("/config", methods=["GET"])
def get_config():
    """Return public application configuration for the frontend (non-sensitive)."""
    return jsonify({
        "success": True,
        "data": {"federation_enabled": Config.FEDERATION_ENABLED, "version": Config.VERSION},
        "error": None,
    })


@api_bp.route("/stats", methods=["GET"])
@require_auth
def get_dashboard_stats():
    stats = DataManager.get_stats(owner_id=request.user_id)
    return jsonify({"success": True, "data": stats, "error": None})


@api_bp.route("/stats/global", methods=["GET"])
def get_global_stats():
    try:
        works_count = db.session.query(Work).count()
        manifestations_count = db.session.query(Manifestation).count()
        items_count = db.session.query(Item).count()
        users_count = db.session.query(User).count()

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "works": works_count,
                        "manifestations": manifestations_count,
                        "items": items_count,
                        "users": users_count,
                    },
                    "error": None,
                }
            ),
            200,
        )
    except (SQLAlchemyError, DBAPIError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/stats", methods=["GET"])
def get_stats():
    stats = DataManager.get_stats()
    return jsonify(stats)


@api_bp.route("/admin/export", methods=["GET"])
def export_data():
    try:
        data = DataManager.export_all()
        output = BytesIO()
        output.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
        output.seek(0)
        return send_file(output, mimetype="application/json", as_attachment=True, download_name=f'iqoqo_export_{data["exported_at"]}.json')
    except (OSError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/import", methods=["POST"])
def import_data():
    try:
        clear_existing = request.args.get("clear_existing", "false").lower() == "true"

        if request.is_json:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return invalid_json_payload_response()
        elif "file" in request.files:
            file = request.files["file"]
            data = json.load(file)
        else:
            return jsonify({"error": "No data provided"}), 400

        counts = DataManager.import_data(data, clear_existing=clear_existing)
        return jsonify({"status": "success", "imported": counts})
    except (ValueError, TypeError, KeyError, SQLAlchemyError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/clear", methods=["DELETE"])
def clear_data():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return invalid_json_payload_response()

    if not data.get("confirm"):
        return jsonify({"error": 'Confirmation required. Send {"confirm": true} to proceed.'}), 400

    try:
        DataManager.clear_all_data()
        return jsonify({"status": "success", "message": "All data cleared"})
    except (SQLAlchemyError, DBAPIError) as e:
        return jsonify({"error": str(e)}), 500
