"""Defines the API endpoints for the application."""

# cSpell:ignore isbnlib

import json
from io import BytesIO
from typing import Any

import requests
from flask import jsonify, request, send_file, session

from app.core.data_manager import DataManager
from app.db.models import Expression, Item, Manifestation, Work, db

from . import api_bp


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
    """Get all items with pagination support."""
    # Get pagination parameters
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    offset = (page - 1) * limit

    # Get all items with pagination
    query = Item.query
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
    item = Item.query.get(item_id)

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
    item = Item.query.get(item_id)

    if not item:
        return jsonify({"success": False, "data": None, "error": "Item not found"}), 404

    data = request.get_json()

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
    item = Item.query.get(item_id)

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

    # Try to fetch using isbnlib (aggregates multiple sources: Google Books, WorldCat, etc.)
    metadata: dict[str, Any] = {}
    canonical_isbn = isbn  # Default to input ISBN

    try:
        import isbnlib  # pylint: disable=import-outside-toplevel

        # Canonicalize the ISBN
        canonical_isbn = isbnlib.canonical(isbn)
        if not canonical_isbn:
            return jsonify({"error": "Invalid ISBN"}), 400

        # Try to get metadata from multiple sources
        book_data = None
        try:
            book_data = isbnlib.meta(canonical_isbn)
        except Exception as e:  # pylint: disable=broad-except
            # Check if this is an ISBN redirect error (ISBNNotConsistentError)
            if "isbn request != isbn response" in str(e):
                # Handle ISBN redirects (when ISBN-10/13 mismatch)
                import ast  # pylint: disable=import-outside-toplevel
                import re  # pylint: disable=import-outside-toplevel

                m_isbn_redirect = re.match(r"isbn request != isbn response \(\S+ not in (\[[^\]]+\])\)", str(e))
                if m_isbn_redirect:
                    a_isbn_redirect = ast.literal_eval(m_isbn_redirect.group(1))  # type: ignore[arg-type]
                    isbn_redirect_dict = {v["type"]: v["identifier"] for v in a_isbn_redirect}
                    re_isbn = isbn_redirect_dict.get("ISBN_13", None) or isbn_redirect_dict.get("ISBN_10", None)

                    if re_isbn:
                        # Try again with redirected ISBN
                        try:
                            book_data = isbnlib.meta(re_isbn)
                            canonical_isbn = re_isbn
                        except Exception:  # pylint: disable=broad-except
                            # If redirect also fails, continue to fallback
                            pass

        if book_data:
            # isbnlib returns dict with 'Title', 'Authors', 'Publisher', 'Year', 'ISBN-13', 'Language'
            metadata = {
                "Title": book_data.get("Title", ""),
                "Authors": book_data.get("Authors", []),
            }
    except (ImportError, AttributeError) as e:
        # If isbnlib import fails, log and continue to Open Library fallback
        print(f"isbnlib not available for {isbn}: {e}")

    # Fall back to Open Library if isbnlib is not available or returned nothing
    if not metadata:
        try:
            response = requests.get(
                f"https://openlibrary.org/api/books?bibkeys=ISBN:{canonical_isbn}&format=json&jscmd=data",
                timeout=10,
            )
            data = response.json()

            if not data:
                return jsonify({}), 404

            book_data = list(data.values())[0]
            metadata = {
                "Title": book_data.get("title", ""),
                "Authors": [author.get("name", "") for author in book_data.get("authors", [])],
            }
        except (requests.RequestException, KeyError, ValueError) as e:
            # Both isbnlib and Open Library failed
            print(f"Open Library lookup also failed for {isbn}: {e}")
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

    metadata = request.get_json()

    # Check if metadata is None or empty dict
    if metadata is None:
        return jsonify({"error": "No metadata provided"}), 400

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
            data = request.get_json()
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
    data = request.get_json()
    if not data or not data.get("confirm"):
        return jsonify({"error": 'Confirmation required. Send {"confirm": true} to proceed.'}), 400

    try:
        DataManager.clear_all_data()
        return jsonify({"status": "success", "message": "All data cleared"})
    except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
        return jsonify({"error": str(e)}), 500
