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
from datetime import UTC, datetime
from typing import Any

from flask import Response, g, jsonify, request
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.utils import secure_filename

import app.utils.isbn as isbn_utils
from app.api.core import api_bp, invalid_json_payload_response
from app.api.decorators import optional_auth, require_auth, require_permission
from app.api.filters import apply_genre_filter, apply_statuses_filter
from app.core.permissions import PermissionName
from app.db.models import Expression, ImageScan, Item, Manifestation, User, Work, db
from app.utils.covers import RAW_DIR, process_fast_cover, start_cover_processing
from app.utils.images import save_upload_image, validate_upload_file


@api_bp.route("/manifestations", methods=["GET"])
@optional_auth
def get_manifestations() -> tuple[Response, int]:
    user_id = getattr(g, "user_id", None)
    page_param = request.args.get("page", "1")
    limit_param = request.args.get("limit", "20")
    q = request.args.get("q", "").strip()
    category_filter = request.args.get("category")
    format_filter = request.args.get("format")
    category_list = [c.strip() for c in category_filter.split(",") if c.strip()] if category_filter else None
    format_list_raw = [f.strip() for f in format_filter.split(",") if f.strip()] if format_filter else None
    from app.core.format_normalizer import expand_format_filter

    format_list = expand_format_filter(format_list_raw)
    missing_cover = request.args.get("missing_cover") == "true"
    missing_id = request.args.get("missing_id") == "true"
    tags_filter = request.args.get("tags")
    collections_filter = request.args.get("collections")
    genres_filter = request.args.get("genres")
    publishers_filter = request.args.get("publishers")
    statuses_filter = request.args.get("statuses")

    tags_list = [t.strip() for t in tags_filter.split(",") if t.strip()] if tags_filter else None
    collections_list = [c.strip() for c in collections_filter.split(",") if c.strip()] if collections_filter else None
    genres_list = [gen.strip() for gen in genres_filter.split(",") if gen.strip()] if genres_filter else None
    publishers_list = [p.strip() for p in publishers_filter.split(",") if p.strip()] if publishers_filter else None
    statuses_list = [s.strip() for s in statuses_filter.split(",") if s.strip()] if statuses_filter else None

    try:
        page = int(page_param)
        limit = int(limit_param)
    except (TypeError, ValueError):
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    if page < 1 or limit < 1:
        return jsonify({"success": False, "data": None, "error": "Invalid pagination parameters"}), 400

    offset = (page - 1) * limit

    if q:
        from app.core.search_service import SearchService

        total, result_ids = SearchService.search_manifestations(
            q,
            limit,
            offset,
            category=category_list,
            format_filter=format_list,
            missing_cover=missing_cover,
            missing_id=missing_id,
            tags=tags_list,
            collections=collections_list,
            genres=genres_list,
            publishers=publishers_list,
            statuses=statuses_list,
            user_id=user_id,
        )

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
    else:
        query = (
            Manifestation.query.options(selectinload(Manifestation.expression).selectinload(Expression.work)).join(Expression).join(Work)
        )

        if category_list:
            query = query.filter(Expression.content_type.in_(category_list))
        if format_list:
            query = query.filter(Manifestation.meta["format"].as_string().in_(format_list))
        if missing_cover:
            query = query.filter(
                db.and_(
                    db.or_(Manifestation.cover_url.is_(None), Manifestation.cover_url == ""),
                    db.or_(
                        Manifestation.meta["cover_url"].as_string().is_(None),
                        Manifestation.meta["cover_url"].as_string() == "",
                    ),
                )
            )
        if missing_id:
            query = query.filter(
                db.and_(
                    db.or_(Manifestation.isbn13.is_(None), Manifestation.isbn13 == ""),
                    db.or_(Manifestation.upc.is_(None), Manifestation.upc == ""),
                    db.or_(Manifestation.ean.is_(None), Manifestation.ean == ""),
                    db.or_(
                        Manifestation.meta["barcode"].as_string().is_(None),
                        Manifestation.meta["barcode"].as_string() == "",
                    ),
                    db.or_(
                        Manifestation.meta["catalog_number"].as_string().is_(None),
                        Manifestation.meta["catalog_number"].as_string() == "",
                    ),
                )
            )

        # Apply taxonomy filters
        has_item_joined = False
        if tags_list:
            if not has_item_joined:
                query = query.join(Item, Manifestation.id == Item.manifestation_id)
                has_item_joined = True
            from app.db.models import ItemTag, Tag

            query = query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
            tags_conditions = [Tag.name.ilike(f.strip()) for f in tags_list]
            query = query.filter(db.or_(*tags_conditions))

        if collections_list:
            if not has_item_joined:
                query = query.join(Item, Manifestation.id == Item.manifestation_id)
                has_item_joined = True
            from app.db.models import UserCollection, UserCollectionItem

            query = query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
                UserCollection, UserCollectionItem.collection_id == UserCollection.id
            )
            coll_conditions = [UserCollection.name.ilike(c.strip()) for c in collections_list]
            query = query.filter(db.or_(*coll_conditions))
            if user_id:
                query = query.filter(UserCollection.owner_id == user_id)

        if genres_list:
            query = apply_genre_filter(query, genres_list)

        if publishers_list:
            pubs_conditions = []
            for p in publishers_list:
                p_term = f"%{p.strip()}%"
                pubs_conditions.append(
                    db.or_(
                        Manifestation.publisher.ilike(p_term),
                        Manifestation.meta["Publisher"].as_string().ilike(p_term),
                        Manifestation.meta["publisher"].as_string().ilike(p_term),
                        db.and_(Expression.content_type == "music", Manifestation.meta["label"].as_string().ilike(p_term)),
                    )
                )
            query = query.filter(db.or_(*pubs_conditions))

        if statuses_list and user_id:
            if not has_item_joined:
                query = query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == user_id))
                has_item_joined = True
            query = apply_statuses_filter(query, statuses_list, user_id=user_id)

        query = query.order_by(Manifestation.id.desc())
        total = query.count()
        manifestations = query.offset(offset).limit(limit).all()

    owned_manifestation_map = {}
    if user_id and manifestations:
        manifestation_ids = [m.id for m in manifestations]
        owned_items_query = db.session.query(Item.manifestation_id, Item.id).filter(
            Item.owner_id == user_id, Item.manifestation_id.in_(manifestation_ids)
        )
        for m_id, item_id in owned_items_query.all():
            owned_manifestation_map[m_id] = item_id

    data = []
    for m in manifestations:
        work_title = ""
        authors: list[str] = []
        if m.expression and m.expression.work:
            work = m.expression.work
            work_title = work.title or ""
            authors = work.meta.get("authors", []) if work.meta else []

        user_owns = False
        item_id = None
        if user_id:
            user_owns = m.id in owned_manifestation_map
            item_id = owned_manifestation_map.get(m.id)

        resolved_year = m.publication_date.year if getattr(m, "publication_date", None) else (m.meta.get("Year") if m.meta else None)

        data.append(
            {
                "id": m.id,
                "expression_id": m.expression_id,
                "work_id": m.expression.work.id if (m.expression and m.expression.work) else None,
                "container_work_id": (
                    m.expression.work.member_of[0].container_work_id
                    if (m.expression and m.expression.work and m.expression.work.member_of)
                    else None
                ),
                "isbn13": m.isbn13,
                "publisher": m.publisher,
                "year": resolved_year,
                "meta": m.meta,
                "title": work_title,
                "authors": authors,
                "cover_url": m.cover_url,
                "cover_status": m.meta.get("cover_status") if m.meta else None,
                "user_owns": user_owns,
                "item_id": item_id,
                "content_type": m.expression.content_type if m.expression else None,
            }
        )

    return (
        jsonify(
            {
                "success": True,
                "data": data,
                "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if limit > 0 else 0},
                "error": None,
            }
        ),
        200,
    )


