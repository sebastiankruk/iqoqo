"""Tests for the web interface routes and static files."""

import os

from app.db import db
from app.db.models import Expression, Item, Manifestation, Work


def test_index_page(client):
    """Test that the index page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<sub>i</sub>QO<sup>2</sup>" in response.data


def test_scan_page(client):
    """Test that the scan page loads."""
    response = client.get("/scan")
    assert response.status_code == 200
    assert b"reader" in response.data


def test_add_page(client):
    """Test that the add page loads."""
    response = client.get("/add")
    assert response.status_code == 200
    assert b"fiIsbnValue" in response.data


def test_update_page(client):
    """Test that the update page loads."""
    response = client.get("/update")
    assert response.status_code == 200
    assert b"fiIsbnValue" in response.data


def test_list_books_page(client):
    """Test that the list books page loads."""
    response = client.get("/list/query/books")
    assert response.status_code == 200
    assert b"ISBN" in response.data
    assert b"Title" in response.data


def test_static_css_bootstrap(client):
    """Test that Bootstrap CSS file is accessible."""
    response = client.get("/static/css/bootstrap.min.css")
    assert response.status_code == 200
    assert response.content_type.startswith("text/css")


def test_static_css_base(client):
    """Test that base CSS file is accessible."""
    response = client.get("/static/css/base.css")
    assert response.status_code == 200
    assert response.content_type.startswith("text/css")


def test_static_js_jquery(client):
    """Test that jQuery file is accessible."""
    response = client.get("/static/js/jquery-3.6.0.min.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_bootstrap(client):
    """Test that Bootstrap JS file is accessible."""
    response = client.get("/static/js/bootstrap.bundle.min.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_html5_qrcode(client):
    """Test that html5-qrcode library is accessible."""
    response = client.get("/static/js/html5-qrcode.min.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_isbn(client):
    """Test that custom ISBN JS file is accessible."""
    response = client.get("/static/js/isbn.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_beep(client):
    """Test that custom beep JS file is accessible."""
    response = client.get("/static/js/beep.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_toast(client):
    """Test that custom toast JS file is accessible."""
    response = client.get("/static/js/toast.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_metaform(client):
    """Test that custom metaform JS file is accessible."""
    response = client.get("/static/js/metaform.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_update_buttons(client):
    """Test that custom update_buttons JS file is accessible."""
    response = client.get("/static/js/update_buttons.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_qrcode(client):
    """Test that custom qrcode JS file is accessible."""
    response = client.get("/static/js/qrcode.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_js_custom_add_update(client):
    """Test that custom add_update JS file is accessible."""
    response = client.get("/static/js/add_update.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript") or response.content_type.startswith(
        "text/javascript"
    )


def test_static_audio_ding(client):
    """Test that ding audio file is accessible."""
    response = client.get("/static/audio/ding.mp3")
    assert response.status_code == 200
    assert response.content_type.startswith("audio/")


def test_static_audio_error(client):
    """Test that error audio file is accessible."""
    response = client.get("/static/audio/error2.mp3")
    assert response.status_code == 200
    assert response.content_type.startswith("audio/")


def test_index_includes_static_assets(client):
    """Test that the index page includes references to static assets."""
    response = client.get("/")
    assert response.status_code == 200

    # Check for CSS links
    assert b"bootstrap.min.css" in response.data
    assert b"base.css" in response.data

    # Check for JS script tags
    assert b"bootstrap.bundle.min.js" in response.data
    assert b"jquery-3.6.0.min.js" in response.data
    assert b"html5-qrcode.min.js" in response.data
    assert b"beep.js" in response.data
    assert b"isbn.js" in response.data


def test_scan_page_includes_scanner_scripts(client):
    """Test that the scan page includes scanner-related scripts."""
    response = client.get("/scan")
    assert response.status_code == 200

    # Check for scanner-specific scripts
    assert b"qrcode.js" in response.data
    assert b"metaform.js" in response.data
    assert b"update_buttons.js" in response.data


def test_add_page_includes_form_scripts(client):
    """Test that the add page includes form-related scripts."""
    response = client.get("/add")
    assert response.status_code == 200

    # Check for form-specific scripts
    assert b"add_update.js" in response.data
    assert b"metaform.js" in response.data
    assert b"update_buttons.js" in response.data


def test_static_files_exist_on_filesystem(app):
    """Test that expected static files exist in the filesystem."""
    static_folder = os.path.join(app.root_path, "web", "static")

    # Check CSS files
    assert os.path.exists(os.path.join(static_folder, "css", "bootstrap.min.css"))
    assert os.path.exists(os.path.join(static_folder, "css", "base.css"))

    # Check JS files
    assert os.path.exists(os.path.join(static_folder, "js", "jquery-3.6.0.min.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "bootstrap.bundle.min.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "html5-qrcode.min.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "isbn.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "beep.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "toast.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "metaform.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "update_buttons.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "qrcode.js"))
    assert os.path.exists(os.path.join(static_folder, "js", "add_update.js"))

    # Check audio files
    assert os.path.exists(os.path.join(static_folder, "audio", "ding.mp3"))
    assert os.path.exists(os.path.join(static_folder, "audio", "error2.mp3"))


# ============================================================================
# FRBR Hierarchy Tests
# ============================================================================


def test_frbr_hierarchy_books_list(app, client):
    """Test that the books list properly traverses the FRBR hierarchy."""
    with app.app_context():
        # Create a complete FRBR hierarchy: Work -> Expression -> Manifestation
        work = Work(title="The Hobbit", meta={"authors": ["J.R.R. Tolkien"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13="9780048230706",
            publisher="Allen & Unwin",
            meta={},
        )
        db.session.add(manifestation)
        db.session.commit()

    # Test that the list endpoint returns the book with title and authors
    response = client.get("/list/query/books")
    assert response.status_code == 200
    assert b"The Hobbit" in response.data
    assert b"J.R.R. Tolkien" in response.data
    assert b"9780048230706" in response.data


def test_frbr_hierarchy_multiple_books(app, client):
    """Test that multiple books with proper FRBR hierarchy are displayed."""
    with app.app_context():
        # Create first book
        work1 = Work(title="1984", meta={"authors": ["George Orwell"]})
        db.session.add(work1)
        db.session.flush()

        expr1 = Expression(work_id=work1.id, content_type="text", language="en")
        db.session.add(expr1)
        db.session.flush()

        manif1 = Manifestation(expression_id=expr1.id, isbn13="9780451524935")
        db.session.add(manif1)

        # Create second book
        work2 = Work(title="Animal Farm", meta={"authors": ["George Orwell"]})
        db.session.add(work2)
        db.session.flush()

        expr2 = Expression(work_id=work2.id, content_type="text", language="en")
        db.session.add(expr2)
        db.session.flush()

        manif2 = Manifestation(expression_id=expr2.id, isbn13="9780452284244")
        db.session.add(manif2)

        db.session.commit()

    response = client.get("/list/query/books")
    assert response.status_code == 200
    assert b"1984" in response.data
    assert b"Animal Farm" in response.data
    assert b"George Orwell" in response.data
    assert b"9780451524935" in response.data
    assert b"9780452284244" in response.data


def test_frbr_hierarchy_multiple_authors(app, client):
    """Test books with multiple authors are displayed correctly."""
    with app.app_context():
        work = Work(title="Good Omens", meta={"authors": ["Terry Pratchett", "Neil Gaiman"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13="9780060853983")
        db.session.add(manifestation)
        db.session.commit()

    response = client.get("/list/query/books")
    assert response.status_code == 200
    assert b"Good Omens" in response.data
    assert b"Terry Pratchett, Neil Gaiman" in response.data


def test_frbr_hierarchy_incomplete_books_query(app, client):
    """Test that incomplete books (missing title or authors) are filtered correctly."""
    with app.app_context():
        # Create complete book
        work1 = Work(title="Complete Book", meta={"authors": ["Author Name"]})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type="text", language="en")
        db.session.add(expr1)
        db.session.flush()
        manif1 = Manifestation(expression_id=expr1.id, isbn13="1111111111111")
        db.session.add(manif1)

        # Create book with missing authors
        work2 = Work(title="No Authors Book", meta={})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type="text", language="en")
        db.session.add(expr2)
        db.session.flush()
        manif2 = Manifestation(expression_id=expr2.id, isbn13="2222222222222")
        db.session.add(manif2)

        db.session.commit()

    # The incomplete query should show the book missing authors
    response = client.get("/list/query/incomplete")
    assert response.status_code == 200
    assert b"No Authors Book" in response.data
    assert b"Complete Book" not in response.data


def test_frbr_hierarchy_not_added_books_query(app, client):
    """Test that books not in user's collection (no Item) are filtered correctly."""
    with app.app_context():
        # Create book without item (not in collection)
        work1 = Work(title="Not Owned", meta={"authors": ["Author One"]})
        db.session.add(work1)
        db.session.flush()
        expr1 = Expression(work_id=work1.id, content_type="text", language="en")
        db.session.add(expr1)
        db.session.flush()
        manif1 = Manifestation(expression_id=expr1.id, isbn13="3333333333333")
        db.session.add(manif1)

        # Create book with item (in collection)
        work2 = Work(title="Owned Book", meta={"authors": ["Author Two"]})
        db.session.add(work2)
        db.session.flush()
        expr2 = Expression(work_id=work2.id, content_type="text", language="en")
        db.session.add(expr2)
        db.session.flush()
        manif2 = Manifestation(expression_id=expr2.id, isbn13="4444444444444")
        db.session.add(manif2)
        db.session.flush()

        item = Item(manifestation_id=manif2.id, owner_id="test_user", status="available")
        db.session.add(item)

        db.session.commit()

    # The not-added query should show only the book without an item
    response = client.get("/list/query/not-added")
    assert response.status_code == 200
    assert b"Not Owned" in response.data
    assert b"Owned Book" not in response.data


