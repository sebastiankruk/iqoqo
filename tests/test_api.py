"""Tests for the API endpoints."""

from unittest.mock import patch

import pytest

from app.db.models import Expression, Item, Manifestation, Work, db

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally
# pylint: disable=unused-argument  # fixtures used for setup, not always referenced


@pytest.fixture
def sample_book(app):
    """Create a sample book in the FRBRoo structure for testing."""
    with app.app_context():
        # Create Work
        work = Work(
            title="The Hitchhiker's Guide to the Galaxy",
            meta={"authors": ["Douglas Adams"], "categories": ["Science Fiction"]},
        )
        db.session.add(work)
        db.session.flush()

        # Create Expression
        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        # Create Manifestation
        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13="9780345391803",
            meta={"Title": "The Hitchhiker's Guide to the Galaxy", "Authors": ["Douglas Adams"]},
        )
        db.session.add(manifestation)
        db.session.commit()

        yield manifestation


@pytest.fixture
def book_without_meta(app):
    """Create a book where metadata is in Work but not in Manifestation.meta."""
    with app.app_context():
        # Create Work
        work = Work(title="Longman Language Activator", meta={"authors": ["Della Summers"], "categories": []})
        db.session.add(work)
        db.session.flush()

        # Create Expression
        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        # Create Manifestation without Title in meta
        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13="9780582040939",
            meta={"imageLinks": {}, "pageCount": None, "industryIdentifiers": []},
        )
        db.session.add(manifestation)
        db.session.commit()

        yield manifestation


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json
    assert data["status"] == "ok"
    assert data["service"] == "iqoqo-api"


def test_lookup_isbn_with_meta_field(client, sample_book):
    """Test ISBN lookup when metadata exists in manifestation.meta."""
    response = client.get("/api/isbn/9780345391803")
    assert response.status_code == 200
    data = response.json
    assert data["Title"] == "The Hitchhiker's Guide to the Galaxy"
    assert data["Authors"] == ["Douglas Adams"]


def test_lookup_isbn_from_work_data(client, book_without_meta):
    """Test ISBN lookup when metadata needs to be built from Work/Expression."""
    response = client.get("/api/isbn/9780582040939")
    assert response.status_code == 200
    data = response.json
    assert data["Title"] == "Longman Language Activator"
    assert data["Authors"] == ["Della Summers"]


@patch("app.utils.isbn.fetch_isbn_metadata", return_value=None)
def test_lookup_isbn_not_found(mock_fetch, client):
    """Test ISBN lookup for a valid ISBN not found in any upstream source returns 404."""
    response = client.get("/api/isbn/9780000000002")
    assert response.status_code == 404


@patch("app.utils.isbn.fetch_isbn_metadata")
def test_lookup_isbn_from_open_library(mock_fetch, client):
    """Test ISBN lookup fetches from external sources when not in DB."""
    mock_fetch.return_value = {"Title": "1984", "Authors": ["George Orwell"]}

    response = client.get("/api/isbn/9780451524935")
    assert response.status_code == 200
    data = response.json
    assert data["Title"] == "1984"
    assert data["Authors"] == ["George Orwell"]

    # Verify the book was saved to the database
    with client.application.app_context():
        manifestation = Manifestation.query.filter_by(isbn13="9780451524935").first()
        assert manifestation is not None
        assert manifestation.expression.work.title == "1984"


def test_update_manifestation(client, sample_book):
    """Test updating manifestation metadata."""
    new_data = {"Title": "Updated Title", "Authors": ["New Author"]}
    response = client.post("/api/isbn/9780345391803", json=new_data, content_type="application/json")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

    # Verify the update
    with client.application.app_context():
        manifestation = Manifestation.query.filter_by(isbn13="9780345391803").first()
        assert manifestation.meta["Title"] == "Updated Title"
        assert manifestation.expression.work.title == "Updated Title"


def test_update_manifestation_not_found(client):
    """Test updating non-existent manifestation returns 404."""
    response = client.post("/api/isbn/9999999999999", json={"Title": "Test"}, content_type="application/json")
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("payload", "content_type"),
    [
        ('{"Title": "Updated Title"', "application/json"),  # malformed JSON
        (None, "application/json"),  # missing JSON body
    ],
)
def test_update_manifestation_invalid_or_missing_json_payload(client, sample_book, payload, content_type):
    """Test update_manifestation returns standardized 400 for invalid or missing JSON payload."""
    request_kwargs = {"content_type": content_type}
    if payload is not None:
        request_kwargs["data"] = payload

    response = client.post("/api/isbn/9780345391803", **request_kwargs)

    assert response.status_code == 400
    assert response.json == {
        "success": False,
        "data": None,
        "error": "Invalid or missing JSON payload",
    }


def test_get_items_by_isbn(client, sample_book):
    """Test getting items for a given ISBN."""
    # First add an item
    with client.application.app_context():
        item = Item(manifestation_id=sample_book.id, owner_id="test_user")
        db.session.add(item)
        db.session.commit()

    response = client.get("/api/item/9780345391803")
    assert response.status_code == 200
    data = response.json
    assert "ids" in data
    assert len(data["ids"]) == 1


def test_get_items_by_isbn_no_items(client, sample_book):
    """Test getting items when none exist returns 404."""
    response = client.get("/api/item/9780345391803")
    assert response.status_code == 404


def test_get_items_by_isbn_no_manifestation(client):
    """Test getting items for non-existent ISBN returns 404."""
    response = client.get("/api/item/9999999999999")
    assert response.status_code == 404


def test_add_item(client, sample_book):
    """Test adding a new item for a given ISBN."""
    metadata = {"Title": "Test Book", "Authors": ["Test Author"]}
    response = client.post("/api/item/9780345391803", json=metadata, content_type="application/json")
    assert response.status_code == 200
    data = response.json
    assert "item_id" in data

    # Verify item was created
    with client.application.app_context():
        items = Item.query.filter_by(manifestation_id=sample_book.id).all()
        assert len(items) == 1


@patch("app.utils.isbn.fetch_isbn_metadata")
def test_add_item_creates_manifestation_if_not_exists(mock_fetch, client):
    """Test adding item creates manifestation from external sources if it doesn't exist."""
    mock_fetch.return_value = {"Title": "The Road", "Authors": ["Cormac McCarthy"]}

    metadata = {"Title": "The Road", "Authors": ["Cormac McCarthy"]}
    response = client.post("/api/item/9780307277671", json=metadata, content_type="application/json")
    assert response.status_code == 200

    # Verify manifestation and item were created
    with client.application.app_context():
        manifestation = Manifestation.query.filter_by(isbn13="9780307277671").first()
        assert manifestation is not None
        items = Item.query.filter_by(manifestation_id=manifestation.id).all()
        assert len(items) == 1


@patch("app.api.routes.threading.Thread")
def test_regenerate_cover(mock_thread, client, sample_book):
    """Test the regenerate cover endpoint triggers background processing."""
    # 1. Call the endpoint
    response = client.post(f"/api/manifestations/{sample_book.id}/regenerate-cover")

    # 2. Verify Response
    assert response.status_code == 202
    assert response.json["status"] == "pending"

    # 3. Verify DB State (Optimistic update)
    with client.application.app_context():
        manif = db.session.get(Manifestation, sample_book.id)
        assert manif.meta["cover_status"] == "pending"

    # 4. Verify Background Thread was started
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()
