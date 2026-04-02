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
"""Tests for audio fetching and ingestion."""

from unittest.mock import patch

from app.core.ingest import IngestService


def test_fetch_audio_metadata_success(app):
    mock_response = {
        "title": "Dark Side of the Moon",
        "author": "Pink Floyd",
        "publisher": "Harvest",
        "cover_url": "https://coverartarchive.org/release/1234/front",
        "format": "audio"
    }

    with patch('app.core.ingest.fetch_audio_metadata', return_value=mock_response), \
         patch('app.core.ingest.fetch_discogs_metadata', return_value=None):
        with app.app_context():
            manifestation = IngestService.ingest_audio_from_barcode("5099902987613")

            assert manifestation.title == "Dark Side of the Moon"
            assert manifestation.meta["format"] == "audio"
            assert manifestation.meta["barcode"] == "5099902987613"
            assert "Pink Floyd" in manifestation.expression.work.meta["authors"]


def test_fetch_audio_metadata_not_found(app):
    with patch('app.core.ingest.fetch_audio_metadata', return_value=None), \
         patch('app.core.ingest.fetch_discogs_metadata', return_value=None):
        with app.app_context():
            try:
                IngestService.ingest_audio_from_barcode("00000000000")
                raise AssertionError("Should have raised ValueError")
            except ValueError as e:
                assert str(e) == "Audio metadata not found in external services."
