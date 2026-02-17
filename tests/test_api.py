"""Tests for the API endpoints."""

from unittest.mock import MagicMock, patch

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


@patch("isbnlib.meta")
@patch("app.api.routes.requests.get")
def test_lookup_isbn_not_found(mock_get, mock_isbnlib_meta, client):
    """Test ISBN lookup for non-existent ISBN returns 404."""
    # Mock isbnlib to return None
    mock_isbnlib_meta.return_value = None

    # Mock Open Library API to return empty result
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_get.return_value = mock_response

    response = client.get("/api/isbn/9999999999999")
    assert response.status_code == 404


@patch("isbnlib.meta")
@patch("isbnlib.canonical")
@patch("app.api.routes.requests.get")
def test_lookup_isbn_from_open_library(mock_get, mock_canonical, mock_meta, client):
    """Test ISBN lookup fetches from Open Library API when not in DB."""
    # Mock isbnlib to return None (not available) so it falls back to Open Library
    mock_meta.return_value = None
    mock_canonical.return_value = "9780451524935"

    # Mock Open Library API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"ISBN:9780451524935": {"title": "1984", "authors": [{"name": "George Orwell"}]}}
    mock_get.return_value = mock_response

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


@patch("app.api.routes.requests.get")
def test_add_item_creates_manifestation_if_not_exists(mock_get, client):
    """Test adding item creates manifestation from Open Library if it doesn't exist."""
    # Mock Open Library API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"ISBN:9780307277671": {"title": "The Road", "authors": [{"name": "Cormac McCarthy"}]}}
    mock_get.return_value = mock_response

    metadata = {"Title": "The Road", "Authors": ["Cormac McCarthy"]}
    response = client.post("/api/item/9780307277671", json=metadata, content_type="application/json")
    assert response.status_code == 200

    # Verify manifestation and item were created
    with client.application.app_context():
        manifestation = Manifestation.query.filter_by(isbn13="9780307277671").first()
        assert manifestation is not None
        items = Item.query.filter_by(manifestation_id=manifestation.id).all()
        assert len(items) == 1
        assert len(items) == 1
        assert len(items) == 1