@api_bp.route("/manifestations/<int:manifestation_id>", methods=["GET"])
@optional_auth
def get_manifestation_detail(manifestation_id: int) -> tuple[Response, int]:
    user_id = getattr(g, "user_id", None)
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
    item_id: int | None = None
    wishlist_item_id: int | None = None
    owner_count = 0
    if user_id:
        from app.db.models import UserWorkIntent

        owned_item = Item.query.filter_by(manifestation_id=m.id, owner_id=user_id).first()
        if owned_item:
            if owned_item.collection_status == "wish_list":
                wishlist_item_id = owned_item.id
            else:
                user_owns = True
                item_id = owned_item.id

        if not user_owns and not wishlist_item_id and m.expression and m.expression.work:
            intent = UserWorkIntent.query.filter_by(user_id=user_id, work_id=m.expression.work.id).first()
            if intent:
                wishlist_item_id = -intent.id

    owner_count = Item.query.filter(Item.manifestation_id == m.id, Item.is_hidden.is_(False)).count()

    resolved_year = m.publication_date.year if getattr(m, "publication_date", None) else (m.meta.get("Year") if m.meta else None)

    data = {
        "id": m.id,
        "expression_id": m.expression_id,
        "work_id": m.expression.work.id if (m.expression and m.expression.work) else None,
        "container_work_id": (
            m.expression.work.member_of[0].container_work_id
            if (m.expression and m.expression.work and m.expression.work.member_of)
            else None
        ),
        "isbn13": m.isbn13,
        "upc": m.upc,
        "ean": m.ean,
        "publisher": m.publisher,
        "year": resolved_year,
        "meta": m.meta,
        "title": work_title,
        "authors": authors,
        "cover_url": m.cover_url,
        "cover_status": m.meta.get("cover_status") if m.meta else None,
        "user_owns": user_owns,
        "item_id": item_id,
        "wishlist_item_id": wishlist_item_id,
        "owner_count": owner_count,
        "content_type": m.expression.content_type if m.expression else None,
    }
    return jsonify({"success": True, "data": data, "error": None}), 200


