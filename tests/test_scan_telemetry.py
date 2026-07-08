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

from unittest.mock import MagicMock, patch

import pytest

from app.db.models import Manifestation, ScanTelemetry, db


def test_lookup_barcode_preview_records_telemetry(client, admin_headers):
    """Test that barcode lookup records success telemetry in DB."""
    barcode = "9783161484100"  # Valid ISBN-13

    # Mocking external metadata fetch to avoid network calls
    with patch("app.strategies.book.fetch_isbn_metadata") as mock_fetch:
        mock_fetch.return_value = {"Title": "Test Book", "Authors": ["Test Author"], "format": "BOOK"}

        response = client.get(f"/api/lookup/{barcode}?format=book", headers=admin_headers)
        assert response.status_code == 200

        # Verify telemetry record
        telemetry = ScanTelemetry.query.filter_by(barcode=barcode).first()
        assert telemetry is not None
        assert telemetry.status == "success"
        assert telemetry.format_hint == "book"


def test_lookup_barcode_preview_records_failure_telemetry(client, admin_headers):
    """Test that failed barcode lookup records failure telemetry in DB."""
    barcode = "9780000000002"  # Correct check digit but unknown

    with (
        patch("app.strategies.book.fetch_isbn_metadata") as mock_fetch,
        patch("app.strategies.book.fetch_allegro_metadata") as mock_allegro,
        patch("app.strategies.book.fetch_discogs_metadata") as mock_discogs,
        patch("app.strategies.book.fetch_audio_metadata") as mock_audio,
    ):
        mock_fetch.return_value = None
        mock_allegro.return_value = None
        mock_discogs.return_value = None
        mock_audio.return_value = None

        response = client.get(f"/api/lookup/{barcode}?format=book", headers=admin_headers)
        assert response.status_code == 404

        # Verify telemetry record
        telemetry = ScanTelemetry.query.filter_by(barcode=barcode).first()
        assert telemetry is not None
        assert telemetry.status == "failed"


def test_scan_barcode_records_telemetry_with_manifestation(client, admin_headers):
    """Test that scanning a barcode records telemetry with manifestation_id."""
    barcode = "9781234567890"

    with patch("app.core.ingest.IngestService.ingest_from_isbn") as mock_ingest:
        # Create a mock manifestation
        mock_manif = MagicMock(spec=Manifestation)
        mock_manif.id = 123
        mock_manif.meta = {"title": "Scan Test"}
        mock_ingest.return_value = mock_manif

        response = client.post("/api/scan", json={"barcode": barcode, "format": "book"}, headers=admin_headers)
        assert response.status_code == 201

        # Verify telemetry record
        telemetry = ScanTelemetry.query.filter_by(barcode=barcode, status="success").first()
        assert telemetry is not None
        assert telemetry.manifestation_id == 123
