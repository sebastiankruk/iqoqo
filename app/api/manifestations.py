"""Handles Global Catalog, ISBN parsing, Covers, and Fresh Arrivals"""

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
import os
from typing import Any

from flask import current_app, jsonify, request
from PIL import Image
from sqlalchemy import text
from sqlalchemy.orm import selectinload
from werkzeug.utils import secure_filename

import app.utils.isbn as isbn_utils
from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import require_auth, require_permission
from app.db.models import Expression, Item, Manifestation, Work, db
from app.utils.covers import RAW_DIR, process_fast_cover, start_cover_processing


@api_bp.route("/manifestations", methods=["GET"])
def get_manifestations():
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
                "cover_url": m.cover_url,
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
        "cover_url": m.cover_url,
        "cover_status": m.meta.get("cover_status") if m.meta else None,
        "user_owns": user_owns,
    }
    return jsonify({"success": True, "data": data, "error": None})


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
                    "cover_url": m.cover_url,
                    "cover_status": m.meta.get("cover_status") if m.meta else None,
                    "meta": m.meta,
                    "author": author,
                    "authors": authors,
                }
            )

        return jsonify({"success": True, "data": result, "error": None}), 200
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
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
            except (db.exc.SQLAlchemyError, db.exc.DBAPIError):
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
        return invalid_json_payload_response()

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


@api_bp.route("/manifestations/<int:manifestation_id>/refetch-metadata", methods=["POST"])
@require_auth
@require_permission("refetch:metadata")
def refetch_metadata(manifestation_id: int):
    manif = db.get_or_404(Manifestation, manifestation_id)
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


@api_bp.route("/manifestations/<int:manifestation_id>/cover", methods=["POST"])
def upload_cover(manifestation_id):
    if "cover" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["cover"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    allowed_extensions = {"png", "jpg", "jpeg", "webp"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, webp"}), 400

    max_size = 10 * 1024 * 1024
    file.seek(0, os.SEEK_END)
    actual_size = file.tell()
    file.seek(0)

    if (request.content_length and request.content_length > max_size) or actual_size > max_size:
        return jsonify({"error": "File too large. Max size: 10MB"}), 413

    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
    except (OSError, SyntaxError):
        return jsonify({"error": "Invalid or corrupted image file"}), 400

    manifestation = db.get_or_404(Manifestation, manifestation_id)
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
    manif = db.get_or_404(Manifestation, manifestation_id)
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


@api_bp.route("/manifestations/<int:manifestation_id>", methods=["DELETE"])
@require_auth
@require_permission("delete:manifestation")
def delete_manifestation(manifestation_id: int):
    manif = db.session.get(Manifestation, manifestation_id)
    if not manif:
        return jsonify({"success": False, "data": None, "error": "Manifestation not found"}), 404

    try:
        db.session.delete(manif)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": manifestation_id}, "error": None})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        return jsonify({"success": False, "data": None, "error": str(e)}), 500
