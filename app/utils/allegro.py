# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Allegro API metadata fetcher for retail physical media items."""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 10
_READ_TIMEOUT: int = 30


def get_allegro_token() -> str | None:
    """Authenticate with Allegro using Client Credentials flow."""
    client_id = os.getenv("ALLEGRO_CLIENT_ID")
    client_secret = os.getenv("ALLEGRO_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    try:
        auth_url = "https://allegro.pl/auth/oauth/token"
        response = requests.post(
            auth_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        return str(token) if isinstance(token, str) else None
    except requests.RequestException as e:
        logger.warning("Failed to obtain Allegro access token: %s", e)
        return None


def fetch_allegro_metadata(barcode: str) -> dict[str, Any] | None:
    """Fetch product metadata using Allegro API based on EAN/UPC."""
    token = get_allegro_token()
    if not token:
        return None

    # Use Allegro's product catalog endpoint, searching by GTIN/EAN
    url = f"https://api.allegro.pl/sale/products?ean={barcode}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.allegro.public.v1+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        data = response.json()

        products = data.get("products", [])
        if not products:
            return None

        item = products[0]

        return {
            "title": item.get("name", "Unknown Media"),
            "barcode": barcode,
            "cover_url": item.get("images", [{}])[0].get("url") if item.get("images") else None,
            "description": item.get("description"),
            "publisher": item.get("publication") and item.get("publication").get("publisher"),
            "affiliate_url": f"https://allegro.pl/listing?string={barcode}",  # Basic fallback; replace with actual affiliate generator
            "source": "Allegro",
        }
    except requests.RequestException as e:
        logger.exception("Allegro GTIN lookup failed for barcode %s: %s", barcode, e)
        return None
