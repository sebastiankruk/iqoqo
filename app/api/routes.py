"""Defines the API endpoints for the application."""

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
import os
from io import BytesIO
from typing import Any

from flask import current_app, jsonify, request, send_file, send_from_directory
from PIL import Image
from sqlalchemy import func, text
from sqlalchemy.orm import selectinload
from werkzeug.utils import secure_filename

import app.utils.isbn as isbn_utils
from app.api.decorators import require_auth, require_permission
from app.config import Config
from app.core.data_manager import DataManager
from app.core.ingest import IngestService  # Assuming this exists based on your architecture
from app.db.models import Expression, Item, Manifestation, User, Work, db
from app.utils.covers import COVERS_DIR, RAW_DIR, process_fast_cover, start_cover_processing

from . import api_bp


def _invalid_json_payload_response():
    """Return a standardized 400 response for absent/invalid JSON payloads."""
    return jsonify({"success": False, "data": None, "error": "Invalid or missing JSON payload"}), 400


@api_bp.route("/static/covers/<path:filename>", methods=["GET"])
def serve_cover(filename: str):
    """Serve a cover image from the local covers directory."""
    return send_from_directory(COVERS_DIR, filename)


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok", "service": "iqoqo-api", "version": Config.VERSION, "api_version": "v1"})


@api_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    """Get dashboard statistics for the frontend."""
    stats = DataManager.get_stats()
    return jsonify({"success": True, "data": stats, "error": None})


