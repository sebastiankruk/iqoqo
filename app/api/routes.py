"""Defines the API endpoints for the application."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

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
from app.core.ingest import IngestService
from app.db.models import Expression, Item, Manifestation, User, Work, db
from app.utils.covers import COVERS_DIR, RAW_DIR, process_fast_cover, start_cover_processing

from .core import api_bp


def _invalid_json_payload_response():
    """Return a standardized 400 response for absent/invalid JSON payloads."""
    return jsonify({"success": False, "data": None, "error": "Invalid or missing JSON payload"}), 400


@api_bp.route("/static/covers/<path:filename>", methods=["GET"])
def serve_cover(filename: str):
    return send_from_directory(COVERS_DIR, filename)


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "iqoqo-api", "version": Config.VERSION, "api_version": "v1"})


@api_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    stats = DataManager.get_stats()
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
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/items", methods=["GET"])
@require_auth
def get_items():
    """Get all items with pagination support."""
    user_id = getattr(request, "user_id", None)
    if not user_id:
        return (
            jsonify({"success": False, "data": [], "meta": {"page": 1, "limit": 20, "total": 0, "pages": 0}, "error": "Unauthorized"}),
            401,
        )

    page_param = request.args.get("page", "1")
    limit_param = request.args.get("limit", "20")
    statuses_filter = request.args.get("statuses", None)
    q = request.args.get("q", "").strip()

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    if page < 1 or limit < 1:
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    offset = (page - 1) * limit

    if q:
        w_tsvector_expr = "w.fts_simple"
        m_tsvector_expr = "m.fts_simple"
        tsquery_expr = "websearch_to_tsquery('simple', :q)"

        params = {"q": q, "limit": limit, "offset": offset, "user_id": user_id}
        statuses_sql = " AND i.owner_id = :user_id"

        if statuses_filter:
            statuses_list = tuple(s.strip() for s in statuses_filter.split(",") if s.strip())
            params["statuses"] = statuses_list
            statuses_sql += " AND i.status IN :statuses"

        try:
            count_sql = f"""
            SELECT count(*) FROM manifestations m
            JOIN expressions e ON e.id = m.expression_id
            JOIN works w ON w.id = e.work_id
            JOIN items i ON i.manifestation_id = m.id
            WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr})
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
            JOIN items i ON i.manifestation_id = m.id
            WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr})
            {statuses_sql}
            ORDER BY rank DESC
            LIMIT :limit OFFSET :offset
            """

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
            if db.engine.dialect.name == "postgresql":
                return jsonify({"success": False, "data": None, "error": "Search backend error"}), 500

            pattern = f"%{q}%"
            base_query = (
                db.session.query(Item, Manifestation, Expression, Work)
                .select_from(Manifestation)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
                .join(Item, Item.manifestation_id == Manifestation.id)
                .filter(Item.owner_id == user_id)
                .filter((Work.title.ilike(pattern)) | (Manifestation.isbn13.ilike(pattern)))
            )

            if statuses_filter:
                statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()]
                base_query = base_query.filter(Item.status.in_(statuses_list))

            total = base_query.count()
            results = base_query.offset(offset).limit(limit).all()

            items_data = []
            for item, manifestation, _expression, work in results:
                w_meta = work.meta if work and work.meta else {}
                m_meta = manifestation.meta if manifestation and manifestation.meta else {}

                items_data.append(
                    {
                        "id": item.id,
                        "owner_id": item.owner_id,
                        "status": item.status,
                        "manifestation_id": manifestation.id,
                        "isbn": manifestation.isbn13,
                        "title": work.title,
                        "cover_path": manifestation.cover_path,
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
                "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
                "error": None,
            }
        )

    # Standard collection mode
    query = Item.query.options(selectinload(Item.manifestation).selectinload(Manifestation.expression).selectinload(Expression.work))
    query = query.filter(Item.owner_id == user_id)
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
        authors: list[str] = []
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
            "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
            "error": None,
        }
    )


@api_bp.route("/items/<int:item_id>", methods=["GET"])
def get_item_detail(item_id: int):
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
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    if manifestation and manifestation.meta and manifestation.meta.get("Title"):
        return jsonify(**manifestation.meta)

    if manifestation and manifestation.expression and manifestation.expression.work:
        work = manifestation.expression.work
        work_metadata = {
            "Title": work.title or "",
            "Authors": work.meta.get("authors", []) if work.meta else [],
        }
        if work_metadata["Title"]:
            manifestation.update_meta(**work_metadata)
            try:
                db.session.commit()
            except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
                db.session.rollback()
            return jsonify(**work_metadata)

    canonical_isbn = isbn_utils.canonicalize_isbn(isbn)
    if not canonical_isbn:
        return jsonify({"success": False, "data": None, "error": f"Invalid ISBN = {isbn}"}), 400

    metadata: dict[str, Any] | None = isbn_utils.fetch_isbn_metadata(canonical_isbn)
    if not metadata:
        return jsonify({"success": False, "data": None, "error": f"Metadata not found for ISBN = {canonical_isbn}"}), 404

    if not manifestation:
        work = Work(title=metadata["Title"], meta={"authors": metadata["Authors"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13=canonical_isbn, meta=metadata)
        db.session.add(manifestation)
        db.session.commit()

        found_cover = process_fast_cover(manifestation, canonical_isbn)
        if not found_cover:
            manifestation.update_meta(cover_status="pending")
            title = work.title or "Unknown"
            author = work.meta.get("authors", ["Unknown"])[0] if work.meta else "Unknown"
            start_cover_processing(manifestation.id, canonical_isbn, title, author)
        db.session.commit()
    else:
        manifestation.update_meta(**metadata)
        if manifestation.expression and manifestation.expression.work:
            manifestation.expression.work.title = metadata["Title"]
            if not manifestation.expression.work.meta:
                manifestation.expression.work.meta = {}
            manifestation.expression.work.meta["authors"] = metadata["Authors"]
        db.session.commit()

    return jsonify(**metadata)


@api_bp.route("/isbn/<isbn>", methods=["POST"])
def update_manifestation(isbn: str):
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    if not manifestation:
        return jsonify({"error": f"Manifestation not found for ISBN = {isbn}"}), 404

    metadata = request.get_json(silent=True)
    if not isinstance(metadata, dict):
        return _invalid_json_payload_response()

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
        db.session.commit()
        return jsonify({"status": "ok"})

    return jsonify({"error": "No metadata provided"}), 400


@api_bp.route("/item/<isbn>", methods=["GET"])
def get_items_by_isbn(isbn: str):
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

    user = User.query.first()
    if not user:
        user = User(email="api_default@iqoqo.local", display_name="API Default")
        db.session.add(user)
        db.session.flush()

    item = Item(manifestation_id=manifestation.id, owner_id=user.id, status="available", meta={})
    db.session.add(item)
    db.session.commit()

    return jsonify({"item_id": item.id})


@api_bp.route("/manifestations/<int:manifestation_id>/cover", methods=["POST"])
def upload_cover(manifestation_id):  # pylint: disable=R0911
    if "cover" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["cover"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    allowed_extensions = {"png", "jpg", "jpeg", "webp"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, webp"}), 400

    max_size = 10 * 1024 * 1024
    if request.content_length and request.content_length > max_size:
        return jsonify({"error": "File too large. Max size: 10MB"}), 413

    file.seek(0, os.SEEK_END)
    if file.tell() > max_size:
        return jsonify({"error": "File too large. Max size: 10MB"}), 413
    file.seek(0)

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

    manifestation.update_meta(cover_status="processing")
    db.session.commit()

    work = manifestation.expression.work if (manifestation.expression and manifestation.expression.work) else None
    title = work.title if work else "Unknown Title"
    author = work.meta.get("authors", ["Unknown Author"])[0] if (work and work.meta and work.meta.get("authors")) else "Unknown Author"

    start_cover_processing(manifestation.id, isbn, title, author, user_image_path=filepath)

    return jsonify({"message": "Cover upload processing started"}), 202


@api_bp.route("/manifestations/<int:manifestation_id>/regenerate-cover", methods=["POST"])
@require_auth
@require_permission("regenerate:cover")
def regenerate_cover(manifestation_id: int):
    manif = Manifestation.query.get_or_404(manifestation_id)
    manif.update_meta(cover_status="pending")
    db.session.commit()

    work = manif.expression.work if manif.expression else None
    title = work.title if work else "Unknown"
    author = work.meta.get("authors", ["Unknown"])[0] if work and work.meta else "Unknown"
    isbn = manif.isbn13 or str(manif.id)

    meta = manif.meta or {}
    description = meta.get("Description", "")
    categories = meta.get("Categories", [])
    genre = ", ".join(categories) if isinstance(categories, list) else str(categories)
    start_cover_processing(manif.id, isbn, title, author, description=description, genre=genre)

    return jsonify({"message": "Cover regeneration scheduled", "status": "pending"}), 202


@api_bp.route("/manifestations", methods=["GET"])
def get_manifestations():
    """Get all manifestations (Global Library) with pagination and ownership status."""
    user_id = getattr(request, "user_id", None)

    page_param = request.args.get("page", "1")
    limit_param = request.args.get("limit", "20")
    q = request.args.get("q", "").strip()

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    if page < 1 or limit < 1:
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    offset = (page - 1) * limit

    if q:
        w_tsvector_expr = "w.fts_simple"
        m_tsvector_expr = "m.fts_simple"
        tsquery_expr = "websearch_to_tsquery('simple', :q)"
        params = {"q": q, "limit": limit, "offset": offset}

        try:
            count_sql = f"""
            SELECT count(*) FROM manifestations m
            JOIN expressions e ON e.id = m.expression_id
            JOIN works w ON w.id = e.work_id
            WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr})
            """

            rows_sql = f"""
            SELECT m.id, ts_rank({w_tsvector_expr} || {m_tsvector_expr}, {tsquery_expr}) as rank
            FROM manifestations m
            JOIN expressions e ON e.id = m.expression_id
            JOIN works w ON w.id = e.work_id
            WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr})
            ORDER BY rank DESC
            LIMIT :limit OFFSET :offset
            """

            count_stmt = text(count_sql)
            rows_stmt = text(rows_sql)
            total = int(db.session.execute(count_stmt, params).scalar() or 0)
            result_ids = [row[0] for row in db.session.execute(rows_stmt, params).all()]

            if result_ids:
                manifestations_unordered = (
                    Manifestation.query.options(selectinload(Manifestation.expression).selectinload(Expression.work))
                    .filter(Manifestation.id.in_(result_ids))
                    .all()
                )

                m_dict = {m.id: m for m in manifestations_unordered}
                manifestations = [m_dict[m_id] for m_id in result_ids if m_id in m_dict]
            else:
                manifestations = []

        except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as exc:
            current_app.logger.exception("Error during FTS manifestation search, attempting fallback", exc_info=exc)
            if db.engine.dialect.name == "postgresql":
                return jsonify({"success": False, "data": None, "error": "Search backend error"}), 500

            pattern = f"%{q}%"
            base_query = (
                db.session.query(Manifestation)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
                .filter((Work.title.ilike(pattern)) | (Manifestation.isbn13.ilike(pattern)))
            )
            total = base_query.count()
            manifestations = base_query.offset(offset).limit(limit).all()
    else:
        query = Manifestation.query.options(selectinload(Manifestation.expression).selectinload(Expression.work)).order_by(
            Manifestation.id.desc()
        )
        total = query.count()
        manifestations = query.offset(offset).limit(limit).all()

    owned_manifestation_ids = set()
    if user_id and manifestations:
        manifestation_ids = [m.id for m in manifestations]
        owned_ids_query = (
            db.session.query(Manifestation.id)
            .join(Item, Item.manifestation_id == Manifestation.id)
            .filter(Item.owner_id == user_id, Manifestation.id.in_(manifestation_ids))
            .distinct()
        )
        owned_manifestation_ids = {str(row[0]) for row in owned_ids_query.all()}

    data = []
    for m in manifestations:
        work_title = ""
        authors: list[str] = []
        if m.expression and m.expression.work:
            work = m.expression.work
            work_title = work.title or ""
            authors = work.meta.get("authors", []) if work.meta else []

        user_owns = False
        if user_id:
            user_owns = str(m.id) in owned_manifestation_ids

        # FIX: Extract year gracefully from Date column or meta fallback
        resolved_year = m.publication_date.year if getattr(m, "publication_date", None) else (m.meta.get("Year") if m.meta else None)

        data.append(
            {
                "id": m.id,
                "expression_id": m.expression_id,
                "isbn13": m.isbn13,
                "publisher": m.publisher,
                "year": resolved_year,
                "meta": m.meta,
                "title": work_title,
                "authors": authors,
                "cover_path": m.cover_path,
                "cover_status": m.meta.get("cover_status") if m.meta else None,
                "user_owns": user_owns,
            }
        )

    return jsonify(
        {
            "success": True,
            "data": data,
            "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
            "error": None,
        }
    )


@api_bp.route("/manifestations/<int:manifestation_id>", methods=["GET"])
def get_manifestation_detail(manifestation_id: int):
    """Get a single global manifestation by ID."""
    user_id = getattr(request, "user_id", None)
    m = db.session.get(Manifestation, manifestation_id)

    if not m:
        return jsonify({"success": False, "data": None, "error": "Manifestation not found"}), 404

    work_title = ""
    authors: list[str] = []
    if m.expression and m.expression.work:
        work = m.expression.work
        work_title = work.title or ""
        authors = work.meta.get("authors", []) if work.meta else []

    user_owns = False
    if user_id:
        owned_item = Item.query.filter_by(manifestation_id=m.id, owner_id=user_id).first()
        if owned_item:
            user_owns = True

    # FIX: Extract year gracefully from Date column or meta fallback
    resolved_year = m.publication_date.year if getattr(m, "publication_date", None) else (m.meta.get("Year") if m.meta else None)

    data = {
        "id": m.id,
        "expression_id": m.expression_id,
        "isbn13": m.isbn13,
        "publisher": m.publisher,
        "year": resolved_year,
        "meta": m.meta,
        "title": work_title,
        "authors": authors,
        "cover_path": m.cover_path,
        "cover_status": m.meta.get("cover_status") if m.meta else None,
        "user_owns": user_owns,
    }

    return jsonify({"success": True, "data": data, "error": None})


# =============================================================================
# Admin API Endpoints
# =============================================================================


@api_bp.route("/manifestations/<int:manifestation_id>/refetch-metadata", methods=["POST"])
@require_auth
@require_permission("refetch:metadata")
def refetch_metadata(manifestation_id: int):
    manif = Manifestation.query.get_or_404(manifestation_id)

    if not manif.isbn13:
        return jsonify({"success": False, "data": None, "error": "No ISBN to fetch metadata for"}), 400

    canonical_isbn = isbn_utils.canonicalize_isbn(manif.isbn13)
    if not canonical_isbn:
        return jsonify({"success": False, "data": None, "error": "Invalid ISBN"}), 400

    metadata = isbn_utils.fetch_isbn_metadata(canonical_isbn)

    if not metadata:
        return jsonify({"success": False, "data": None, "error": "No upstream metadata found"}), 404

    manif.update_meta(**metadata)

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
    stats = DataManager.get_stats()
    return jsonify(stats)


@api_bp.route("/admin/export", methods=["GET"])
def export_data():
    try:
        data = DataManager.export_all()
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
    try:
        clear_existing = request.args.get("clear_existing", "false").lower() == "true"

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
    data = request.get_json()
    barcode = data.get("barcode")

    if not barcode:
        return jsonify({"error": "Barcode is required"}), 400

    manifestation = Manifestation.query.filter(Manifestation.meta.op("->>")("isbn") == barcode).first()

    if not manifestation:
        try:
            manifestation = IngestService.ingest_from_isbn(barcode)
        except ValueError as e:
            return jsonify({"error": f"Invalid barcode or ISBN: {str(e)}"}), 400
        except ConnectionError as e:
            return jsonify({"error": f"Network error while fetching metadata: {str(e)}"}), 503
        except Exception as e:
            return jsonify({"error": f"Failed to find or ingest metadata for barcode: {str(e)}"}), 404

    if not manifestation:
        return jsonify({"error": "Could not resolve barcode"}), 404

    new_item = Item(manifestation_id=manifestation.id, owner_id=request.user_id, status="available")
    db.session.add(new_item)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Item successfully added to your collection",
                "item_id": new_item.id,
                "manifestation_id": manifestation.id,
                "title": manifestation.title,
                "is_new_manifestation": not manifestation,
            }
        ),
        201,
    )


@api_bp.route("/manifestations/recent", methods=["GET"])
def get_recent_manifestations():
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
            authors: list[str] = work.meta.get("authors", []) if (work and work.meta) else (m.meta.get("Authors", []) if m.meta else [])
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
