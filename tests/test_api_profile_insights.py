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
"""Tests for profile insights API endpoints and cover provenance enhancements."""

import os

from PIL import Image

from app.utils.covers import add_source_badge, generate_fallback_cover


def test_insights_velocity_unauthenticated(client):
    """Verify velocity endpoint returns 401 for unauthenticated requests."""
    res = client.get("/api/profile/insights/velocity")
    assert res.status_code == 401


def test_insights_velocity_authenticated(client, normal_user_headers):
    """Verify velocity endpoint returns 12 months of acquisition data for authenticated user."""
    res = client.get("/api/profile/insights/velocity", headers=normal_user_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    items = data["data"]
    assert isinstance(items, list)
    assert len(items) == 12
    for entry in items:
        assert "month" in entry
        assert "count" in entry
        assert isinstance(entry["count"], int)


def test_insights_distribution_unauthenticated(client):
    """Verify distribution endpoint returns 401 for unauthenticated requests."""
    res = client.get("/api/profile/insights/distribution")
    assert res.status_code == 401


def test_insights_distribution_authenticated(client, normal_user_headers):
    """Verify distribution endpoint returns by_type and by_format arrays."""
    res = client.get("/api/profile/insights/distribution", headers=normal_user_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    dist = data["data"]
    assert "by_type" in dist
    assert "by_format" in dist
    assert isinstance(dist["by_type"], list)
    assert isinstance(dist["by_format"], list)


def test_generate_fallback_cover_enhancement(app):
    """Verify generate_fallback_cover produces a valid, deterministic JPEG image."""
    with app.app_context():
        res = generate_fallback_cover("test_isbn_123", "Test Title", "Test Author")
        assert res is not None
        url, source = res
        assert source == "fallback_pil"
        assert "test_isbn_123_generated.jpg" in url

        from app.utils.covers import COVERS_DIR

        filepath = os.path.join(COVERS_DIR, "test_isbn_123_generated.jpg")
        assert os.path.exists(filepath)

        with Image.open(filepath) as img:
            assert img.format == "JPEG"
            assert img.size == (600, 900)


def test_add_source_badge_new_providers(tmp_path):
    """Verify add_source_badge handles new providers api_musicbrainz and api_tmdb without errors."""
    img_path = str(tmp_path / "test_badge.jpg")
    img = Image.new("RGB", (200, 300), color="blue")
    img.save(img_path)

    add_source_badge(img_path, "api_musicbrainz")
    assert os.path.exists(img_path)

    add_source_badge(img_path, "api_tmdb")
    assert os.path.exists(img_path)

    with Image.open(img_path) as result_img:
        assert result_img.size == (200, 300)


def test_velocity_returns_empty_array_for_user_with_no_items(client, guest_user_headers):
    """User with 0 items gets velocity: [] shape from velocity endpoint."""
    res = client.get("/api/profile/insights/velocity", headers=guest_user_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    items = data["data"]
    assert isinstance(items, list)
    assert len(items) == 12
    for entry in items:
        assert entry["count"] == 0


def test_distribution_returns_empty_arrays_for_user_with_no_items(client, guest_user_headers):
    """User with 0 items gets by_type: [], by_format: [] from distribution endpoint."""
    res = client.get("/api/profile/insights/distribution", headers=guest_user_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    dist = data["data"]
    assert dist["by_type"] == []
    assert dist["by_format"] == []