@api_bp.route("/manifestations/recent", methods=["GET"])
def get_recent_manifestations() -> tuple[Response, int]:
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
                    "cover_url": m.cover_url or (m.meta.get("cover_url") if m.meta else None),
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
def lookup_isbn(isbn: str) -> tuple[Response, int]:
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    if manifestation and manifestation.meta and manifestation.meta.get("Title"):
        return jsonify(**manifestation.meta), 200

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
            return jsonify(**work_metadata), 200

    canonical_isbn = isbn_utils.canonicalize_isbn(isbn)
    if not canonical_isbn:
        return jsonify({"success": False, "data": None, "error": f"Invalid ISBN = {isbn}"}), 400

    metadata: dict[str, Any] | None = isbn_utils.fetch_isbn_metadata(canonical_isbn)
    if not metadata:
        return jsonify({"success": False, "data": None, "error": f"Metadata not found for ISBN = {canonical_isbn}"}), 404

    if not manifestation:
        from app.core.ingest import _extract_genres

        work_genres = _extract_genres(metadata)
        work_meta: dict[str, object] = {"authors": metadata.get("Authors", [])}
        if work_genres:
            work_meta["genres"] = work_genres
        work = Work(title=metadata["Title"], meta=work_meta)
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
            user_id = getattr(g, "user_id", None)
            user_id_str = str(user_id) if user_id else "anonymous"
            user = db.session.get(User, user_id) if user_id else None
            llm_permissions = User.list_llm_permissions(user)
            start_cover_processing(manifestation.id, canonical_isbn, title, author, user_id_str, llm_permissions=llm_permissions)
        db.session.commit()
    else:
        manifestation.update_meta(**metadata)
        if manifestation.expression and manifestation.expression.work:
            manifestation.expression.work.title = metadata["Title"]
            if not manifestation.expression.work.meta:
                manifestation.expression.work.meta = {}
            manifestation.expression.work.meta["authors"] = metadata["Authors"]
        db.session.commit()

    return jsonify(**metadata), 200


@api_bp.route("/isbn/<isbn>", methods=["POST"])
@require_auth
@require_permission(PermissionName.WRITE_METADATA)
def update_manifestation(isbn: str) -> tuple[Response, int]:
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    if not manifestation:
        return jsonify({"error": f"Manifestation not found for ISBN = {isbn}"}), 404

    payload_json = request.get_json(silent=True)
    if not isinstance(payload_json, dict):
        return invalid_json_payload_response()

    from pydantic import ValidationError

    from app.api.schemas import ManifestationUpdateSchema

    try:
        payload = ManifestationUpdateSchema(**payload_json)
    except (ValidationError, TypeError) as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid payload",
                    "details": str(e) if isinstance(e, TypeError) else e.errors(),
                }
            ),
            400,
        )

    metadata = payload.model_dump(exclude_unset=True)

    if metadata:
        if "publisher" in metadata:
            manifestation.publisher = metadata.pop("publisher")

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
        return jsonify({"status": "ok"}), 200

    return jsonify({"error": "No metadata provided"}), 400


