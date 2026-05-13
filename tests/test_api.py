# tests/test_api.py
"""Tests for the API endpoints."""

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

from unittest.mock import patch

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, Work, db

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


@pytest.fixture
def admin_headers(app):
    """Fixture to provide authorization headers for an admin user."""
    with app.app_context():
        # Create permissions
        perms = [
            Permission(name="regenerate:cover"),
            Permission(name="refetch:metadata"),
            Permission(name="delete:item"),
            Permission(name="upload:cover"),
            Permission(name="write:metadata"),
        ]
        db.session.add_all(perms)

        # Create admin role
        admin_role = Role(name="admin")
        admin_role.permissions.extend(perms)
        db.session.add(admin_role)

        # Create admin user
        admin_user = User(email="test_admin@iqoqo.local", display_name="Admin")
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()

        # Generate token
        token = generate_internal_jwt(admin_user)
        return {"Authorization": f"Bearer {token}"}


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json
    assert data["status"] == "ok"
    assert data["service"] == "iqoqo-api"


def test_config(client):
    """Test the config endpoint returns expected envelope and fields."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert "federation_enabled" in data["data"]
    assert "version" in data["data"]
    assert data["error"] is None


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


def test_update_manifestation(client, sample_book, admin_headers):
    """Test updating manifestation metadata."""
    new_data = {"Title": "Updated Title", "Authors": ["New Author"]}
    response = client.post("/api/isbn/9780345391803", json=new_data, headers=admin_headers, content_type="application/json")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

    # Verify the update
    with client.application.app_context():
        manifestation = Manifestation.query.filter_by(isbn13="9780345391803").first()
        assert manifestation.meta["Title"] == "Updated Title"
        assert manifestation.expression.work.title == "Updated Title"


def test_update_manifestation_not_found(client, admin_headers):
    """Test updating non-existent manifestation returns 404."""
    response = client.post("/api/isbn/9999999999999", json={"Title": "Test"}, headers=admin_headers, content_type="application/json")
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("payload", "content_type"),
    [
        ('{"Title": "Updated Title"', "application/json"),  # malformed JSON
        (None, "application/json"),  # missing JSON body
    ],
)
def test_update_manifestation_invalid_or_missing_json_payload(client, sample_book, payload, content_type, admin_headers):
    """Test update_manifestation returns standardized 400 for invalid or missing JSON payload."""
    request_kwargs = {"content_type": content_type, "headers": admin_headers}
    if payload is not None:
        request_kwargs["data"] = payload

    response = client.post("/api/isbn/9780345391803", **request_kwargs)

    assert response.status_code == 400
    assert response.json == {
        "error": "Invalid or missing JSON payload",
        "code": 400,
    }


def test_get_items_by_isbn(client, sample_book):
    """Test getting items for a given ISBN."""
    # First add an item
    with client.application.app_context():
        test_user = User(email="datamanager_tester@iqoqo.local", display_name="DM Tester")
        db.session.add(test_user)
        db.session.flush()
        item = Item(manifestation_id=sample_book.id, owner_id=test_user.id)
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


def test_add_item(client, sample_book, normal_user_headers):
    """Test adding a new item for a given ISBN."""
    metadata = {"Title": "Test Book", "Authors": ["Test Author"]}
    response = client.post("/api/item/9780345391803", json=metadata, headers=normal_user_headers, content_type="application/json")
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert "item_id" in data["data"]

    # Verify item was created
    with client.application.app_context():
        items = Item.query.filter_by(manifestation_id=sample_book.id).all()
        assert len(items) == 1


@patch("app.utils.isbn.fetch_isbn_metadata")
def test_add_item_creates_manifestation_if_not_exists(mock_fetch, client, normal_user_headers):
    """Test adding item creates manifestation from external sources if it doesn't exist."""
    mock_fetch.return_value = {"Title": "The Road", "Authors": ["Cormac McCarthy"]}

    metadata = {"Title": "The Road", "Authors": ["Cormac McCarthy"]}
    response = client.post("/api/item/9780307277671", json=metadata, headers=normal_user_headers, content_type="application/json")
    assert response.status_code == 200

    # Verify manifestation and item were created
    with client.application.app_context():
        manifestation = Manifestation.query.filter_by(isbn13="9780307277671").first()
        assert manifestation is not None
        items = Item.query.filter_by(manifestation_id=manifestation.id).all()
        assert len(items) == 1


@patch("app.api.manifestations.start_cover_processing")
def test_regenerate_cover(mock_start, client, sample_book, admin_headers):
    """Test the regenerate cover endpoint triggers background processing."""
    mock_start.return_value = "test-task-id"
    # 1. Call the endpoint
    response = client.post(f"/api/manifestations/{sample_book.id}/regenerate-cover", headers=admin_headers)

    # 2. Verify Response
    assert response.status_code == 202
    assert response.json["data"]["status"] == "pending"

    # 3. Verify DB State (Optimistic update)
    with client.application.app_context():
        manif = db.session.get(Manifestation, sample_book.id)
        assert manif.meta["cover_status"] == "pending"

    # 4. Verify background pipeline was scheduled
    mock_start.assert_called_once()


# =============================================================================
# /vision/extract tests
# =============================================================================


