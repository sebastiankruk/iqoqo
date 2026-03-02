from unittest.mock import MagicMock, patch

import pytest

from app.utils.isbn import fetch_isbn_metadata
from app.utils.llm_covers import build_context


def test_build_context():
    """Test that LLM context string is built correctly."""
    assert build_context("", "") == ""
    assert build_context("A story about a hobbit.", "Fantasy") == " Genre: Fantasy. Theme/Description: A story about a hobbit.."

    long_desc = "A" * 500
    ctx = build_context(long_desc, "")
    assert len(ctx) <= 350  # Should be trimmed + prefix
    assert "Theme/Description" in ctx


@patch("app.utils.isbn._lookup_google_books")
def test_fetch_isbn_metadata_rich(mock_gb):
    """Test that fetch_isbn_metadata returns rich metadata."""
    mock_gb.return_value = {
        "Title": "Test Book",
        "Authors": ["Test Author"],
        "Description": "A test description",
        "Categories": ["Fiction"],
        "Source": "Google Books",
        "publisher": "Test Pub",
    }

    meta = fetch_isbn_metadata("9780000000000")
    assert meta["Description"] == "A test description"
    assert meta["Categories"] == ["Fiction"]
    assert meta["publisher"] == "Test Pub"


def test_refetch_metadata_endpoint(client, app):
    """Test the refetch-metadata endpoint."""
    # Create a dummy manifestation
    from app.db.models import Expression, Manifestation, Work, db

    with app.app_context():
        w = Work(title="Old Title", meta={"authors": ["Old Author"]})
        db.session.add(w)
        e = Expression(work=w)
        db.session.add(e)
        m = Manifestation(expression=e, isbn13="9780000000000", meta={})
        db.session.add(m)
        db.session.commit()
        mid = m.id

    with patch("app.utils.isbn.fetch_isbn_metadata") as mock_fetch:
        mock_fetch.return_value = {"Title": "New Title", "Authors": ["New Author"], "Description": "New Desc", "Categories": ["New Cat"]}

        resp = client.post(f"/api/manifestations/{mid}/refetch-metadata")
        assert resp.status_code == 200
        assert resp.json["success"] is True
        resp = client.post(f"/api/manifestations/{mid}/refetch-metadata")
        assert resp.status_code == 200
        assert resp.json["success"] is True