@api_bp.route("/manifestations/<int:manifestation_id>/refetch-metadata", methods=["POST"])
@require_auth
@require_permission(PermissionName.REFETCH_METADATA)
def refetch_metadata(manifestation_id: int) -> tuple[Response, int]:
    manif = db.get_or_404(Manifestation, manifestation_id)
    isbn_val = manif.isbn13
    if not isbn_val and manif.meta:
        isbn_val = manif.meta.get("isbn") or manif.meta.get("barcode") or manif.meta.get("identifier")

    if not isbn_val:
        return jsonify({"success": False, "data": None, "error": "No ISBN to fetch metadata for"}), 400

    canonical_isbn = isbn_utils.canonicalize_isbn(str(isbn_val))
    if not canonical_isbn:
        return jsonify({"success": False, "data": None, "error": "Invalid ISBN"}), 400

    metadata = isbn_utils.fetch_isbn_metadata(canonical_isbn)
    if not metadata:
        return jsonify({"success": False, "data": None, "error": "No upstream metadata found"}), 404

    manif.update_meta(**metadata)
    if not manif.isbn13:
        manif.isbn13 = canonical_isbn

    if manif.expression and manif.expression.work:
        if "Title" in metadata:
            manif.expression.work.title = metadata["Title"]
        if "Authors" in metadata:
            work_meta = dict(manif.expression.work.meta or {})
            work_meta["authors"] = metadata["Authors"]
            manif.expression.work.meta = work_meta

    db.session.commit()
    return jsonify({"success": True, "data": {"id": manif.id}, "error": None}), 200


@api_bp.route("/manifestations/<int:manifestation_id>/cover", methods=["POST"])
@require_auth
@require_permission(PermissionName.UPLOAD_COVER)
def upload_cover(manifestation_id: int) -> tuple[Response, int]:
    if "cover" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["cover"]
    if not file.filename:
        return jsonify({"error": "No selected file"}), 400

    try:
        validate_upload_file(file)
    except ValueError as e:
        error_message = str(e)
        status_code = 413 if "too large" in error_message.lower() else 400
        return jsonify({"error": error_message}), status_code

    manifestation = db.get_or_404(Manifestation, manifestation_id)
    identifier = manifestation.isbn13 or manifestation.ean or manifestation.upc or f"item_{manifestation_id}"

    filename = secure_filename(f"{identifier}_raw.jpg")
    filepath = os.path.join(RAW_DIR, filename)
    file.save(filepath)

    manifestation.update_meta(cover_status="processing")
    db.session.commit()

    work = manifestation.expression.work if (manifestation.expression and manifestation.expression.work) else None
    title = work.title if work else "Unknown Title"
    author = work.meta.get("authors", ["Unknown Author"])[0] if (work and work.meta and work.meta.get("authors")) else "Unknown Author"

    user_id = getattr(g, "user_id", None)
    user_id_str = str(user_id) if user_id else "anonymous"
    user_obj = db.session.get(User, user_id) if user_id else None
    llm_permissions = User.list_llm_permissions(user_obj)

    # Record as a scan event if source is provided (e.g., scanner_camera)
    image_source = request.form.get("source", "user_upload")
    scan = ImageScan(
        manifestation_id=manifestation.id,
        file_path=f"/static/uploads/raw_covers/{filename}",  # Record raw for now, processing will update cover_url
        scan_type="front",
        source=image_source,
    )
    db.session.add(scan)
    db.session.commit()

    task_id = start_cover_processing(
        manifestation.id, identifier, title, author, user_id_str, llm_permissions=llm_permissions, user_image_path=filepath
    )

    if task_id is None:
        # Queue unavailable (e.g. Redis down): raw file is saved; mark as pending so
        # the user or admin can trigger regeneration once the queue recovers.
        manifestation.update_meta(cover_status="pending")
        db.session.commit()
        return (
            jsonify(
                {
                    "success": True,
                    "data": {"task_id": None, "message": "Cover saved; processing deferred — queue unavailable"},
                    "error": None,
                }
            ),
            202,
        )

    return jsonify({"success": True, "data": {"task_id": task_id, "message": "Cover upload processing started"}, "error": None}), 202


