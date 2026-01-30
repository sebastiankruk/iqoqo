"""Defines the API endpoints for the application."""

import json
from io import BytesIO

import requests
from flask import jsonify, request, send_file, session

from app.core.data_manager import DataManager
from app.db.models import Expression, Item, Manifestation, Work, db

from . import api_bp


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@api_bp.route("/items", methods=["GET"])
def get_items():
    items = Item.query.all()
    return jsonify([{"id": item.id, "owner_id": item.owner_id} for item in items])


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
        metadata = {
            "Title": work.title or "",
            "Authors": work.meta.get("authors", []) if work.meta else [],
        }
        # Only return if we have at least a title
        if metadata["Title"]:
            # Update manifestation.meta for future use
            if not manifestation.meta:
                manifestation.meta = {}
            manifestation.meta.update(metadata)
            try:
                db.session.commit()
            except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as e:
                db.session.rollback()
                # Continue anyway, we can still return the data
                print(f"Warning: Failed to update manifestation.meta: {e}")
            return jsonify(**metadata)

    # Try to fetch using isbnlib (aggregates multiple sources: Google Books, WorldCat, etc.)
    try:
        import isbnlib
        from isbnlib.exceptions import ISBNNotConsistentError

        # Canonicalize the ISBN
        canonical_isbn = isbnlib.canonical(isbn)
        if not canonical_isbn:
            return jsonify({"error": "Invalid ISBN"}), 400

        # Try to get metadata from multiple sources
        book_data = None
        try:
            book_data = isbnlib.meta(canonical_isbn)
        except ISBNNotConsistentError as e:
            # Handle ISBN redirects (when ISBN-10/13 mismatch)
            import re

            m_isbn_redirect = re.match(r"isbn request != isbn response \(\S+ not in (\[[^\]]+\])\)", str(e))
            if m_isbn_redirect:
                a_isbn_redirect = eval(m_isbn_redirect.group(1))
                m_isbn_redirect = {v["type"]: v["identifier"] for v in a_isbn_redirect}
                re_isbn = m_isbn_redirect.get("ISBN_13", None) or m_isbn_redirect.get("ISBN_10", None)

                if re_isbn:
                    # Try again with redirected ISBN
                    try:
                        book_data = isbnlib.meta(re_isbn)
                        canonical_isbn = re_isbn
                    except Exception:
                        # If redirect also fails, continue to fallback
                        pass
        except Exception as e:
            # If isbnlib fails (e.g., rate limiting, network errors), log and continue to fallback
            print(f"isbnlib lookup failed for {isbn}: {e}")
            pass

        if book_data:
            # isbnlib returns dict with 'Title', 'Authors', 'Publisher', 'Year', 'ISBN-13', 'Language'
            metadata = {
                "Title": book_data.get("Title", ""),
                "Authors": book_data.get("Authors", []),
            }
        else:
            # Fall back to Open Library if isbnlib returns nothing
            try:
                response = requests.get(
                    f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data", timeout=10
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

    except (ImportError, AttributeError) as e:
        # If isbnlib import fails, return 404 with empty dict
        print(f"ISBN lookup failed for {isbn}: {e}")
        return jsonify({}), 404


@api_bp.route("/isbn/<isbn>", methods=["POST"])
def update_manifestation(isbn: str):
    """Update manifestation metadata."""
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    if not manifestation:
        return jsonify({"error": "Manifestation not found"}), 404

    metadata = request.get_json()

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
        if lookup_response.status_code != 200:  # Check if lookup failed
            return jsonify({"error": "Manifestation not found"}), 404
        manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

    metadata = request.get_json()

    # Update manifestation metadata if provided
    if metadata:
        if not manifestation.meta:
            manifestation.meta = {}
        manifestation.meta.update(metadata)

        # Also update the work title if provided
        if "Title" in metadata and manifestation.expression and manifestation.expression.work:
            manifestation.expression.work.title = metadata["Title"]

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
