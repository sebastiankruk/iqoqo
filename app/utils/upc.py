# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Universal UPC/EAN metadata fetcher orchestrating the waterfall strategy."""

import logging
import os
from typing import Any

import requests

from app.utils.allegro import fetch_allegro_metadata
from app.utils.tmdb import clean_video_title, fetch_video_metadata

logger = logging.getLogger(__name__)

_TIMEOUT = 5


def fetch_upcdatabase_org(barcode: str) -> dict[str, Any] | None:
    """Tier 1a: Fetch from upcdatabase.org (Open, Free).."""
    api_key = os.getenv("UPC_DATABASE_ORG_KEY")
    if not api_key:
        return None

    try:
        url = f"https://api.upcdatabase.org/product/{barcode}?apikey={api_key}"
        response = requests.get(url, timeout=_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return {
                    "title": data.get("title") or data.get("alias"),
                    "barcode": barcode,
                    "description": data.get("description"),
                    "manufacturer": data.get("brand"),
                    "source": "upcdatabase.org",
                }
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("upcdatabase.org lookup failed for barcode %s", barcode)
    return None


def fetch_upc_metadata(barcode: str) -> dict[str, Any] | None:
    """Tier 1b: Fetch product metadata using UPCitemdb (High Quality, Strict Rate Limits)."""
    api_key = os.getenv("UPC_ITEM_DB_KEY")
    try:
        if api_key:
            url = f"https://api.upcitemdb.com/prod/v1/lookup?upc={barcode}"
            response = requests.get(url, headers={"user_key": api_key, "Accept": "application/json"}, timeout=_TIMEOUT)
        else:
            # Fallback to trial endpoint (no key required, limited rate)
            url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
            response = requests.get(url, timeout=_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            if data.get("items") and len(data["items"]) > 0:
                item = data["items"][0]
                return {
                    "title": item.get("title", "Unknown Item"),
                    "barcode": item.get("upc") or item.get("ean"),
                    "cover_url": (item.get("images") or [None])[0],
                    "description": item.get("description"),
                    "manufacturer": item.get("brand"),
                    "publisher": item.get("brand"),
                    "source": "upcitemdb",
                }
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("UPCitemdb lookup failed for barcode %s", barcode)
    return None


def resolve_physical_media(barcode: str) -> dict[str, Any] | None:
    """
    Orchestrates the UPC Waterfall Strategy for Physical Media:
    1. upcdatabase.org (Fast, Free)
    2. upcitemdb (High Quality)
    3. Allegro (Retail Manifestation & Covers)
    4. TMDB (Cinematic Work Metadata)
    """
    manifestation_data = None

    # Tier 1a: upcdatabase.org
    manifestation_data = fetch_upcdatabase_org(barcode)

    # Tier 1b: upcitemdb (Fallback if Tier 1a fails)
    if not manifestation_data:
        manifestation_data = fetch_upc_metadata(barcode)

    # Tier 2: Allegro (Fallback if missing or if we need better covers/affiliate links)
    if not manifestation_data or not manifestation_data.get("cover_url"):
        allegro_data = fetch_allegro_metadata(barcode)
        if allegro_data:
            if not manifestation_data:
                manifestation_data = allegro_data
            else:
                # Enrich existing open data with Retail data
                manifestation_data["cover_url"] = allegro_data.get("cover_url") or manifestation_data.get("cover_url")
                manifestation_data["affiliate_url"] = allegro_data.get("affiliate_url")

    # If we couldn't resolve a title, the waterfall fails entirely
    if not manifestation_data or not manifestation_data.get("title"):
        return None

    # Tier 3: TMDB (Fetch Work/Expression Cinematic Metadata)
    title_clean = clean_video_title(manifestation_data["title"])
    tmdb_data = fetch_video_metadata(title_clean)

    if tmdb_data:
        manifestation_data["work"] = tmdb_data

    return manifestation_data
