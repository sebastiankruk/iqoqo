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
