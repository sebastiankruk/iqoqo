"""IGDB (Internet Game Database) metadata lookup utilities."""

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

import json
import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT: int = 3
_READ_TIMEOUT: int = 7
_TOKEN_FILE: str = os.path.join(os.path.dirname(__file__), "..", "..", ".igdb_token.json")


def get_igdb_token() -> str | None:
    """Obtains a client credentials OAuth token from Twitch and caches it locally."""
    from app.db.models import InstanceSettings

    client_id = (
        os.getenv("IGDB_CLIENT_ID")
        or os.getenv("TWITCH_CLIENT_ID")
        or InstanceSettings.get_value("IGDB_CLIENT_ID")
        or InstanceSettings.get_value("TWITCH_CLIENT_ID")
    )
    client_secret = (
        os.getenv("IGDB_CLIENT_SECRET")
        or os.getenv("TWITCH_CLIENT_SECRET")
        or InstanceSettings.get_value("IGDB_CLIENT_SECRET")
        or InstanceSettings.get_value("TWITCH_CLIENT_SECRET")
    )

    if not client_id or not client_secret:
        logger.warning("IGDB / Twitch Client ID or Secret not set in environment or database.")
        return None

    # Try loading cached token first
    if os.path.isfile(_TOKEN_FILE):
        try:
            with open(_TOKEN_FILE, encoding="utf-8") as f:
                tokens = json.load(f)
            file_mtime = os.path.getmtime(_TOKEN_FILE)
            expires_in = tokens.get("expires_in", 3600)
            # Proactively refresh if the token is within 1 hour of expiration
            if time.time() - file_mtime < expires_in - 3600:
                access_token = tokens.get("access_token")
                if isinstance(access_token, str):
                    return access_token
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning("Failed to load cached IGDB token: %s", e)

    # Request a new token
    try:
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }
        response = requests.post(url, data=data, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        new_tokens = response.json()
        token_fd = os.open(
            _TOKEN_FILE,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(token_fd, "w", encoding="utf-8") as wf:
            # os.open's mode only applies to new files; also tighten an existing
            # cache file before writing a newly fetched credential.
            os.fchmod(wf.fileno(), 0o600)
            json.dump(new_tokens, wf)
        access_token = new_tokens.get("access_token")
        return str(access_token) if isinstance(access_token, str) else None
    except requests.RequestException as e:
        logger.warning("Failed to obtain IGDB access token from Twitch: %s", e)
        return None


def get_igdb_token_status(probe_remote: bool = False) -> dict[str, Any]:
    """Check IGDB/Twitch configuration, token freshness, and health status.

    Returns a dict with 4-state health status:
    - DISABLED: credentials not set in environment or database.
    - CONFIGURED_VALID: credentials configured and cached token is valid.
    - EXPIRED_NEEDS_REFRESH: credentials configured but cached token is expired or absent.
    - AUTH_ERROR: Twitch OAuth returned 401/400 (invalid client credentials).
    """
    from app.db.models import InstanceSettings

    try:
        client_id = (
            os.getenv("IGDB_CLIENT_ID")
            or os.getenv("TWITCH_CLIENT_ID")
            or InstanceSettings.get_value("IGDB_CLIENT_ID")
            or InstanceSettings.get_value("TWITCH_CLIENT_ID")
        )
        client_secret = (
            os.getenv("IGDB_CLIENT_SECRET")
            or os.getenv("TWITCH_CLIENT_SECRET")
            or InstanceSettings.get_value("IGDB_CLIENT_SECRET")
            or InstanceSettings.get_value("TWITCH_CLIENT_SECRET")
        )
    except Exception as e:
        return {
            "status": "DISABLED",
            "configured": False,
            "active": False,
            "reason": "probe_error",
            "error": str(e),
        }

    if not client_id or not client_secret:
        return {
            "status": "DISABLED",
            "configured": False,
            "active": False,
            "reason": "missing_credentials",
        }

    cached_token = None
    is_expired = True
    token_age_hours: float | None = None

    if os.path.isfile(_TOKEN_FILE):
        try:
            with open(_TOKEN_FILE, encoding="utf-8") as f:
                tokens = json.load(f)
            file_mtime = os.path.getmtime(_TOKEN_FILE)
            expires_in = tokens.get("expires_in", 3600)
            age_sec = time.time() - file_mtime
            token_age_hours = round(age_sec / 3600.0, 1) if age_sec >= 0 else 0.0
            is_expired = age_sec >= expires_in
            cached_token = tokens.get("access_token")
        except (json.JSONDecodeError, OSError, KeyError):
            is_expired = True

    if not is_expired and cached_token:
        return {
            "status": "CONFIGURED_VALID",
            "configured": True,
            "active": True,
            "token_age_hours": token_age_hours,
            "reason": "token_valid",
        }

    if probe_remote:
        try:
            url = "https://id.twitch.tv/oauth2/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }
            response = requests.post(url, data=data, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
            if response.status_code in (400, 401, 403):
                return {
                    "status": "AUTH_ERROR",
                    "configured": True,
                    "active": False,
                    "reason": f"auth_failure_{response.status_code}",
                    "error": response.text,
                }
            response.raise_for_status()
            new_tokens = response.json()
            token_fd = os.open(
                _TOKEN_FILE,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            with os.fdopen(token_fd, "w", encoding="utf-8") as wf:
                os.fchmod(wf.fileno(), 0o600)
                json.dump(new_tokens, wf)

            return {
                "status": "CONFIGURED_VALID",
                "configured": True,
                "active": True,
                "token_age_hours": 0.0,
                "reason": "token_refreshed",
            }
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (400, 401, 403):
                return {
                    "status": "AUTH_ERROR",
                    "configured": True,
                    "active": False,
                    "reason": "invalid_credentials",
                    "error": str(e),
                }
            return {
                "status": "EXPIRED_NEEDS_REFRESH",
                "configured": True,
                "active": False,
                "token_age_hours": token_age_hours,
                "reason": "network_error_on_refresh",
                "error": str(e),
            }
        except requests.RequestException as e:
            return {
                "status": "EXPIRED_NEEDS_REFRESH",
                "configured": True,
                "active": False,
                "token_age_hours": token_age_hours,
                "reason": "network_error_on_refresh",
                "error": str(e),
            }

    return {
        "status": "EXPIRED_NEEDS_REFRESH",
        "configured": True,
        "active": False,
        "token_age_hours": token_age_hours,
        "reason": "token_expired" if cached_token else "token_missing",
    }


def fetch_game_metadata(query: str) -> dict[str, Any] | None:
    """Fetch video game metadata from IGDB using a title search."""
    if not query:
        return None

    client_id = os.getenv("IGDB_CLIENT_ID")
    token = get_igdb_token()

    if not client_id or not token:
        return None

    url = "https://api.igdb.com/v4/games"
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    # Escape backslashes first, then quotes, so attacker-supplied sequences
    # cannot consume the escaping applied to a quote.
    escaped_query = query.replace("\\", "\\\\").replace('"', '\\"')
    body = f'search "{escaped_query}"; fields name, cover.url, first_release_date, summary; limit 1;'

    try:
        response = requests.post(url, headers=headers, data=body, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        results = response.json()

        if not results:
            return None

        game = results[0]
        cover_data = game.get("cover")
        cover_url = None

        if cover_data and "url" in cover_data:
            raw_url = cover_data["url"]
            # Convert protocol-relative URL to secure HTTPS
            if raw_url.startswith("//"):
                raw_url = "https:" + raw_url
            # Scale up thumbnail size to t_cover_big
            cover_url = raw_url.replace("t_thumb", "t_cover_big")

        release_year = None
        release_timestamp = game.get("first_release_date")
        if release_timestamp is not None:
            try:
                from datetime import UTC, datetime

                dt = datetime.fromtimestamp(release_timestamp, tz=UTC)
                release_year = dt.year
            except (ValueError, OverflowError, OSError):
                pass

        return {
            "Title": game.get("name") or "Unknown Title",
            "title": game.get("name") or "Unknown Title",
            "cover_url": cover_url,
            "description": game.get("summary") or "",
            "PublicationYear": release_year,
            "year": release_year,
            "Source": "IGDB",
            "Format": "game",
        }
    except requests.RequestException as e:
        logger.warning("IGDB metadata fetch failed for %s: %s", query, e)
        return None
