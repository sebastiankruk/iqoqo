# tests/test_step3_refinements.py
"""Tests for Step 3 UI Refinements: data_source injection and new statuses."""

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

from app.db.models import Item, Manifestation, db


def test_want_to_play_status_acceptance(client, normal_user_headers, app):
    """Verify that 'want_to_play' is accepted as a valid status for board games."""
    with app.app_context():
        from app.db.models import User

        user = User.query.filter_by(email="test_user@iqoqo.local").first()

        # Create a board game item
        from app.db.models import Expression, Work

        w = Work(title="Game Test")
        db.session.add(w)
        db.session.flush()
        e = Expression(work_id=w.id, content_type="boardgame")
        db.session.add(e)
        db.session.flush()
        m = Manifestation(expression_id=e.id)
        db.session.add(m)
        db.session.flush()

        item = Item(manifestation_id=m.id, owner_id=user.id, status="playing")
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Update status to want_to_play
    resp = client.put(f"/api/items/{item_id}", json={"status": "want_to_play"}, headers=normal_user_headers)
    assert resp.status_code == 200

    with app.app_context():
        updated_item = db.session.get(Item, item_id)
        assert updated_item.status == "want_to_play"


def test_data_source_injection_discogs(client, normal_user_headers, app):
    """Verify that Discogs lookups inject 'data_source': 'discogs' into meta."""
    with patch("app.strategies.audio.fetch_discogs_by_id") as mock_fetch:
        mock_fetch.return_value = {"title": "Test Discogs Release", "artist": "Test Artist", "thumb": "http://example.com/cover.jpg"}

        # Call lookup with audio hint
        resp = client.get("/api/lookup/12345?format=audio", headers=normal_user_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]

        assert data["data_source"] == "discogs"
        assert data["title"] == "Test Discogs Release"


def test_data_source_injection_barcode_tmdb(client, normal_user_headers, app):
    """Verify that barcode lookups for video inject 'data_source': 'tmdb'."""
    with (
        patch("app.strategies.video.resolve_physical_media") as mock_upc,
        patch("app.strategies.video.fetch_video_metadata") as mock_tmdb,
    ):
        mock_upc.return_value = {"title": "The Movie", "format": "DVD"}
        mock_tmdb.return_value = {"title": "The Movie (2024)", "year": "2024"}

        # Call lookup with video hint
        resp = client.get("/api/lookup/123456789012?format=video", headers=normal_user_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]

        assert data["data_source"] == "tmdb"
        assert data["title"] == "The Movie (2024)"


def test_data_source_injection_barcode_bgg(client, normal_user_headers, app):
    """Verify that barcode lookups for games inject 'data_source': 'bgg'."""
    with (
        patch("app.strategies.boardgame.resolve_physical_media") as mock_upc,
        patch("app.strategies.boardgame.fetch_bgg_metadata") as mock_bgg,
    ):
        mock_upc.return_value = {"title": "The Game", "format": "Board Game"}
        mock_bgg.return_value = {"title": "The Game (2nd Edition)", "min_players": 2}

        # Call lookup with boardgame hint
        resp = client.get("/api/lookup/123456789012?format=boardgame", headers=normal_user_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]

        assert data["data_source"] == "bgg"
        assert data["title"] == "The Game (2nd Edition)"


def test_data_source_injection_barcode_isbn(client, normal_user_headers, app):
    """Verify that barcode lookups for books expose the real metadata provider in data_source.

    The backend fetch_isbn_metadata sets meta['Source'] to 'Google Books' or
    'Open Library'. The scanner converts this to a snake_case data_source value.
    """
    with patch("app.strategies.book.fetch_isbn_metadata") as mock_isbn, patch("app.strategies.book.canonicalize_isbn") as mock_canon:
        mock_canon.return_value = "9781234567890"
        # Include the Source field that fetch_isbn_metadata always sets
        mock_isbn.return_value = {"title": "The Book", "authors": ["Me"], "Source": "Google Books"}

        # Call lookup with book hint
        resp = client.get("/api/lookup/9781234567890?format=book", headers=normal_user_headers)
        assert resp.status_code == 200
        data = resp.get_json()["data"]

        # data_source should now reflect the actual upstream provider
        assert data["data_source"] in {"google_books", "open_library"}
        assert data["title"] == "The Book"
