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

from flask import g, jsonify, make_response, request, send_file, send_from_directory
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import admin_required, optional_auth, require_auth
from app.api.filters import parse_csv_param
from app.config import Config
from app.core.data_manager import DataManager
from app.core.limiter import limiter
from app.db.models import Item, Manifestation, User, Work, db
from app.utils.covers import COVERS_DIR, GALLERY_DIR


@api_bp.route("/static/covers/<path:filename>", methods=["GET", "HEAD"])
@limiter.exempt
def serve_cover(filename: str):
    """Serve a cover image from the covers directory."""
    response = make_response(send_from_directory(COVERS_DIR, filename))

    wants_provenance = request.args.get("include") == "provenance" or request.headers.get("X-Include-Provenance", "").strip() in (
        "1",
        "true",
        "yes",
    )
    if wants_provenance:
        from sqlalchemy import or_

        isbn_prefix = filename.split("_")[0].split(".")[0]

        m = (
            db.session.query(Manifestation.id, Manifestation.meta)
            .filter(
                or_(
                    Manifestation.cover_url == filename,
                    Manifestation.cover_url == f"/static/covers/{filename}",
                    Manifestation.cover_url == f"{Config.COVERS_BASE_URL}/{filename}",
                    Manifestation.isbn13 == isbn_prefix,
                )
            )
            .first()
        )

        if m:
            response.headers["X-Manifestation-ID"] = str(m.id)
            if m.meta and "cover_source" in m.meta:
                response.headers["X-Image-Source"] = str(m.meta["cover_source"])

        response.headers["Access-Control-Expose-Headers"] = "X-Manifestation-ID, X-Image-Source"

    return response


@api_bp.route("/static/gallery/<path:filename>", methods=["GET"])
@limiter.exempt
def serve_gallery_image(filename: str):
    """Serve a gallery image from the gallery directory."""
    return send_from_directory(GALLERY_DIR, filename)


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "iqoqo-api", "version": Config.VERSION, "api_version": "v1"})


@api_bp.route("/config", methods=["GET"])
def get_config():
    """Return public application configuration for the frontend (non-sensitive)."""
    from app.db.models import InstanceSettings

    def is_true(v):
        if isinstance(v, bool):
            return v
        return str(v or "").lower() == "true"

    return jsonify(
        {
            "success": True,
            "data": {
                "federation_enabled": Config.FEDERATION_ENABLED,
                "version": Config.VERSION,
                "maintenance_mode": is_true(InstanceSettings.get_value("MAINTENANCE_MODE", False)),
            },
            "error": None,
        }
    )


@api_bp.route("/stats", methods=["GET"])
@require_auth
def get_dashboard_stats():
    stats = DataManager.get_stats(owner_id=getattr(g, "user_id", None))
    return jsonify({"success": True, "data": stats, "error": None})


@api_bp.route("/stats/facets", methods=["GET"])
@optional_auth
@limiter.limit("60 per minute")
def get_faceted_stats():
    """Return cross-filtered per-facet counts for the faceted navigation sidebar.

    Accepts the same filter query params as /api/items to narrow counts.
    When ``scope=user``, counts are filtered to the authenticated user's items.
    When ``scope=global``, counts reflect all entities in the catalog
    (unauthenticated users see public catalog-level counts).

    The ``view`` param controls the FRBR level at which counts are aggregated:
    ``items``, ``manifestations``, ``expressions``, or ``works``.
    """
    scope = request.args.get("scope", "user")
    view = request.args.get("view", "items")
    owner_id = getattr(g, "user_id", None) if scope == "user" else None
    category_str = request.args.get("category")
    fmt_str = request.args.get("format")
    tags_str = request.args.get("tags")
    collections_str = request.args.get("collections")
    genres_str = request.args.get("genres")
    publishers_str = request.args.get("publishers")
    statuses_str = request.args.get("statuses")
    borrowed_only = request.args.get("borrowed", "false").lower() == "true"
    missing_cover = request.args.get("missing_cover", "false").lower() == "true"
    missing_id = request.args.get("missing_id", "false").lower() == "true"

    category_list = parse_csv_param(category_str)
    fmt_list_raw = parse_csv_param(fmt_str)
    from app.core.format_normalizer import expand_format_filter

    fmt_list = expand_format_filter(fmt_list_raw)
    tags_list = parse_csv_param(tags_str)
    collections_list = parse_csv_param(collections_str)
    genres_list = parse_csv_param(genres_str)
    publishers_list = parse_csv_param(publishers_str)
    statuses_list = parse_csv_param(statuses_str)

    stats = DataManager.get_faceted_stats(
        owner_id=owner_id,
        category=category_list,
        fmt=fmt_list,
        tags=tags_list,
        collections=collections_list,
        genres=genres_list,
        publishers=publishers_list,
        statuses=statuses_list,
        borrowed_only=borrowed_only,
        missing_cover=missing_cover,
        missing_id=missing_id,
        view=view,
    )
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
@require_auth
@admin_required
def get_stats():
    stats = DataManager.get_stats()
    return jsonify(stats)


@api_bp.route("/admin/export", methods=["GET"])
@require_auth
@admin_required
def export_data():
    try:
        data = DataManager.export_all()
        output = BytesIO()
        output.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
        output.seek(0)
        return send_file(output, mimetype="application/json", as_attachment=True, download_name=f"iqoqo_export_{data['exported_at']}.json")
    except (OSError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/import", methods=["POST"])
@require_auth
@admin_required
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
@require_auth
@admin_required
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