@api_bp.route("/stats/global", methods=["GET"])
def get_global_stats():
    """Get global instance statistics (works, manifestations, items, users)."""
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
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/items", methods=["GET"])
def get_items():
    """Get all items with pagination support.

    Query parameters:
        page (int, default 1):    1-based page number.
        limit (int, default 20):  Maximum items per page.
        statuses (str, optional): Comma-separated list of item statuses to filter by
                                  (e.g. ``reading,wish_list``). When omitted all
                                  statuses are returned.
        q (str, optional):        Free-text search query applied to this collection
                                  of items (i.e. owned/user items only). The search
                                  does not include catalog or other unowned records.

    Results are sorted by most-recently-updated first, falling back to
    ``added_at`` for legacy rows that pre-date the ``updated_at`` column.
    """
    # Get pagination parameters
    page_param = request.args.get("page", "1")
    limit_param = request.args.get("limit", "20")
    statuses_filter = request.args.get("statuses", None)  # Optional filter by item status
    q = request.args.get("q", "").strip()

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

    # If a search query is provided, run a full-text search across the global
    # manifest catalog and include owned Items where they exist. When the
    # database does not support PostgreSQL FTS (e.g. tests using SQLite), fall
    # back to a simple ILIKE search.
    if q:
        # Use the generated tsvector columns so the expressions exactly match
        # the GIN indexes created by the migration. This avoids full table scans
        # caused by mismatched expressions.
        w_tsvector_expr = "w.fts_simple"
        m_tsvector_expr = "m.fts_simple"
        tsquery_expr = "websearch_to_tsquery('simple', :q)"

        # Securely parameterize pagination and optional statuses filter
        params = {"q": q, "limit": limit, "offset": offset}
        statuses_sql = ""
        if statuses_filter:
            statuses_list = tuple(s.strip() for s in statuses_filter.split(",") if s.strip())
            params["statuses"] = statuses_list
            if "unowned" in statuses_list:
                statuses_sql = " AND (i.status IN :statuses OR i.id IS NULL)"
            else:
                statuses_sql = " AND i.status IN :statuses"

        # Attempt PostgreSQL FTS; fall back to ILIKE for SQLite in tests
        try:
            count_sql = f"""
            SELECT count(*) FROM manifestations m
            JOIN expressions e ON e.id = m.expression_id
            JOIN works w ON w.id = e.work_id
            LEFT JOIN items i ON i.manifestation_id = m.id
            WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr})
              AND i.id IS NOT NULL
            {statuses_sql}
            """

            rows_sql = f"""
            SELECT i.id as item_id, i.owner_id, i.status, m.id as manifestation_id,
                   m.isbn13, w.title, m.cover_path, m.meta as manifestation_meta,
                   w.meta as work_meta, i.added_at, i.updated_at,
                   ts_rank({w_tsvector_expr} || {m_tsvector_expr}, {tsquery_expr}) as rank
            FROM manifestations m
            JOIN expressions e ON e.id = m.expression_id
            JOIN works w ON w.id = e.work_id
            LEFT JOIN items i ON i.manifestation_id = m.id
            WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr})
              AND i.id IS NOT NULL
            {statuses_sql}
            ORDER BY rank DESC
            LIMIT :limit OFFSET :offset
            """

            # Bind params and enable tuple-expansion for statuses when provided
            count_stmt = text(count_sql)
            rows_stmt = text(rows_sql)
            if "statuses" in params:
                from sqlalchemy import bindparam

                count_stmt = count_stmt.bindparams(bindparam("statuses", expanding=True))
                rows_stmt = rows_stmt.bindparams(bindparam("statuses", expanding=True))

            total = int(db.session.execute(count_stmt, params).scalar() or 0)
            results = db.session.execute(rows_stmt, params).mappings().all()

            items_data = []
            for row in results:
                item_id = row.get("item_id")
                manifestation_id = row.get("manifestation_id")
                owner_id = row.get("owner_id")
                added_at = row.get("added_at")
                updated_at = row.get("updated_at")
                manifestation_meta = row.get("manifestation_meta") or {}
                work_meta = row.get("work_meta") or {}

                items_data.append(
                    {
                        "id": item_id,
                        "owner_id": str(owner_id) if owner_id else None,
                        "status": row.get("status"),
                        "manifestation_id": manifestation_id,
                        "isbn": row.get("isbn13"),
                        "title": row.get("title"),
                        "cover_path": row.get("cover_path"),
                        "cover_status": manifestation_meta.get("cover_status") if isinstance(manifestation_meta, dict) else None,
                        "authors": work_meta.get("authors", []) if isinstance(work_meta, dict) else [],
                        "added_at": added_at.isoformat() if added_at else None,
                        "updated_at": (updated_at or added_at).isoformat() if (updated_at or added_at) else None,
                    }
                )

        except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as exc:
            current_app.logger.exception("Error during FTS item search, attempting fallback", exc_info=exc)

            # If we are on PostgreSQL, an unexpected FTS error should not be silently masked.
            if db.engine.dialect.name == "postgresql":
                return (
                    jsonify({"success": False, "data": None, "error": "Search backend error"}),
                    500,
                )

            # Fallback for SQLite tests or databases without FTS support.
            pattern = f"%{q}%"
            base_query = (
                db.session.query(Item, Manifestation, Expression, Work)
                .select_from(Manifestation)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
                .outerjoin(Item, Item.manifestation_id == Manifestation.id)
                .filter((Work.title.ilike(pattern)) | (Manifestation.isbn13.ilike(pattern)))
            )

            if statuses_filter:
                statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()]
                if "unowned" in statuses_list:
                    base_query = base_query.filter((Item.status.in_(statuses_list)) | (Item.id.is_(None)))
                else:
                    base_query = base_query.filter(Item.status.in_(statuses_list))

            total = base_query.count()
            results = base_query.offset(offset).limit(limit).all()

            items_data = []
            for item, manifestation, _expression, work in results:
                m_id = manifestation.id if manifestation else None
                w_meta = work.meta if work and work.meta else {}
                m_meta = manifestation.meta if manifestation and manifestation.meta else {}

                items_data.append(
                    {
                        "id": item.id if item else f"m_{m_id}",
                        "owner_id": item.owner_id if item else None,
                        "status": item.status if item else "unowned",
                        "manifestation_id": m_id,
                        "isbn": manifestation.isbn13 if manifestation else None,
                        "title": work.title if work else None,
                        "cover_path": manifestation.cover_path if manifestation else None,
                        "cover_status": m_meta.get("cover_status") if m_meta else None,
                        "authors": w_meta.get("authors", []) if w_meta else [],
                        "added_at": item.added_at.isoformat() if item and item.added_at else None,
                        "updated_at": (
                            (item.updated_at or item.added_at).isoformat() if item and (item.updated_at or item.added_at) else None
                        ),
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

    # Standard collection mode (only owned items)
    query = Item.query.options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
    if statuses_filter:
        statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()]
        query = query.filter(Item.status.in_(statuses_list))
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
                "cover_path": manifestation.cover_path if manifestation else None,
                "cover_status": manifestation.meta.get("cover_status") if manifestation and manifestation.meta else None,
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
        item_data["cover_path"] = manifestation.cover_path
        item_data["cover_status"] = manifestation.meta.get("cover_status") if manifestation.meta else None

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
@require_auth
@require_permission("delete:item")
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
            manifestation.update_meta(**work_metadata)
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
        return jsonify({"success": False, "data": None, "error": f"Invalid ISBN = {isbn}"}), 400

    # Fetch metadata from external sources (Google Books → Open Library).
    metadata: dict[str, Any] | None = isbn_utils.fetch_isbn_metadata(canonical_isbn)
    if not metadata:
        return jsonify({"success": False, "data": None, "error": f"Metadata not found for ISBN = {canonical_isbn}"}), 404

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

        # --- Cover Generation Pipeline ---
        # 1. Try fast API lookup
        found_cover = process_fast_cover(manifestation, canonical_isbn)

        if not found_cover:
            # 2. Schedule async LLM generation
            manifestation.update_meta(cover_status="pending")

            # Extract title/author
            title = work.title or "Unknown"
            author = work.meta.get("authors", ["Unknown"])[0] if work.meta else "Unknown"

            start_cover_processing(manifestation.id, canonical_isbn, title, author)

        db.session.commit()
    else:
        # Update existing manifestation
        manifestation.update_meta(**metadata)
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
        return jsonify({"error": f"Manifestation not found for ISBN = {isbn}"}), 404

    metadata = request.get_json(silent=True)
    if not isinstance(metadata, dict):
        return _invalid_json_payload_response()

    if metadata:
        # Update the manifestation's metadata
        manifestation.update_meta(**metadata)

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
        return jsonify({"error": f"Manifestation not found for ISBN = {isbn}"}), 404

    items = Item.query.filter_by(manifestation_id=manifestation.id).all()

    if not items:
        return jsonify({"error": f"No items found for ISBN = {isbn}"}), 404

    return jsonify({"ids": [item.id for item in items]})


@api_bp.route("/item/<isbn>", methods=["POST"])
def add_item(isbn: str):
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    if not manifestation:
        lookup_response = lookup_isbn(isbn)
        if isinstance(lookup_response, tuple):
            status_code = lookup_response[1] if len(lookup_response) > 1 else 404
            if status_code != 200:
                return jsonify({"error": f"Manifestation not found for ISBN = {isbn}"}), 404
        manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    metadata = request.get_json(silent=True)

    if metadata:
        manifestation.update_meta(**metadata)
        if manifestation.expression and manifestation.expression.work:
            if "Title" in metadata:
                manifestation.expression.work.title = metadata["Title"]
            if "Authors" in metadata:
                if not manifestation.expression.work.meta:
                    manifestation.expression.work.meta = {}
                work_meta = dict(manifestation.expression.work.meta)
                work_meta["authors"] = metadata["Authors"]
                manifestation.expression.work.meta = work_meta

    # --- Ensure a valid User exists to assign ownership ---
    user = User.query.first()
    if not user:
        user = User(email="api_default@iqoqo.local", display_name="API Default")
        db.session.add(user)
        db.session.flush()

    # Create new item using the valid UUID
    item = Item(manifestation_id=manifestation.id, owner_id=user.id, status="available", meta={})

    db.session.add(item)
    db.session.commit()

    return jsonify({"item_id": item.id})


@api_bp.route("/manifestations/<int:manifestation_id>/cover", methods=["POST"])
def upload_cover(manifestation_id):  # pylint: disable=R0911
    """Handles manual user photo uploads for a manifestation."""
    if "cover" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["cover"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Validate extension
    allowed_extensions = {"png", "jpg", "jpeg", "webp"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, webp"}), 400

    # Validate size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    if request.content_length and request.content_length > max_size:
        return jsonify({"error": "File too large. Max size: 10MB"}), 413

    file.seek(0, os.SEEK_END)
    if file.tell() > max_size:
        return jsonify({"error": "File too large. Max size: 10MB"}), 413
    file.seek(0)

    # Verify image content
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except (OSError, SyntaxError):
        return jsonify({"error": "Invalid or corrupted image file"}), 400

    manifestation = Manifestation.query.get_or_404(manifestation_id)
    isbn = manifestation.isbn13 or f"item_{manifestation_id}"

    filename = secure_filename(f"{isbn}_raw.jpg")
    filepath = os.path.join(RAW_DIR, filename)
    file.save(filepath)

    # Set status to processing
    manifestation.update_meta(cover_status="processing")
    db.session.commit()

    # Get Title/Author from related Expression/Work
    work = manifestation.expression.work if (manifestation.expression and manifestation.expression.work) else None
    title = work.title if work else "Unknown Title"
    author = work.meta.get("authors", ["Unknown Author"])[0] if (work and work.meta and work.meta.get("authors")) else "Unknown Author"

    start_cover_processing(manifestation.id, isbn, title, author, user_image_path=filepath)

    return jsonify({"message": "Cover upload processing started"}), 202


@api_bp.route("/manifestations/<int:manifestation_id>/regenerate-cover", methods=["POST"])
@require_auth
@require_permission("regenerate:cover")
def regenerate_cover(manifestation_id: int):
    """Force regeneration of a cover for a manifestation."""
    manif = Manifestation.query.get_or_404(manifestation_id)

    # Reset status
    manif.update_meta(cover_status="pending")
    db.session.commit()

    # Launch background pipeline (API lookup → LLM generation)
    work = manif.expression.work if manif.expression else None
    title = work.title if work else "Unknown"
    author = work.meta.get("authors", ["Unknown"])[0] if work and work.meta else "Unknown"
    isbn = manif.isbn13 or str(manif.id)

    # Extract extra metadata for the LLM
    meta = manif.meta or {}
    description = meta.get("Description", "")
    categories = meta.get("Categories", [])
    genre = ", ".join(categories) if isinstance(categories, list) else str(categories)
    start_cover_processing(manif.id, isbn, title, author, description=description, genre=genre)

    return jsonify({"message": "Cover regeneration scheduled", "status": "pending"}), 202


# =============================================================================
# Admin API Endpoints
# =============================================================================


@api_bp.route("/manifestations/<int:manifestation_id>/refetch-metadata", methods=["POST"])
@require_auth
@require_permission("refetch:metadata")
def refetch_metadata(manifestation_id: int):
    """Force refetch metadata from upstream providers."""
    manif = Manifestation.query.get_or_404(manifestation_id)

    if not manif.isbn13:
        return jsonify({"success": False, "data": None, "error": "No ISBN to fetch metadata for"}), 400

    # Canonicalize ISBN before lookup
    canonical_isbn = isbn_utils.canonicalize_isbn(manif.isbn13)
    if not canonical_isbn:
        return jsonify({"success": False, "data": None, "error": "Invalid ISBN"}), 400

    metadata = isbn_utils.fetch_isbn_metadata(canonical_isbn)

    if not metadata:
        return jsonify({"success": False, "data": None, "error": "No upstream metadata found"}), 404

    # Merge metadata into Manifestation
    manif.update_meta(**metadata)

    # Update Work details if available
    if manif.expression and manif.expression.work:
        if "Title" in metadata:
            manif.expression.work.title = metadata["Title"]
        if "Authors" in metadata:
            work_meta = dict(manif.expression.work.meta or {})
            work_meta["authors"] = metadata["Authors"]
            manif.expression.work.meta = work_meta

    db.session.commit()
    return jsonify({"success": True, "data": {"id": manif.id}, "error": None})


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


@api_bp.route("/scan", methods=["POST"])
@require_auth
def scan_barcode():
    """
    Handles Scenarios 1 & 2:
    - Scans for existing manifestation.
    - If missing, fetches metadata and creates Work->Expr->Manifestation.
    - Creates user Item.
    """
    data = request.get_json()
    barcode = data.get("barcode")

    if not barcode:
        return jsonify({"error": "Barcode is required"}), 400

    # 1. Check if Manifestation already exists locally
    # Assuming ISBN is stored in the meta JSON or a dedicated column. Adjust to your specific DB schema.
    manifestation = Manifestation.query.filter(Manifestation.meta.op("->>")("isbn") == barcode).first()

    # Scenario 1: No manifestation exists -> Fetch external metadata and build FRBR tree
    if not manifestation:
        try:
            # You will need to ensure this function exists in app/core/ingest.py using app/utils/isbn.py
            manifestation = IngestService.ingest_from_isbn(barcode)
        except ValueError as e:
            return jsonify({"error": f"Invalid barcode or ISBN: {str(e)}"}), 400
        except ConnectionError as e:
            return jsonify({"error": f"Network error while fetching metadata: {str(e)}"}), 503
        except Exception as e:  # pylint: disable=broad-except
            return jsonify({"error": f"Failed to find or ingest metadata for barcode: {str(e)}"}), 404

    if not manifestation:
        return jsonify({"error": "Could not resolve barcode"}), 404

    # Scenario 2 & 1 Conclusion: Create the Item for the user
    new_item = Item(manifestation_id=manifestation.id, owner_id=request.user_id, status="available")  # Default status
    db.session.add(new_item)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Item successfully added to your collection",
                "item_id": new_item.id,
                "manifestation_id": manifestation.id,
                "title": manifestation.title,
                "is_new_manifestation": not manifestation,  # conceptually true if we just ingested it
            }
        ),
        201,
    )


