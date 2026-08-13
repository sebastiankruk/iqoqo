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

"""Tests for scan telemetry recording and oversized barcode handling."""

from app.api.scanner import _record_scan_telemetry
from app.db.models import ScanTelemetry, db


def test_record_scan_telemetry_oversized_barcode(app) -> None:
    """Verifies that an oversized barcode is truncated and recorded with status='rejected_oversized'."""
    long_barcode = "A" * 200
    with app.app_context():
        _record_scan_telemetry(
            barcode=long_barcode,
            format_hint="book",
            provider="test_provider",
            status="success",
        )

        record = ScanTelemetry.query.filter_by(provider="test_provider", status="rejected_oversized").first()
        assert record is not None
        assert record.status == "rejected_oversized"
        assert len(record.barcode) <= 128
        assert record.barcode == f"{'A' * 120}...(200)"