@api_bp.route("/manifestations/<int:manifestation_id>/images", methods=["GET"])
@optional_auth
def get_manifestation_images(manifestation_id: int) -> tuple[Response, int]:
    """Get all additional scans for a manifestation."""
    scans = ImageScan.query.filter_by(manifestation_id=manifestation_id).order_by(ImageScan.created_at.desc()).all()
    return (
        jsonify(
            {
                "success": True,
                "data": [
                    {
                        "id": s.id,
                        "url": s.file_path,
                        "label": s.scan_type,
                        "source": s.source,
                        "added_at": s.created_at.isoformat(),
                    }
                    for s in scans
                ],
                "error": None,
            }
        ),
        200,
    )


@api_bp.route("/manifestations/<int:manifestation_id>/images", methods=["POST"])
@require_auth
@require_permission(PermissionName.WRITE_METADATA)
def upload_manifestation_image(manifestation_id: int) -> tuple[Response, int]:
    """Upload an additional image (inlay, disc, back) for a manifestation."""
    manifestation = db.session.get(Manifestation, manifestation_id)
    if not manifestation:
        return jsonify({"success": False, "error": "Manifestation not found"}), 404

    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No selected file"}), 400

    try:
        validate_upload_file(file)
        image_label = request.form.get("label", "other")
        # QA/Tech-Debt Fix: Accept dynamic source from caller (scanner vs manual upload),
        # avoiding hardcoded "user_upload" that prevented scanner auto-fallback from being recorded.
        image_source = request.form.get("source", "user_upload")
        if len(image_source) > 100:
            return jsonify({"success": False, "error": "Source identifier too long (max 100)"}), 400
        filename = secure_filename(f"manifestation_{manifestation_id}_{image_label}_{file.filename}")
        image_url = save_upload_image(file, subfolder="gallery", filename=filename)
    except ValueError as e:
        msg = str(e)
        return jsonify({"success": False, "error": msg}), (413 if "too large" in msg.lower() else 400)
    except (OSError, SyntaxError):
        return jsonify({"success": False, "error": "Invalid or corrupted image file"}), 400

    # Save to ImageScan table with dynamic source
    scan = ImageScan(manifestation_id=manifestation_id, file_path=image_url, scan_type=image_label, source=image_source)
    db.session.add(scan)

    # Keep compatibility with old JSONB field for now
    meta = dict(manifestation.meta or {})
    additional_images = meta.get("additional_images", [])
    additional_images.append({"url": image_url, "label": image_label, "added_at": datetime.now(UTC).isoformat()})
    meta["additional_images"] = additional_images
    manifestation.meta = meta
    flag_modified(manifestation, "meta")

    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "url": image_url,
                    "label": image_label,
                    "added_at": scan.created_at.isoformat(),
                },
            }
        ),
        201,
    )


@api_bp.route("/manifestations/<int:manifestation_id>/regenerate-cover", methods=["POST"])
@require_auth
@require_permission(PermissionName.REGENERATE_COVER)
def regenerate_cover(manifestation_id: int) -> tuple[Response, int]:
    manif = db.get_or_404(Manifestation, manifestation_id)
    manif.update_meta(cover_status="pending")
    db.session.commit()

    work = manif.expression.work if manif.expression else None
    title = work.title if work else "Unknown"
    author = work.meta.get("authors", ["Unknown"])[0] if work and work.meta else "Unknown"
    identifier = manif.resolved_identifier

    meta = manif.meta or {}
    description = meta.get("Description", "")
    categories = meta.get("Categories", [])
    genre = ", ".join(categories) if isinstance(categories, list) else str(categories)
    user_id = getattr(g, "user_id", None)
    user_id_str = str(user_id) if user_id else "anonymous"
    user_obj = db.session.get(User, user_id) if user_id else None
    llm_permissions = User.list_llm_permissions(user_obj)
    task_id = start_cover_processing(
        manif.id,
        identifier,
        title,
        author,
        user_id_str,
        llm_permissions=llm_permissions,
        description=description,
        genre=genre,
    )

    if task_id is None:
        # Queue unavailable: reset cover_status so the user can retry later.
        manif.update_meta(cover_status="failed")
        db.session.commit()
        return (
            jsonify({"success": False, "data": None, "error": "Background queue unavailable. Please try again later."}),
            503,
        )

    return (
        jsonify(
            {"success": True, "data": {"task_id": task_id, "message": "Cover regeneration scheduled", "status": "pending"}, "error": None}
        ),
        202,
    )


