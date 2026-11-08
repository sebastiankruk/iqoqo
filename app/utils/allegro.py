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
import re
import time
import urllib.parse
from typing import Any, cast

import requests

from app.config import Config
from app.core.telemetry import record_outbound_telemetry

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 3
_READ_TIMEOUT: int = 7

DEVICE_AUTH_URL = "https://allegro.pl/auth/oauth/device"
TOKEN_URL = "https://allegro.pl/auth/oauth/token"
GRANT_TYPE_DEVICE = "urn:ietf:params:oauth:grant-type:device_code"


def get_allegro_user_agent() -> str:
    """Return Allegro User-Agent header string formatted per Allegro API specification.

    Format: ``{Config.ALLEGRO_APP_NAME}/{Config.VERSION} (+https://iqoqo.cc)``
    """
    return f"{Config.ALLEGRO_APP_NAME}/{Config.VERSION} (+https://iqoqo.cc)"


def save_allegro_token(tokens: dict[str, Any]) -> None:
    """Save Allegro OAuth token dictionary to cache and database."""
    from sqlalchemy.exc import DBAPIError, SQLAlchemyError

    from app.core.cache import cache
    from app.db.models import InstanceSettings

    token_data = dict(tokens)
    if "created_at" not in token_data:
        token_data["created_at"] = time.time()

    try:
        cache.set("allegro_token_data", token_data, timeout=86400)
    except (RuntimeError, KeyError, TypeError, ValueError, OSError) as e:
        logger.debug("Failed to store Allegro token in cache: %s", e)

    try:
        InstanceSettings.set_value("ALLEGRO_TOKEN_DATA", token_data)
    except (SQLAlchemyError, DBAPIError, RuntimeError, KeyError, TypeError, ValueError, OSError) as e:
        logger.debug("Failed to store Allegro token in InstanceSettings: %s", e)


def load_allegro_token() -> dict[str, Any] | None:
    """Load Allegro OAuth token dictionary from cache or database."""
    from sqlalchemy.exc import DBAPIError, SQLAlchemyError

    from app.core.cache import cache
    from app.db.models import InstanceSettings

    try:
        cached = cache.get("allegro_token_data")
        if cached and isinstance(cached, dict) and cached.get("access_token"):
            return cast(dict[str, Any], cached)
    except (RuntimeError, KeyError, TypeError, ValueError, OSError) as e:
        logger.debug("Failed to read Allegro token from cache: %s", e)

    try:
        db_token = InstanceSettings.get_value("ALLEGRO_TOKEN_DATA")
        if db_token and isinstance(db_token, dict) and db_token.get("access_token"):
            try:
                cache.set("allegro_token_data", db_token, timeout=86400)
            except (RuntimeError, KeyError, TypeError, ValueError, OSError):
                pass
            return cast(dict[str, Any], db_token)
    except (SQLAlchemyError, DBAPIError, RuntimeError, KeyError, TypeError, ValueError, OSError) as e:
        logger.debug("Failed to read Allegro token from InstanceSettings: %s", e)

    return None


def has_allegro_user_token() -> bool:
    """Return True if a User Context OAuth token is present in central store."""
    tokens = load_allegro_token()
    return bool(tokens and isinstance(tokens, dict) and tokens.get("access_token"))


def get_allegro_token_status() -> dict[str, Any]:
    """Check Allegro configuration and token freshness."""
    from app.db.models import InstanceSettings

    try:
        client_id = os.getenv("ALLEGRO_CLIENT_ID") or InstanceSettings.get_value("ALLEGRO_CLIENT_ID")
        client_secret = os.getenv("ALLEGRO_CLIENT_SECRET") or InstanceSettings.get_value("ALLEGRO_CLIENT_SECRET")
    except Exception as e:
        return {
            "configured": False,
            "allegro_token_active": False,
            "reason": "probe_error",
            "token_age_hours": None,
            "error": str(e),
        }

    if not client_id or not client_secret:
        return {
            "configured": False,
            "allegro_token_active": False,
            "reason": "not_configured",
            "token_age_hours": None,
        }

    try:
        tokens = load_allegro_token()
    except Exception as e:
        return {
            "configured": True,
            "allegro_token_active": False,
            "reason": "probe_error",
            "token_age_hours": None,
            "error": str(e),
        }

    if not tokens or not isinstance(tokens, dict) or not tokens.get("access_token"):
        return {
            "configured": True,
            "allegro_token_active": False,
            "reason": "handshake_pending",
            "token_age_hours": None,
        }

    created_at = tokens.get("created_at")
    age_hours: float | None = None
    if created_at:
        try:
            age_hours = round((time.time() - float(created_at)) / 3600.0, 1)
        except (ValueError, TypeError):
            age_hours = 0.0

    expires_in = tokens.get("expires_in", 43200)
    is_expired = (time.time() - float(created_at)) > float(expires_in) if created_at else False
    is_active = not is_expired or bool(tokens.get("refresh_token"))

    return {
        "configured": True,
        "allegro_token_active": is_active,
        "is_expired": is_expired,
        "token_age_hours": age_hours,
        "has_refresh_token": bool(tokens.get("refresh_token")),
        "reason": "active" if is_active else "expired",
    }


