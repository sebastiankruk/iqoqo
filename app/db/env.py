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
#
"""Environment resolution helpers for database URLs and canonical BASE_URL origins."""

from __future__ import annotations

import os
from urllib.parse import quote


def resolve_database_url() -> str | None:
    """Return DATABASE_URL or derive a PostgreSQL URL from POSTGRES_* variables."""
    explicit = os.environ.get("DATABASE_URL", "").strip()
    if explicit:
        return explicit

    pg_password = os.environ.get("POSTGRES_PASSWORD", "").strip()
    if not pg_password:
        return None

    pg_user = os.environ.get("POSTGRES_USER", "").strip() or "iqoqo"
    pg_db = os.environ.get("POSTGRES_DB", "").strip() or "iqoqo"
    pg_host = os.environ.get("POSTGRES_HOST", "").strip() or "db"
    pg_port = os.environ.get("POSTGRES_PORT", "").strip() or os.environ.get("DB_PORT", "").strip() or "5432"

    return f"postgresql://{quote(pg_user, safe='')}:{quote(pg_password, safe='')}" f"@{pg_host}:{pg_port}/{quote(pg_db, safe='')}"


def ensure_database_url_env() -> str | None:
    """Populate os.environ['DATABASE_URL'] from POSTGRES_* when DATABASE_URL is unset."""
    resolved = resolve_database_url()
    if resolved and not os.environ.get("DATABASE_URL", "").strip():
        os.environ["DATABASE_URL"] = resolved
    return resolved


def resolve_frontend_url(default: str = "http://localhost:3000") -> str:
    """Return NEXT_PUBLIC_FRONTEND_URL, falling back to BASE_URL, then default."""
    candidate = os.environ.get("NEXT_PUBLIC_FRONTEND_URL", "").strip() or os.environ.get("BASE_URL", "").strip()
    return (candidate or default).rstrip("/")


def resolve_public_app_url() -> str | None:
    """Return PUBLIC_APP_URL, falling back to NEXT_PUBLIC_FRONTEND_URL or BASE_URL."""
    candidate = (
        os.environ.get("PUBLIC_APP_URL", "").strip()
        or os.environ.get("NEXT_PUBLIC_FRONTEND_URL", "").strip()
        or os.environ.get("BASE_URL", "").strip()
    )
    return candidate.rstrip("/") if candidate else None