@api_bp.route("/manifestations/<int:manifestation_id>/refetch-cover", methods=["POST"])
@require_auth
@require_permission(PermissionName.REFETCH_COVER)
def refetch_cover(manifestation_id: int) -> tuple[Response, int]:
    manif = db.get_or_404(Manifestation, manifestation_id)
    manif.update_meta(cover_status="pending")
    db.session.commit()

    work = manif.expression.work if manif.expression else None
    title = work.title if work else "Unknown"
    author = work.meta.get("authors", ["Unknown"])[0] if work and work.meta else "Unknown"
    identifier = manif.resolved_identifier

    meta = manif.meta or {}
    description = meta.get("Description", "")
    categories = meta.get("Categories", [])
    genre = ", ".join(categories) if isinstance(categories, list) else str(categories)
    user_id = getattr(g, "user_id", None)
    user_id_str = str(user_id) if user_id else "anonymous"

    # Disable LLM options to force fetching from upstream metadata sources only
    llm_permissions = {
        "allow_generate_cover": False,
        "allow_cloud_llm": False,
    }

    task_id = start_cover_processing(
        manif.id,
        identifier,
        title,
        author,
        user_id_str,
        llm_permissions=llm_permissions,
        description=description,
        genre=genre,
    )

    if task_id is None:
        manif.update_meta(cover_status="failed")
        db.session.commit()
        return (
            jsonify({"success": False, "data": None, "error": "Background queue unavailable. Please try again later."}),
            503,
        )

    return (
        jsonify({"success": True, "data": {"task_id": task_id, "message": "Cover refetch scheduled", "status": "pending"}, "error": None}),
        202,
    )


@api_bp.route("/manifestations/<int:manifestation_id>/cover-status", methods=["GET"])
@require_auth
def get_cover_status(manifestation_id: int):
    """Polling endpoint for async cover generation task."""
    task_id = request.args.get("task_id")
    if not task_id:
        # Fallback to DB status if no specific task ID provided
        m = db.session.get(Manifestation, manifestation_id)
        if not m:
            return jsonify({"success": False, "data": None, "error": "Manifestation not found"}), 404
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "cover_url": m.cover_url,
                        "status": m.meta.get("cover_status") if m.meta else None,
                    },
                    "error": None,
                }
            ),
            200,
        )

    from app.core.tasks import get_task_result

    user_id = getattr(g, "user_id", None)
    result = get_task_result(task_id, user_id=str(user_id) if user_id else None)

    if not result:
        return jsonify({"success": False, "data": None, "error": "Task not found"}), 404

    status = result.get("status")
    if status == "completed":
        m = db.session.get(Manifestation, manifestation_id)
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "cover_url": m.cover_url if m else None,
                        "status": "ready",
                    },
                    "error": None,
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "success": True,
                "data": {"status": status, "error": result.get("error")},
                "error": None,
            }
        ),
        202,
    )


@api_bp.route("/manifestations/<int:manifestation_id>", methods=["DELETE"])
@require_auth
@require_permission(PermissionName.DELETE_MANIFESTATION)
def delete_manifestation(manifestation_id: int) -> tuple[Response, int]:
    manif = db.session.get(Manifestation, manifestation_id)
    if not manif:
        return jsonify({"success": False, "data": None, "error": "Manifestation not found"}), 404

    try:
        # Manually nullify scan telemetry to avoid ForeignKeyViolation on delete
        from app.db.models import ScanTelemetry

        ScanTelemetry.query.filter_by(manifestation_id=manifestation_id).update({"manifestation_id": None})

        db.session.delete(manif)
        db.session.commit()
        return jsonify({"success": True, "data": {"id": manifestation_id}, "error": None}), 200
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        db.session.rollback()
        return jsonify({"success": False, "data": None, "error": str(e)}), 500