def initiate_device_flow(client_id: str, client_secret: str) -> dict[str, Any]:
    """Initiate Allegro Device Code flow."""
    auth_headers = {"User-Agent": get_allegro_user_agent()}
    response = requests.post(
        DEVICE_AUTH_URL,
        data={"client_id": client_id},
        auth=(client_id, client_secret),
        headers=auth_headers,
        timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


def exchange_device_token(device_code: str, client_id: str, client_secret: str) -> dict[str, Any]:
    """Attempt to exchange the device code for a token. Returns the JSON response."""
    auth_headers = {"User-Agent": get_allegro_user_agent()}
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": GRANT_TYPE_DEVICE,
            "device_code": device_code,
            "client_id": client_id,
        },
        auth=(client_id, client_secret),
        headers=auth_headers,
        timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
    )

    if response.ok:
        tokens = response.json()
        save_allegro_token(tokens)
        return cast(dict[str, Any], tokens)

    # If not ok, it might be authorization_pending, slow_down, expired_token, etc.
    try:
        err = response.json()
    except json.JSONDecodeError:
        response.raise_for_status()

    return cast(dict[str, Any], err)


def _refresh_user_token(tokens: dict[str, Any], client_id: str, client_secret: str, auth_headers: dict[str, str]) -> str | None:
    """Refresh user context OAuth token under distributed lock."""
    from app.core.cache import cache

    with cache.lock("allegro_refresh_lock", timeout=30):
        # Re-read token inside lock to verify another worker hasn't already refreshed it
        fresh_tokens = load_allegro_token()
        fresh_created_at = fresh_tokens.get("created_at") if isinstance(fresh_tokens, dict) else None
        fresh_age = (time.time() - float(fresh_created_at)) if fresh_created_at else None
        if (
            fresh_tokens
            and isinstance(fresh_tokens, dict)
            and fresh_age is not None
            and fresh_age <= 11 * 3600
            and fresh_tokens.get("access_token")
        ):
            access_token = fresh_tokens.get("access_token")
            return access_token if isinstance(access_token, str) else None

        current_refresh_token = (
            fresh_tokens.get("refresh_token")
            if isinstance(fresh_tokens, dict) and fresh_tokens.get("refresh_token")
            else tokens.get("refresh_token")
        )
        if not current_refresh_token:
            fallback_token = (fresh_tokens or tokens).get("access_token") if isinstance(fresh_tokens or tokens, dict) else None
            return fallback_token if isinstance(fallback_token, str) else None

        auth_url = "https://allegro.pl/auth/oauth/token"
        data = {"grant_type": "refresh_token", "refresh_token": current_refresh_token}
        record_outbound_telemetry("Allegro", auth_headers, url=auth_url)
        response = requests.post(
            auth_url,
            auth=(client_id, client_secret),
            data=data,
            headers=auth_headers,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        response.raise_for_status()
        new_tokens = response.json()
        save_allegro_token(new_tokens)
        new_access_token = new_tokens.get("access_token")
        return new_access_token if isinstance(new_access_token, str) else None


def get_allegro_token() -> str | None:
    """Authenticate with Allegro using User Context (if available) or Client Credentials flow."""
    from app.db.models import InstanceSettings

    client_id = os.getenv("ALLEGRO_CLIENT_ID") or InstanceSettings.get_value("ALLEGRO_CLIENT_ID")
    client_secret = os.getenv("ALLEGRO_CLIENT_SECRET") or InstanceSettings.get_value("ALLEGRO_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    auth_headers = {"User-Agent": get_allegro_user_agent()}

    # Check for User Context token from Authorization Code / Device flow first
    tokens = load_allegro_token()
    if tokens and isinstance(tokens, dict) and tokens.get("access_token"):
        try:
            created_at = tokens.get("created_at")
            token_age = (time.time() - float(created_at)) if created_at else 0
            if token_age > 11 * 3600 and tokens.get("refresh_token"):
                return _refresh_user_token(tokens, client_id, client_secret, auth_headers)

            access_token = tokens.get("access_token")
            return access_token if isinstance(access_token, str) else None
        except (requests.RequestException, ValueError, KeyError, OSError) as e:
            logger.warning("Failed to load or refresh User Context Allegro token from cache/DB: %s", e)

    # Fallback to Client Credentials
    try:
        auth_url = "https://allegro.pl/auth/oauth/token"
        record_outbound_telemetry("Allegro", auth_headers, url=auth_url)
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


def _extract_allegro_parameters(params: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract standard bibliographic and media fields from Allegro product/offer parameters."""
    barcode = None
    authors: list[str] = []
    clean_title: str | None = None
    publisher: str | None = None
    year: str | None = None
    genres: list[str] = []
    format_label: str | None = None
    language: str | None = None
    set_number: str | None = None
    piece_count: int | None = None
    theme: str | None = None

    for param in params or []:
        p_name = (param.get("name") or "").strip()
        vals = param.get("valuesLabels") or param.get("values") or []
        vals = [str(v).strip() for v in vals if v is not None and str(v).strip()]
        if not vals:
            continue

        if p_name in ("EAN", "ISBN", "GTIN", "Kod producenta"):
            if not barcode:
                barcode = vals[0]
            if p_name == "Kod producenta" and not set_number:
                if vals[0].isdigit() and len(vals[0]) in (4, 5, 6):
                    set_number = vals[0]
        elif p_name in ("Numer produktu", "Numer zestawu"):
            if not set_number:
                set_number = vals[0]
        elif p_name in ("Liczba elementów", "Liczba klocków"):
            if piece_count is None:
                try:
                    piece_count = int(re.sub(r"[^\d]", "", vals[0]))
                except (ValueError, TypeError):
                    pass
        elif p_name in ("Seria", "Linia"):
            if not theme:
                theme = vals[0]
        elif p_name in ("Autor", "Autorzy", "Wykonawca", "Twórca", "Reżyser"):
            authors.extend(vals)
        elif p_name in ("Tytuł", "Tytuł oryginalny"):
            if not clean_title:
                clean_title = vals[0]
        elif p_name in ("Wydawnictwo", "Wytwórnia", "Producent"):
            if not publisher:
                publisher = vals[0]
        elif p_name in ("Rok wydania", "Rok nagrania", "Rok"):
            if not year:
                year = vals[0]
        elif p_name in ("Gatunek",):
            genres.extend(vals)
        elif p_name in ("Nośnik", "Format"):
            if not format_label:
                format_label = vals[0]
        elif p_name in ("Język publikacji", "Język"):
            if not language:
                language = vals[0]

    seen: set[str] = set()
    unique_authors: list[str] = []
    for a in authors:
        a_clean = a.strip().rstrip(",;.")
        if a_clean and a_clean not in seen:
            seen.add(a_clean)
            unique_authors.append(a_clean)

    return {
        "barcode": barcode,
        "authors": unique_authors,
        "author": unique_authors[0] if unique_authors else None,
        "title": clean_title,
        "publisher": publisher,
        "year": year,
        "genres": genres,
        "format": format_label,
        "language": language,
        "set_number": set_number,
        "piece_count": piece_count,
        "theme": theme,
    }


def _normalize_allegro_product(item: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Normalize a product item from Allegro Catalog API."""
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

    extracted = _extract_allegro_parameters(item.get("parameters", []))
    barcode = extracted["barcode"] or query

    pub_obj = item.get("publication")
    publisher = extracted["publisher"] or (pub_obj.get("publisher") if isinstance(pub_obj, dict) else None)

    return {
        "title": extracted["title"] or item.get("name", "Unknown Media"),
        "barcode": barcode,
        "cover_url": item.get("images", [{}])[0].get("url") if item.get("images") else None,
        "description": desc_text,
        "publisher": publisher,
        "author": extracted["author"],
        "authors": extracted["authors"],
        "year": extracted["year"],
        "genres": extracted["genres"],
        "format": extracted["format"],
        "language": extracted["language"],
        "set_number": extracted.get("set_number"),
        "piece_count": extracted.get("piece_count"),
        "theme": extracted.get("theme"),
        "affiliate_url": f"https://allegro.pl/listing?string={urllib.parse.quote_plus(str(barcode or query))}",
        "source": "Allegro Catalog",
        "data_source": "allegro",
        "raw_payload": item,
    }


def _normalize_allegro_offer(offer: dict[str, Any], query: str = "") -> dict[str, Any]:
    """Normalize an offer item from Allegro Listing API."""
    extracted = _extract_allegro_parameters(offer.get("parameters", []))
    barcode = extracted["barcode"] or query
    return {
        "title": extracted["title"] or offer.get("name", "Unknown Media"),
        "barcode": barcode,
        "cover_url": offer.get("images", [{}])[0].get("url") if offer.get("images") else None,
        "publisher": extracted["publisher"],
        "author": extracted["author"],
        "authors": extracted["authors"],
        "year": extracted["year"],
        "genres": extracted["genres"],
        "format": extracted["format"],
        "language": extracted["language"],
        "set_number": extracted.get("set_number"),
        "piece_count": extracted.get("piece_count"),
        "theme": extracted.get("theme"),
        "affiliate_url": f"https://allegro.pl/listing?string={urllib.parse.quote_plus(str(barcode or query))}",
        "source": "Allegro Listing",
        "data_source": "allegro",
        "raw_payload": offer,
    }


def fetch_allegro_candidates(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search Allegro product catalog and marketplace listing for candidates matching query.

    Args:
        query: Free-text search term (e.g. title or barcode).
        max_results: Maximum number of results to return (default 10).

    Returns:
        List of normalised metadata dicts, possibly empty.
    """
    token = get_allegro_token()
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.allegro.public.v1+json",
        "User-Agent": get_allegro_user_agent(),
    }

    candidates: list[dict[str, Any]] = []

    try:
        # Step 1: Try Product Catalog
        is_numeric_barcode = query.isdigit() and len(query) in (8, 10, 12, 13, 14)
        catalog_params: dict[str, Any] = {"phrase": query}
        if is_numeric_barcode:
            catalog_params["mode"] = "GTIN"

        try:
            catalog_url = "https://api.allegro.pl/sale/products"
            record_outbound_telemetry("Allegro", headers, url=catalog_url)
            cat_resp = requests.get(catalog_url, headers=headers, params=catalog_params, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
            if cat_resp.status_code == 200:
                cat_data = cat_resp.json()
                products = cat_data.get("products", [])
                for product in products[:max_results]:
                    candidates.append(_normalize_allegro_product(product, query))
        except requests.exceptions.RequestException:
            pass  # Fall back to Listing if Catalog fails

        # Step 2: Use Listing API (Public Marketplace Search) ONLY if catalog found nothing and user token is active
        if not candidates and has_allegro_user_token():
            listing_url = "https://api.allegro.pl/offers/listing"
            listing_params = {"phrase": query}
            record_outbound_telemetry("Allegro", headers, url=listing_url)
            response = requests.get(listing_url, headers=headers, params=listing_params, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", {})
                offers = items.get("promoted", []) + items.get("regular", [])
                for offer in offers:
                    if len(candidates) >= max_results:
                        break
                    candidates.append(_normalize_allegro_offer(offer, query))
            elif response.status_code == 403:
                logger.debug("Allegro Listing API returned 403; skipping fallback.")
    except requests.exceptions.Timeout:
        logger.warning("Allegro lookup timed out for query %s", query)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(
                "Allegro API returned 403 Forbidden. Check if your Client ID/Secret are valid and if the Public Listing API is accessible for your app type."
            )
        else:
            logger.warning("Allegro lookup HTTP error %s for query %s", e.response.status_code, query)
    except requests.exceptions.RequestException as e:
        logger.warning("Allegro lookup network error for query %s: %s", query, e)
    except (ValueError, KeyError, IndexError, AttributeError, TypeError, OSError, RuntimeError):
        logger.exception("Allegro lookup unexpected error for query %s", query)

    return candidates[:max_results]


def fetch_allegro_metadata(barcode: str, max_results: int = 10) -> dict[str, Any] | None:
    """Fetch product metadata using Allegro API based on EAN/UPC or query."""
    candidates = fetch_allegro_candidates(barcode, max_results=max_results)
    if not candidates:
        return None
    return cast(dict[str, Any], candidates[0])
