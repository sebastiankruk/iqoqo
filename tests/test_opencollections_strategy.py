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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Unit tests for SSRF-safe OpenCollections.org lookup strategy (C116)."""

from unittest.mock import MagicMock, patch

import requests

from app.strategies.opencollections import OpenCollectionsLookupStrategy
from app.utils.http_client import SSRFError


def test_opencollections_lookup_success_and_provenance():
    """Strategy normalizes creators, title, date, lod_links, and _provenance."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "oc-42",
        "uri": "https://opencollections.org/records/oc-42",
        "title": "Atlas of Imaginary Places",
        "creators": ["Alberto Manguel", "Gianni Guadalupi"],
        "publication_date": "1980",
        "publisher": "Macmillan",
        "format": "book",
        "isbn": "9780025793101",
    }

    with (
        patch("app.utils.opencollections.safe_get", return_value=mock_resp) as mock_get,
        patch("app.utils.opencollections.record_outbound_telemetry") as mock_tel,
    ):
        strategy = OpenCollectionsLookupStrategy()
        meta, provider = strategy.lookup("9780025793101")

    assert provider == "opencollections"
    assert meta is not None
    assert meta["Title"] == "Atlas of Imaginary Places"
    assert meta["Authors"] == ["Alberto Manguel", "Gianni Guadalupi"]
    assert meta["PublishedDate"] == "1980"
    assert meta["lod_links"] == {"opencollections_uri": "https://opencollections.org/records/oc-42"}
    assert meta["_provenance"]["Title"] == "opencollections"
    assert meta["_provenance"]["lod_links"] == "opencollections"
    assert mock_get.call_args.kwargs["timeout"] == (3.0, 5.0)
    mock_tel.assert_called_once()
    assert mock_tel.call_args.kwargs["provider"] == "opencollections"


def test_opencollections_ssrf_and_timeout_fail_gracefully():
    """SSRF errors and timeouts return (None, None) without hallucinating metadata."""
    strategy = OpenCollectionsLookupStrategy()

    with (
        patch("app.utils.opencollections.safe_get", side_effect=SSRFError("Blocked private IP")),
        patch("app.utils.opencollections.record_outbound_telemetry") as mock_tel,
    ):
        meta, provider = strategy.lookup("oc-ssrf-test")

    assert meta is None
    assert provider is None
    assert mock_tel.call_args.kwargs["error_type"] == "ssrf_blocked"

    with (
        patch("app.utils.opencollections.safe_get", side_effect=requests.Timeout("Read timed out")),
        patch("app.utils.opencollections.record_outbound_telemetry") as mock_tel2,
    ):
        meta2, provider2 = strategy.lookup("", query="Timeout Book")

    assert meta2 is None
    assert provider2 is None
    assert mock_tel2.call_args.kwargs["error_type"] == "Timeout"


def test_opencollections_search_candidates():
    """lookup_candidates parses list results and skips malformed entries."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {"id": "oc-1", "title": "Valid Entry", "authors": ["Author One"]},
            {"id": "oc-bad", "title": ""},  # Fails min_length=1
        ]
    }

    with (
        patch("app.utils.opencollections.safe_get", return_value=mock_resp),
        patch("app.utils.opencollections.record_outbound_telemetry"),
    ):
        strategy = OpenCollectionsLookupStrategy()
        candidates = strategy.lookup_candidates("Valid Entry", max_results=5)

    assert len(candidates) == 1
    assert candidates[0]["Title"] == "Valid Entry"
    assert candidates[0]["lod_links"]["opencollections_uri"] == "https://opencollections.org/records/oc-1"
