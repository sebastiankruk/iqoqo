"""Defines the main routes for the web interface."""

from math import ceil, floor

from flask import render_template, request

from app.db.models import Expression, Item, Manifestation, Work, db

from . import web_bp


@web_bp.route("/")
def index():
    """Home page with statistics."""
    # Get counts for different categories
    total_books = db.session.query(Manifestation).count()
    not_added = (
        total_books
        - db.session.query(Manifestation.id)
        .join(Item, Manifestation.id == Item.manifestation_id, isouter=True)
        .filter(Item.id.is_(None))
        .count()
    )
    # Query incomplete works (missing title or authors) by joining with Expression and Work
    # Note: We'll do a simpler query and filter in Python for cross-database compatibility
    all_manifestations = db.session.query(Manifestation).join(Expression).join(Work).all()
    incomplete = sum(
        1
        for m in all_manifestations
        if not m.expression.work.title
        or not m.expression.work.meta
        or not m.expression.work.meta.get("authors")
        or len(m.expression.work.meta.get("authors", [])) == 0
    )

    counts = {"books": total_books, "not added": not_added, "incomplete": incomplete}

    return render_template("index.html", counts=counts, page="index")


@web_bp.route("/scan")
def scan():
    """Barcode scanner page."""
    return render_template("scan.html", page="scan")


@web_bp.route("/add")
def add():
    """Add new item page."""
    return render_template("add_update.html", page="add")


@web_bp.route("/update")
def update():
    """Update existing item page."""
    return render_template("add_update.html", page="update")


@web_bp.route("/list/query/<query_name>")
def list_query(query_name: str):
    """List books with pagination."""
    offset = int(request.args.get("offset", 0))
    page_size = 10

    # Build query based on query_name - join with Expression and Work to get title/authors
    query = db.session.query(Manifestation).join(Expression).join(Work)

    if query_name == "incomplete":
        # For incomplete, we need to check authors in meta which is JSON
        # Fetch all and filter in Python for database compatibility
        all_books = query.all()
        books_filtered = [
            book
            for book in all_books
            if not book.expression.work.title
            or not book.expression.work.meta
            or not book.expression.work.meta.get("authors")
            or len(book.expression.work.meta.get("authors", [])) == 0
        ]
        count = len(books_filtered)
        books = books_filtered[offset : offset + page_size]
    elif query_name == "not-added":
        query = query.outerjoin(Item, Manifestation.id == Item.manifestation_id).filter(Item.id.is_(None))
        count = query.count()
        books = query.order_by(Manifestation.id).offset(offset).limit(page_size).all()
    else:
        # Default: all books
        count = query.count()
        books = query.order_by(Manifestation.id).offset(offset).limit(page_size).all()

    pages = ceil(count / page_size)
    current_page = floor(offset / page_size)

    # Format books for template
    book_list = []
    for book in books:
        # Get title from the related Work
        title = book.expression.work.title if book.expression and book.expression.work else ""
        # Get authors from Work metadata
        authors_list = (
            book.expression.work.meta.get("authors", [])
            if book.expression and book.expression.work and book.expression.work.meta
            else []
        )
        authors = ", ".join(authors_list) if authors_list else ""

        book_list.append(
            {
                "id": book.id,
                "isbn": book.isbn13,
                "title": title,
                "authors": authors,
            }
        )

    return render_template(
        "list.html", books=book_list, count=count, offset=offset, pages=pages, current_page=current_page, page="list"
    )
