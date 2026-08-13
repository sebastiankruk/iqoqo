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
from unittest.mock import MagicMock, patch

import pytest

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Manifestation, Permission, Role, User, Work, db
from app.utils.isbn import fetch_isbn_metadata
from app.utils.llm_covers import build_context


@pytest.fixture
def admin_headers(app):
    """Fixture to provide authorization headers for an admin user."""
    with app.app_context():
        # Create permissions
        perms = [Permission(name="refetch:metadata")]
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


def test_build_context():
    """Test that LLM context string is built correctly."""
    assert build_context("", "") == ""
    assert build_context("A story about a hobbit.", "Fantasy") == " Genre: Fantasy. Theme/Description: A story about a hobbit.."

    long_desc = "A" * 500
    ctx = build_context(long_desc, "")
    assert len(ctx) <= 350  # Should be trimmed + prefix
    assert "Theme/Description" in ctx


@patch("app.utils.isbn._lookup_google_books_outcome")
def test_fetch_isbn_metadata_rich(mock_gb_outcome):
    """Test that fetch_isbn_metadata returns rich metadata."""
    from app.utils.isbn import ISBNProviderOutcome, ISBNProviderOutcomeStatus

    mock_gb_outcome.return_value = ISBNProviderOutcome(
        status=ISBNProviderOutcomeStatus.SUCCESS,
        metadata={
            "Title": "Test Book",
            "Authors": ["Test Author"],
            "Description": "A test description",
            "Categories": ["Fiction"],
            "Source": "Google Books",
            "publisher": "Test Pub",
        },
    )

    meta = fetch_isbn_metadata("9780000000000")
    assert meta["Description"] == "A test description"
    assert meta["Categories"] == ["Fiction"]
    assert meta["publisher"] == "Test Pub"


def test_refetch_metadata_endpoint(client, app, admin_headers):
    """Test the refetch-metadata endpoint."""
    # Create a dummy manifestation

    with app.app_context():
        w = Work(title="Old Title", meta={"authors": ["Old Author"]})
        db.session.add(w)
        e = Expression(work=w)
        db.session.add(e)
        m = Manifestation(expression=e, isbn13="9780553380163", meta={})
        db.session.add(m)
        db.session.commit()
        mid = m.id

    with patch("app.utils.isbn.fetch_isbn_metadata") as mock_fetch:
        mock_fetch.return_value = {"Title": "New Title", "Authors": ["New Author"], "Description": "New Desc", "Categories": ["New Cat"]}

        resp = client.post(f"/api/manifestations/{mid}/refetch-metadata", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json["success"] is True


def test_refetch_metadata_null_isbn_with_meta_fallback(client, app, admin_headers):
    """Test the refetch-metadata endpoint fallback when isbn13 column is NULL but meta contains it."""
    with app.app_context():
        w = Work(title="Old Title", meta={"authors": ["Old Author"]})
        db.session.add(w)
        e = Expression(work=w)
        db.session.add(e)
        m = Manifestation(expression=e, isbn13=None, meta={"isbn": "9780553380163"})
        db.session.add(m)
        db.session.commit()
        mid = m.id

    with patch("app.utils.isbn.fetch_isbn_metadata") as mock_fetch:
        mock_fetch.return_value = {"Title": "New Title", "Authors": ["New Author"], "Description": "New Desc", "Categories": ["New Cat"]}

        resp = client.post(f"/api/manifestations/{mid}/refetch-metadata", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json["success"] is True

        # Verify database column was healed (populated with canonical ISBN)
        with app.app_context():
            updated_m = db.session.get(Manifestation, mid)
            assert updated_m.isbn13 == "9780553380163"
