"""Defines the API endpoints for the application."""

import json
from io import BytesIO
from typing import Any

from flask import jsonify, request, send_file, session
from sqlalchemy import func
from sqlalchemy.orm import selectinload

import app.utils.isbn as isbn_utils
from app.core.data_manager import DataManager
from app.db.models import Expression, Item, Manifestation, Work, db

from . import api_bp


def _invalid_json_payload_response():
    """Return a standardized 400 response for absent/invalid JSON payloads."""
    return jsonify({"success": False, "data": None, "error": "Invalid or missing JSON payload"}), 400


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok", "service": "iqoqo-api"})


@api_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    """Get dashboard statistics for the frontend."""
    stats = DataManager.get_stats()
    return jsonify({"success": True, "data": stats, "error": None})


@api_bp.route("/items", methods=["GET"])
def get_items():
    """Get all items with pagination support.

    Query parameters:
        page (int, default 1):    1-based page number.
        limit (int, default 20):  Maximum items per page.
        statuses (str, optional): Comma-separated list of item statuses to filter by
                                  (e.g. ``reading,wish_list``).  When omitted all
                                  statuses are returned.

    Results are sorted by most-recently-updated first, falling back to
    ``added_at`` for legacy rows that pre-date the ``updated_at`` column.
    """
    # Get pagination parameters
    page_param = request.args.get("page", "1")
    limit_param = request.args.get("limit", "20")
    statuses_filter = request.args.get("statuses", None)  # Optional filter by item status

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return (
            jsonify(
                {
                    "success": False,
                    "data": None,
                    "error": "Invalid pagination parameters: 'page' and 'limit' must be integers.",
                }
            ),
            400,
        )

    if page < 1 or limit < 1:
        return (
            jsonify(
                {
                    "success": False,
                    "data": None,
                    "error": "Invalid pagination parameters: 'page' and 'limit' must be positive integers.",
                }
            ),
            400,
        )
    offset = (page - 1) * limit

    # Get all items with pagination
    query = Item.query.options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
    if statuses_filter:
        statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()]
        query = query.filter(Item.status.in_(statuses_list))
    # Order by most-recently-updated first; fall back to added_at for legacy rows
    # where updated_at is NULL (pre-migration data).
    query = query.order_by(func.coalesce(Item.updated_at, Item.added_at).desc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()

    items_data = []
    for item in items:
        manifestation = item.manifestation
        work_title = ""
        authors = []
        if manifestation and manifestation.expression and manifestation.expression.work:
            work = manifestation.expression.work
            work_title = work.title or ""
            authors = work.meta.get("authors", []) if work.meta else []

        items_data.append(
            {
                "id": item.id,
                "owner_id": item.owner_id,
                "status": item.status,
                "manifestation_id": item.manifestation_id,
                "isbn": manifestation.isbn13 if manifestation else None,
                "title": work_title,
                "authors": authors,
                "added_at": item.added_at.isoformat() if item.added_at else None,
                "updated_at": (item.updated_at or item.added_at).isoformat() if (item.updated_at or item.added_at) else None,
            }
        )

    return jsonify(
        {
            "success": True,
            "data": items_data,
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            },
            "error": None,
        }
    )


@api_bp.route("/items/<int:item_id>", methods=["GET"])
def get_item_detail(item_id: int):
    """Get detailed information about a specific item."""
    item = db.session.get(Item, item_id)

    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    manifestation = item.manifestation
    item_data = {
        "id": item.id,
        "owner_id": item.owner_id,
        "status": item.status,
        "manifestation_id": item.manifestation_id,
        "meta": item.meta,
    }

    if manifestation:
        item_data["isbn"] = manifestation.isbn13
        item_data["manifestation_meta"] = manifestation.meta

        if manifestation.expression:
            expression = manifestation.expression
            item_data["expression"] = {
                "id": expression.id,
                "content_type": expression.content_type,
                "language": expression.language,
            }

            if expression.work:
                work = expression.work
                item_data["work"] = {
                    "id": work.id,
                    "title": work.title,
                    "authors": work.meta.get("authors", []) if work.meta else [],
                    "meta": work.meta,
                }

    return jsonify({"success": True, "data": item_data, "error": None})