def test_frbr_hierarchy_index_statistics(app, client):
    """Test that index page statistics correctly count books across FRBR hierarchy."""
    with app.app_context():
        # Create 3 complete books
        for i in range(3):
            work = Work(title=f"Book {i}", meta={"authors": [f"Author {i}"]})
            db.session.add(work)
            db.session.flush()
            expr = Expression(work_id=work.id, content_type="text", language="en")
            db.session.add(expr)
            db.session.flush()
            manif = Manifestation(expression_id=expr.id, isbn13=f"555555555555{i}")
            db.session.add(manif)

        # Create 1 incomplete book (missing authors)
        work_inc = Work(title="Incomplete", meta={})
        db.session.add(work_inc)
        db.session.flush()
        expr_inc = Expression(work_id=work_inc.id, content_type="text", language="en")
        db.session.add(expr_inc)
        db.session.flush()
        manif_inc = Manifestation(expression_id=expr_inc.id, isbn13="6666666666666")
        db.session.add(manif_inc)

        # Add item for first book only
        db.session.flush()
        manifestations = Manifestation.query.all()
        item = Item(manifestation_id=manifestations[0].id, owner_id="test_user")
        db.session.add(item)

        db.session.commit()

    response = client.get("/")
    assert response.status_code == 200
    # Should show 4 total books
    assert b"4" in response.data


