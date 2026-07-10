# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Allegro API metadata fetcher for retail physical media items."""

import json
import logging
import os
import time
from typing import Any

import requests

from app.config import Config

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 3
_READ_TIMEOUT: int = 7
_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".allegro_token.json")

# Allegro requires a specific User-Agent format to avoid 403 EDGE_REQUEST_REJECTED errors:
# ApplicationName/Version (+DocumentationURL)
_USER_AGENT: str = f"iqoqo/{Config.VERSION} (+https://iqoqo.cc)"


def get_allegro_token() -> str | None:
    """Authenticate with Allegro using User Context (if available) or Client Credentials flow."""
    client_id = os.getenv("ALLEGRO_CLIENT_ID")
    client_secret = os.getenv("ALLEGRO_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    auth_headers = {"User-Agent": _USER_AGENT}

    # Check for User Context token from Authorization Code flow first
    if os.path.isfile(_TOKEN_FILE):
        try:
            with open(_TOKEN_FILE, encoding="utf-8") as f:
                tokens = json.load(f)

            # Check if token needs refresh (if Allegro doesn't provide expires_at, assume 12h lifespan)
            # Simplest approach: Always try to refresh if it fails, but here we can just return it
            # and let the calling function handle 401 Unauthorized by triggering a refresh.
            # To be safe, we'll try to refresh proactively if it's older than 11 hours.
            file_mtime = os.path.getmtime(_TOKEN_FILE)
            if time.time() - file_mtime > 11 * 3600:
                auth_url = "https://allegro.pl/auth/oauth/token"
                data = {"grant_type": "refresh_token", "refresh_token": tokens.get("refresh_token")}
                response = requests.post(
                    auth_url,
                    auth=(client_id, client_secret),
                    data=data,
                    headers=auth_headers,
                    timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                )
                response.raise_for_status()
                new_tokens = response.json()
                with open(_TOKEN_FILE, "w", encoding="utf-8") as wf:
                    json.dump(new_tokens, wf)
                new_access_token = new_tokens.get("access_token")
                return new_access_token if isinstance(new_access_token, str) else None

            access_token = tokens.get("access_token")
            return access_token if isinstance(access_token, str) else None
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Failed to load or refresh User Context Allegro token from file: %s", e)

    # Fallback to Client Credentials
    try:
        auth_url = "https://allegro.pl/auth/oauth/token"
        response = requests.post(
            auth_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers=auth_headers,
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

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.allegro.public.v1+json",
        "User-Agent": _USER_AGENT,
    }

    try:
        # Step 1: Try Product Catalog as User (Preferred for clean metadata)
        # Use mode=GTIN only if barcode looks like a real EAN/UPC
        is_numeric_barcode = barcode.isdigit() and len(barcode) in (8, 10, 12, 13, 14)
        catalog_params = {"phrase": barcode}
        if is_numeric_barcode:
            catalog_params["mode"] = "GTIN"

        try:
            catalog_url = "https://api.allegro.pl/sale/products"
            cat_resp = requests.get(catalog_url, headers=headers, params=catalog_params, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
            if cat_resp.status_code == 200:
                cat_data = cat_resp.json()
                products = cat_data.get("products", [])
                if products:
                    item = products[0]
                    desc_obj = item.get("description")
                    desc_text = None
                    if isinstance(desc_obj, dict) and "sections" in desc_obj:
                        texts = []
                        for section in desc_obj.get("sections", []):
                            for section_item in section.get("items", []):
                                if section_item.get("type") == "TEXT" and section_item.get("content"):
                                    texts.append(section_item.get("content"))
                        desc_text = "\n".join(texts) if texts else None
                    elif isinstance(desc_obj, str):
                        desc_text = desc_obj

                    return {
                        "title": item.get("name", "Unknown Media"),
                        "barcode": barcode,
                        "cover_url": item.get("images", [{}])[0].get("url") if item.get("images") else None,
                        "description": desc_text,
                        "publisher": item.get("publication") and item.get("publication").get("publisher"),
                        "affiliate_url": f"https://allegro.pl/listing?string={barcode}",
                        "source": "Allegro Catalog",
                    }
        except requests.exceptions.RequestException:
            pass  # Fall back to Listing if Catalog fails

        # Step 2: Use Listing API (Public Marketplace Search)
        # ONLY if catalog found nothing and we are NOT getting 403s
        # Note: listing API is often 403 for Client Credentials; we only try if we have a real token
        if os.path.isfile(_TOKEN_FILE):
            listing_url = "https://api.allegro.pl/offers/listing"
            listing_params = {"phrase": barcode}
            response = requests.get(listing_url, headers=headers, params=listing_params, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", {})
                offers = items.get("promoted", []) + items.get("regular", [])
                if offers:
                    offer = offers[0]
                    return {
                        "title": offer.get("name", "Unknown Media"),
                        "barcode": barcode,
                        "cover_url": offer.get("images", [{}])[0].get("url") if offer.get("images") else None,
                        "affiliate_url": f"https://allegro.pl/listing?string={barcode}",
                        "source": "Allegro Listing",
                    }
            elif response.status_code == 403:
                logger.debug("Allegro Listing API returned 403; skipping fallback.")
    except requests.exceptions.Timeout:
        logger.warning("Allegro lookup timed out for barcode %s", barcode)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(
                "Allegro API returned 403 Forbidden. Check if your Client ID/Secret are valid and if the Public Listing API is accessible for your app type."
            )
        else:
            logger.warning("Allegro lookup HTTP error %s for barcode %s", e.response.status_code, barcode)
    except requests.exceptions.RequestException as e:
        logger.warning("Allegro lookup network error for barcode %s: %s", barcode, e)
    except (ValueError, KeyError, IndexError, AttributeError, TypeError, OSError, RuntimeError):
        logger.exception("Allegro lookup unexpected error for barcode %s", barcode)
    return None