@api_bp.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id: int):
    """Update an item's status or metadata."""
    item = db.session.get(Item, item_id)

    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _invalid_json_payload_response()

    if data.get("status"):
        item.status = data["status"]

    if data.get("meta"):
        item.meta = data["meta"]

    try:
        db.session.commit()
        return jsonify({"success": True, "data": {"id": item.id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        return jsonify({"success": False, "data": None, "error": str(e)}), 500


@api_bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id: int):
    """Delete an item."""
    item = db.session.get(Item, item_id)

    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": item_id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        return jsonify({"success": False, "data": None, "error": str(e)}), 500


@api_bp.route("/isbn/<isbn>", methods=["GET"])
def lookup_isbn(isbn: str):
    """Look up book metadata by ISBN from multiple sources or local DB."""
    # First check if we have it locally
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    # If we have manifestation with metadata in meta field, return it
    if manifestation and manifestation.meta and manifestation.meta.get("Title"):
        return jsonify(**manifestation.meta)

    # If we have manifestation with Work/Expression data, build metadata from there
    if manifestation and manifestation.expression and manifestation.expression.work:
        work = manifestation.expression.work
        work_metadata = {
            "Title": work.title or "",
            "Authors": work.meta.get("authors", []) if work.meta else [],
        }
        # Only return if we have at least a title
        if work_metadata["Title"]:
            # Update manifestation.meta for future use
            if not manifestation.meta:
                manifestation.meta = {}
            manifestation.meta.update(work_metadata)
            try:
                db.session.commit()
            except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
                db.session.rollback()
                # Continue anyway, we can still return the data
                print(f"Warning: Failed to update manifestation.meta: {e}")
            return jsonify(**work_metadata)

    # Canonicalize ISBN-10 or ISBN-13 input into a standard 13-digit string.
    canonical_isbn = isbn_utils.canonicalize_isbn(isbn)
    if not canonical_isbn:
        return jsonify({"error": "Invalid ISBN"}), 400

    # Fetch metadata from external sources (Google Books → Open Library).
    metadata: dict[str, Any] | None = isbn_utils.fetch_isbn_metadata(canonical_isbn)
    if not metadata:
        return jsonify({}), 404

    # Store in database if not exists
    if not manifestation:
        # We need to create Work -> Expression -> Manifestation
        work = Work(title=metadata["Title"], meta={"authors": metadata["Authors"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13=canonical_isbn, meta=metadata)
        db.session.add(manifestation)
        db.session.commit()
    else:
        # Update existing manifestation
        manifestation.meta = metadata
        # Also update the Work if it has a title
        if manifestation.expression and manifestation.expression.work:
            manifestation.expression.work.title = metadata["Title"]
            if not manifestation.expression.work.meta:
                manifestation.expression.work.meta = {}
            manifestation.expression.work.meta["authors"] = metadata["Authors"]
        db.session.commit()

    return jsonify(**metadata)


@api_bp.route("/isbn/<isbn>", methods=["POST"])
def update_manifestation(isbn: str):
    """Update manifestation metadata."""
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    if not manifestation:
        return jsonify({"error": "Manifestation not found"}), 404

    metadata = request.get_json(silent=True)
    if not isinstance(metadata, dict):
        return _invalid_json_payload_response()

    if metadata:
        # Update the manifestation's metadata
        if not manifestation.meta:
            manifestation.meta = {}
        # Need to update the mutable dict properly for SQLAlchemy to detect changes
        updated_meta = dict(manifestation.meta)
        updated_meta.update(metadata)
        manifestation.meta = updated_meta

        # Also update the work title and authors if provided
        if manifestation.expression and manifestation.expression.work:
            if "Title" in metadata:
                manifestation.expression.work.title = metadata["Title"]
            if "Authors" in metadata:
                if not manifestation.expression.work.meta:
                    manifestation.expression.work.meta = {}
                work_meta = dict(manifestation.expression.work.meta)
                work_meta["authors"] = metadata["Authors"]
                manifestation.expression.work.meta = work_meta

        db.session.commit()
        return jsonify({"status": "ok"})

    return jsonify({"error": "No metadata provided"}), 400


@api_bp.route("/item/<isbn>", methods=["GET"])
def get_items_by_isbn(isbn: str):
    """Get all items for a given ISBN."""
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    if not manifestation:
        return jsonify({"error": "Manifestation not found"}), 404

    items = Item.query.filter_by(manifestation_id=manifestation.id).all()

    if not items:
        return jsonify({"error": "No items found"}), 404

    return jsonify({"ids": [item.id for item in items]})


@api_bp.route("/item/<isbn>", methods=["POST"])
def add_item(isbn: str):
    """Add a new item for a given ISBN."""
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    if not manifestation:
        # If manifestation doesn't exist, try to fetch it first
        lookup_response = lookup_isbn(isbn)
        # lookup_isbn returns a tuple (response, status_code) on error
        if isinstance(lookup_response, tuple):
            status_code = lookup_response[1] if len(lookup_response) > 1 else 404
            if status_code != 200:
                return jsonify({"error": "Manifestation not found"}), 404
        manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    metadata = request.get_json()

    # Update manifestation metadata if provided
    if metadata:
        if not manifestation.meta:
            manifestation.meta = {}
        # Need to update the mutable dict properly for SQLAlchemy to detect changes
        updated_meta = dict(manifestation.meta)
        updated_meta.update(metadata)
        manifestation.meta = updated_meta

        # Also update the work title and authors if provided
        if manifestation.expression and manifestation.expression.work:
            if "Title" in metadata:
                manifestation.expression.work.title = metadata["Title"]
            if "Authors" in metadata:
                if not manifestation.expression.work.meta:
                    manifestation.expression.work.meta = {}
                work_meta = dict(manifestation.expression.work.meta)
                work_meta["authors"] = metadata["Authors"]
                manifestation.expression.work.meta = work_meta

    # Get or create client ID (simplified - you may want to use proper authentication)
    client_id = session.get("client_id", "default_user")

    # Create new item
    item = Item(manifestation_id=manifestation.id, owner_id=client_id, status="available", meta={})

    db.session.add(item)
    db.session.commit()

    return jsonify({"item_id": item.id})


# =============================================================================
# Admin API Endpoints
# =============================================================================


@api_bp.route("/admin/stats", methods=["GET"])
def get_stats():
    """Get database statistics."""
    stats = DataManager.get_stats()
    return jsonify(stats)


@api_bp.route("/admin/export", methods=["GET"])
def export_data():
    """
    Export all database content as JSON.

    Returns:
        JSON file download containing all database content.
    """
    try:
        data = DataManager.export_all()

        # Create an in-memory file
        output = BytesIO()
        output.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
        output.seek(0)

        return send_file(
            output,
            mimetype="application/json",
            as_attachment=True,
            download_name=f'iqoqo_export_{data["exported_at"]}.json',
        )
    except (OSError, ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/import", methods=["POST"])
def import_data():
    """
    Import data from JSON.

    Expects:
        JSON body containing the data structure or multipart/form-data with file.
        Optional query parameter: clear_existing=true

    Returns:
        JSON with import statistics.
    """
    try:
        clear_existing = request.args.get("clear_existing", "false").lower() == "true"

        # Check if data is in the request body or as a file upload
        if request.is_json:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return _invalid_json_payload_response()
        elif "file" in request.files:
            file = request.files["file"]
            data = json.load(file)
        else:
            return jsonify({"error": "No data provided"}), 400

        counts = DataManager.import_data(data, clear_existing=clear_existing)
        return jsonify({"status": "success", "imported": counts})
    except (ValueError, TypeError, KeyError, db.exc.SQLAlchemyError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/clear", methods=["DELETE"])
def clear_data():
    """
    Clear all data from the database. Use with extreme caution!

    Requires confirmation in the request body: {"confirm": true}
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _invalid_json_payload_response()

    if not data.get("confirm"):
        return jsonify({"error": 'Confirmation required. Send {"confirm": true} to proceed.'}), 400

    try:
        DataManager.clear_all_data()
        return jsonify({"status": "success", "message": "All data cleared"})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        return jsonify({"error": str(e)}), 500
