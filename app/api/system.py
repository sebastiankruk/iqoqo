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

from flask import Response, g, jsonify, make_response, request, send_file, send_from_directory
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import admin_required, require_auth
from app.config import Config
from app.core.data_manager import DataManager
from app.core.frbr_service import serialize_collection_to_rdf
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


@api_bp.route("/v1/items/export", methods=["GET"])
@require_auth
def export_user_collection():
    """Export the authenticated user's collection in JSON, JSON-LD, or Turtle format."""
    fmt = request.args.get("format", "json")

    if fmt == "json":
        items = Item.query.filter_by(owner_id=g.user_id).all()
        data = []
        for item in items:
            entry = {
                "id": str(item.id),
                "manifestation_id": str(item.manifestation_id),
                "status": item.status,
                "is_hidden": item.is_hidden,
                "meta": item.meta,
            }
            if item.manifestation:
                m = item.manifestation
                entry["title"] = getattr(m, "title", None) or (m.expression.work.title if m.expression and m.expression.work else None)
                entry["isbn13"] = m.isbn13
                entry["publisher"] = m.publisher
                if m.expression:
                    entry["content_type"] = m.expression.content_type
                    entry["language"] = m.expression.language
                    if m.expression.work:
                        entry["work_title"] = m.expression.work.title
                        entry["authors"] = (m.expression.work.meta or {}).get("authors", [])
            data.append(entry)
        output = BytesIO()
        output.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
        output.seek(0)
        return send_file(output, mimetype="application/json", as_attachment=True, download_name="iqoqo_collection.json")

    if fmt in ("json-ld", "turtle"):
        items = Item.query.filter_by(owner_id=g.user_id).all()
        base_url = request.url_root.rstrip("/")
        output_format = "json-ld" if fmt == "json-ld" else "turtle"
        rdf_data = serialize_collection_to_rdf(items, base_url, output_format=output_format)

        if output_format == "json-ld":
            mimetype = "application/ld+json"
            filename = "iqoqo_collection.jsonld"
        else:
            mimetype = "text/turtle"
            filename = "iqoqo_collection.ttl"

        return Response(
            response=rdf_data,
            status=200,
            mimetype=mimetype,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return jsonify({"error": f"Unsupported format: {fmt}. Use 'json', 'json-ld', or 'turtle'."}), 400


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