def test_frbr_hierarchy_empty_metadata(app, client):
    """Test that books with empty/null metadata don't crash the view."""
    with app.app_context():
        work = Work(title="Minimal Book", meta=None)
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta=None)
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13="7777777777777", meta=None)
        db.session.add(manifestation)
        db.session.commit()

    response = client.get("/list/query/books")
    assert response.status_code == 200
    assert b"Minimal Book" in response.data
    assert b"7777777777777" in response.data


def test_frbr_hierarchy_pagination(app, client):
    """Test that pagination works correctly with FRBR hierarchy."""
    with app.app_context():
        # Create 15 books to test pagination (default page size is 10)
        for i in range(15):
            work = Work(title=f"Book {i:02d}", meta={"authors": [f"Author {i}"]})
            db.session.add(work)
            db.session.flush()
            expr = Expression(work_id=work.id, content_type="text", language="en")
            db.session.add(expr)
            db.session.flush()
            manif = Manifestation(expression_id=expr.id, isbn13=f"888888888{i:04d}")
            db.session.add(manif)
        db.session.commit()

    # First page should have 10 books
    response = client.get("/list/query/books?offset=0")
    assert response.status_code == 200
    content = response.data.decode()

    # Check that we have some books from the first page
    assert "Book 00" in content
    assert "Book 09" in content

    # Second page should have 5 books
    response = client.get("/list/query/books?offset=10")
    assert response.status_code == 200
    content = response.data.decode()
    assert "Book 10" in content
    assert "Book 14" in content