@api_bp.route("/discover", methods=["GET"])
@require_auth
def get_global_manifestations():
    """
    Scenario 3: Fetch all manifestations in the local node, independent of user ownership.
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    pagination = Manifestation.query.order_by(Manifestation.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    result = []
    for m in pagination.items:
        result.append(
            {
                "id": m.id,
                "title": m.title,
                "cover_url": m.meta.get("cover_url"),
                "author": m.expression.work.author if m.expression and m.expression.work else "Unknown",
            }
        )

    return jsonify({"manifestations": result, "total": pagination.total, "pages": pagination.pages, "current_page": page})


@api_bp.route("/manifestations/recent", methods=["GET"])
def get_recent_manifestations():
    """Get the most recently added manifestations across the entire instance (public).

    Query param: `limit` (int, default 10)
    """
    try:
        limit = request.args.get("limit", 10, type=int)

        recent = (
            Manifestation.query.options(selectinload(Manifestation.expression).selectinload(Expression.work))
            .order_by(Manifestation.id.desc())
            .limit(limit)
            .all()
        )

        result = []
        for m in recent:
            work = m.expression.work if (m.expression and m.expression.work) else None
            title = work.title if work else (m.meta.get("Title") if m.meta else None)
            authors = work.meta.get("authors", []) if (work and work.meta) else (m.meta.get("Authors") if m.meta else [])
            author = authors[0] if authors else None

            result.append(
                {
                    "id": m.id,
                    "title": title,
                    "cover_path": m.cover_path,
                    "author": author,
                }
            )

        return jsonify({"success": True, "data": result, "error": None}), 200
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        return jsonify({"success": False, "data": None, "error": str(e)}), 500