def _make_minimal_jpeg() -> bytes:
    """Return the bytes of a valid, tiny 1×1 JPEG image for upload tests."""
    from io import BytesIO

    from PIL import Image as PILImage

    buf = BytesIO()
    PILImage.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def test_vision_extract_requires_auth(client):
    """POST /api/vision/extract must return 401 when no auth token is supplied."""
    response = client.post("/api/vision/extract")
    assert response.status_code == 401


def test_vision_extract_forbidden(client, normal_user_headers):
    """POST /api/vision/extract must return 403 when user lacks permission."""
    response = client.post("/api/vision/extract", headers=normal_user_headers)
    assert response.status_code == 403
    assert response.json["error"] == "Forbidden"


def test_vision_extract_missing_file(client, vision_user_headers):
    """POST /api/vision/extract must return 400 when no 'cover' file is included."""
    response = client.post("/api/vision/extract", headers=vision_user_headers)
    assert response.status_code == 400
    data = response.json
    assert data["success"] is False
    assert "No file provided" in data["error"]


def test_vision_extract_empty_filename(client, vision_user_headers):
    """POST /api/vision/extract must return 400 when the filename is empty."""
    from io import BytesIO

    response = client.post(
        "/api/vision/extract",
        headers=vision_user_headers,
        data={"cover": (BytesIO(b"data"), "")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    data = response.json
    assert data["success"] is False
    assert "No file provided" in data["error"]


@pytest.mark.parametrize("bad_ext", ["exe", "txt", "gif", "pdf"])
def test_vision_extract_invalid_extension(client, vision_user_headers, bad_ext):
    """POST /api/vision/extract must return 400 for disallowed file extensions."""
    from io import BytesIO

    response = client.post(
        "/api/vision/extract",
        headers=vision_user_headers,
        data={"cover": (BytesIO(b"data"), f"cover.{bad_ext}")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    data = response.json
    assert data["success"] is False
    assert "Invalid file type" in data["error"]


def test_vision_extract_corrupted_image(client, vision_user_headers):
    """POST /api/vision/extract must return 400 for a corrupt/non-image payload."""
    from io import BytesIO

    response = client.post(
        "/api/vision/extract",
        headers=vision_user_headers,
        data={"cover": (BytesIO(b"not-an-image-at-all"), "cover.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    data = response.json
    assert data["success"] is False
    assert "Invalid or corrupted image" in data["error"]


@patch("app.api.scanner.submit_task")
def test_vision_extract_success(mock_submit, client, vision_user_headers):
    """POST /api/vision/extract returns 202 on success."""
    from io import BytesIO

    mock_submit.return_value = "test-task-id"

    jpeg_bytes = _make_minimal_jpeg()
    response = client.post(
        "/api/vision/extract",
        headers=vision_user_headers,
        data={"cover": (BytesIO(jpeg_bytes), "cover.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 202
    data = response.json
    assert data["success"] is True
    assert data["data"]["task_id"] == "test-task-id"
    assert data["error"] is None


@patch("app.api.scanner.get_task_result")
def test_vision_extract_api_unavailable(mock_get_result, client, vision_user_headers):
    """GET /api/vision/extract/<id> returns 503 when the Vision API fails."""
    mock_get_result.return_value = {"status": "failed", "error": "Vision extraction failed. All fallback methods"}

    response = client.get(
        "/api/vision/extract/test-task-id",
        headers=vision_user_headers,
    )
    assert response.status_code == 503
    data = response.json
    assert data["success"] is False
    assert "Vision extraction failed. All fallback methods" in data["error"]


@patch("app.api.manifestations.start_cover_processing")
def test_upload_cover(mock_start, client, sample_book, admin_headers):
    """POST /api/manifestations/<id>/cover returns 202 on success."""
    mock_start.return_value = "test-task-id"
    from io import BytesIO

    jpeg_bytes = _make_minimal_jpeg()
    response = client.post(
        f"/api/manifestations/{sample_book.id}/cover",
        headers=admin_headers,
        data={"cover": (BytesIO(jpeg_bytes), "cover.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 202
    assert response.json["data"]["message"] == "Cover upload processing started"
    mock_start.assert_called_once()


def test_manifestation_user_owns_authenticated(client, sample_book):
    """Test that retrieving a manifestation correctly returns user_owns=True if logged in and user owns it."""
    # First add a user and item
    with client.application.app_context():
        test_user = User(email="owns_tester@iqoqo.local", display_name="Ownership Tester")
        db.session.add(test_user)
        db.session.flush()
        item = Item(manifestation_id=sample_book.id, owner_id=test_user.id)
        db.session.add(item)
        db.session.commit()
        token = generate_internal_jwt(test_user)
        auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Test authenticated endpoint calculates user_owns True
    response = client.get(f"/api/manifestations/{sample_book.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json["data"]["user_owns"] is True

    # 2. Test unauthenticated endpoint calculates user_owns False
    response = client.get(f"/api/manifestations/{sample_book.id}")
    assert response.status_code == 200
    assert response.json["data"]["user_owns"] is False


def test_add_item_manual_standard_envelope(client, normal_user_headers):
    """Test that manual item creation uses the standard {success, data, error} envelope."""
    payload = {"Title": "Manual Test Book", "Authors": ["Manual Author"], "Format": "book"}
    response = client.post("/api/items/manual", json=payload, headers=normal_user_headers)
    assert response.status_code == 200
    data = response.json
    assert data["success"] is True
    assert "item_id" in data["data"]
    assert "manifestation_id" in data["data"]
    assert data["error"] is None
