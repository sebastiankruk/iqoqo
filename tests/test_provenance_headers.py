# tests/test_provenance_headers.py
"""Tests for cover provenance headers."""

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

import pytest

from app.db.models import Expression, Manifestation, Work, db
from app.utils.covers import COVERS_DIR


@pytest.fixture
def manifestation_with_cover(app):
    """Fixture to create a manifestation with a cover for provenance testing."""
    with app.app_context():
        w = Work(title="Provenance Test")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="text", language="en")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(
            expression_id=e.id,
            isbn13="1234567890123",
            cover_url="/static/covers/1234567890123_test.jpg",
            meta={"cover_source": "test_provenance"},
        )
        db.session.add(m)
        db.session.commit()

        # Create physical file
        filename = "1234567890123_test.jpg"
        filepath = os.path.join(COVERS_DIR, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(b"dummy image data")

        yield m, filename

        # Cleanup
        if os.path.exists(filepath):
            os.remove(filepath)


def test_serve_cover_provenance_headers_get(client, manifestation_with_cover):
    """Test that provenance headers are correctly injected in GET requests when requested."""
    m, filename = manifestation_with_cover

    # CASE 1: With query parameter
    response = client.get(f"/api/static/covers/{filename}?include=provenance")

    assert response.status_code == 200
    assert response.headers.get("X-Manifestation-ID") == str(m.id)
    assert response.headers.get("X-Image-Source") == "test_provenance"
    assert "X-Manifestation-ID" in response.headers.get("Access-Control-Expose-Headers")
    assert "X-Image-Source" in response.headers.get("Access-Control-Expose-Headers")

    # CASE 2: With request header
    response = client.get(f"/api/static/covers/{filename}", headers={"X-Include-Provenance": "1"})
    assert response.status_code == 200
    assert response.headers.get("X-Manifestation-ID") == str(m.id)

    # CASE 3: Without trigger (Performance Guard)
    response = client.get(f"/api/static/covers/{filename}")
    assert response.status_code == 200
    assert response.headers.get("X-Manifestation-ID") is None


def test_serve_cover_provenance_headers_head(client, manifestation_with_cover):
    """Test that provenance headers are correctly injected in HEAD requests when requested."""
    m, filename = manifestation_with_cover

    response = client.head(f"/api/static/covers/{filename}?include=provenance")

    assert response.status_code == 200
    assert response.headers.get("X-Manifestation-ID") == str(m.id)
    assert response.headers.get("X-Image-Source") == "test_provenance"


def test_serve_cover_provenance_headers_isbn_fallback(client, manifestation_with_cover):
    """Test that provenance headers work via ISBN fallback when filename doesn't match path."""
    m, filename = manifestation_with_cover

    # We rename the physical file to something that doesn't match the DB cover_url
    # but still has the ISBN prefix
    new_filename = "1234567890123_different.jpg"
    old_filepath = os.path.join(COVERS_DIR, filename)
    new_filepath = os.path.join(COVERS_DIR, new_filename)

    os.rename(old_filepath, new_filepath)
    try:
        response = client.get(f"/api/static/covers/{new_filename}?include=provenance")

        assert response.status_code == 200
        # Should match via isbn13="1234567890123" extracted from "1234567890123_different.jpg"
        assert response.headers.get("X-Manifestation-ID") == str(m.id)
        assert response.headers.get("X-Image-Source") == "test_provenance"
    finally:
        if os.path.exists(new_filepath):
            os.remove(new_filepath)
