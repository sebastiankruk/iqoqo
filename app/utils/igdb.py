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
        with open(_TOKEN_FILE, "w", encoding="utf-8") as wf:
            json.dump(new_tokens, wf)
        access_token = new_tokens.get("access_token")
        return str(access_token) if isinstance(access_token, str) else None
    except requests.RequestException as e:
        logger.warning("Failed to obtain IGDB access token from Twitch: %s", e)
        return None


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

    # Escape double quotes in the search query to prevent payload injection errors
    escaped_query = query.replace('"', '\\"')
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
