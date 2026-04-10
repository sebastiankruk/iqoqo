# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from unittest.mock import patch

from app.utils.upc import fetch_upc_metadata, resolve_physical_media


@patch("app.utils.upc.requests.get")
def test_fetch_upc_metadata_success(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "items": [
            {"title": "Starry Night 1000pc", "upc": "4005556199999", "brand": "Ravensburger", "images": ["http://example.com/cover.jpg"]}
        ]
    }

    result = fetch_upc_metadata("4005556199999")

    assert result is not None
    assert result["title"] == "Starry Night 1000pc"
    assert result["manufacturer"] == "Ravensburger"
    assert result["source"] == "upcitemdb"


@patch("app.utils.upc.requests.get")
def test_fetch_upc_metadata_not_found(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"items": []}

    result = fetch_upc_metadata("0000000000000")
    assert result is None


@patch("app.utils.upc.fetch_allegro_metadata")
@patch("app.utils.upc.fetch_upc_metadata")
@patch("app.utils.upc.fetch_upcdatabase_org")
def test_waterfall_resolution_full_pipeline(mock_upcdb, mock_upcitem, mock_allegro):
    # Tier 1a fails
    mock_upcdb.return_value = None
    # Tier 1b succeeds but lacks a cover image
    mock_upcitem.return_value = {"title": "Matrix DVD 1999", "barcode": "123456"}
    # Tier 2 (Allegro) provides the missing cover
    mock_allegro.return_value = {"title": "Matrix", "cover_url": "http://allegro.pl/matrix.jpg", "affiliate_url": "link"}

    result = resolve_physical_media("123456")

    assert result is not None
    assert result["title"] == "Matrix DVD 1999"  # Keeps original manifestation title
    assert result["cover_url"] == "http://allegro.pl/matrix.jpg"  # Enriched cover
