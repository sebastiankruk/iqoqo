#!/usr/bin/env python3
"""Backfill allowlisted legacy external cover URLs to local cover files.

The command is a dry run unless ``--apply`` and a matching sanitized database
target confirmation are both supplied. Downloads go through the standard
cover pipeline and SSRF-safe HTTP client; this script never processes an
unapproved source host or invokes fallback providers.
"""

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

import argparse
import os
import sys
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from app import create_app
from app.db import db
from app.db.models import Manifestation
from app.utils.covers import is_allowed_legacy_cover_url, is_local_cover_url, process_cover_pipeline

PAGE_SIZE = 100


class DatabaseConnectivityError(RuntimeError):
    """Raised when the configured database cannot be reached safely."""


def database_target(url: URL) -> str:
    """Return a credential-free database identity for the apply confirmation."""
    driver = url.drivername.split("+", 1)[0]
    if driver == "sqlite":
        return f"sqlite:{url.database or ':memory:'}"

    host = url.host or "localhost"
    if url.port is not None:
        host = f"{host}:{url.port}"
    return f"{driver}://{host}/{url.database or ''}"


def _external_urls(manifestation: Manifestation) -> list[str]:
    """Return external-looking cover values without logging their contents."""
    meta = manifestation.meta if isinstance(manifestation.meta, dict) else {}
    values = [manifestation.cover_url, meta.get("cover_url")]
    return [value for value in values if isinstance(value, str) and value.lower().startswith(("http://", "https://"))]


def _has_external_cover_source_query():
    """Build a SQL filter for legacy cover sources in either canonical field."""
    metadata_cover = Manifestation.meta["cover_url"].as_string()
    return db.or_(
        Manifestation.cover_url.ilike("http://%"),
        Manifestation.cover_url.ilike("https://%"),
        metadata_cover.ilike("http://%"),
        metadata_cover.ilike("https://%"),
    )


def _iter_candidates(limit: int | None) -> Iterable[Manifestation]:
    """Yield externally sourced manifestations in bounded, stable ID pages."""
    last_id = 0
    yielded = 0
    while limit is None or yielded < limit:
        page_limit = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - yielded)
        page = (
            Manifestation.query.filter(Manifestation.id > last_id, _has_external_cover_source_query())
            .order_by(Manifestation.id)
            .limit(page_limit)
            .all()
        )
        if not page:
            return
        for manifestation in page:
            last_id = manifestation.id
            yielded += 1
            yield manifestation


def run_backfill(
    *,
    app=None,
    apply: bool = False,
    confirm_target: str | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    """Audit or backfill matching sources using local database state only.

    Apply mode is refused unless ``confirm_target`` exactly matches the
    credential-free target identity printed by dry-run mode.
    """
    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer")

    flask_app = app or create_app(config_override={"SKIP_STARTUP_COVER_CLEANUP": True})
    with flask_app.app_context():
        target = database_target(db.engine.url)
        mode = "APPLY" if apply else "DRY RUN"
        print(f"Database target: {target}")
        print(f"Mode: {mode}")
        if apply and confirm_target != target:
            raise ValueError("apply mode requires --confirm-target to exactly match the displayed database target")

        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            db.session.rollback()
            loopback_host = db.engine.url.host in {"localhost", "127.0.0.1", "::1"}
            if loopback_host and os.path.exists("/.dockerenv"):
                hint = " Inside a container, loopback refers to that container; configure a database hostname reachable on its network."
            else:
                hint = " Verify the configured database endpoint and network connectivity."
            raise DatabaseConnectivityError(f"Cannot connect to configured database target {target}.{hint}") from exc

        counts: dict[str, int] = {
            "candidates": 0,
            "eligible": 0,
            "already_local_ready": 0,
            "unsupported_host": 0,
            "processed": 0,
            "failed": 0,
        }

        for manifestation in _iter_candidates(limit):
            counts["candidates"] += 1
            meta = manifestation.meta if isinstance(manifestation.meta, dict) else {}
            if is_local_cover_url(manifestation.cover_url) and meta.get("cover_status") == "ready":
                counts["already_local_ready"] += 1
                continue

            source_url = next((url for url in _external_urls(manifestation) if is_allowed_legacy_cover_url(url)), None)
            if source_url is None:
                counts["unsupported_host"] += 1
                print(f"Skipped manifestation {manifestation.id}: no allowlisted cover host")
                continue

            counts["eligible"] += 1
            if not apply:
                print(f"Would process manifestation {manifestation.id}")
                continue

            work = manifestation.expression.work if manifestation.expression else None
            title = work.title if work else (meta.get("title") or "Unknown")
            authors = work.meta.get("authors") if work and work.meta else None
            author = authors[0] if isinstance(authors, list) and authors else (meta.get("author") or "Unknown")
            identifier = manifestation.isbn13 or manifestation.ean or manifestation.upc or f"manifestation_{manifestation.id}"

            try:
                process_cover_pipeline(
                    manifestation.id,
                    identifier,
                    title,
                    author,
                    llm_permissions={"allow_generate_cover": False, "allow_cloud_llm": False},
                    legacy_source_only=True,
                )
                db.session.refresh(manifestation)
                if is_local_cover_url(manifestation.cover_url) and (manifestation.meta or {}).get("cover_status") == "ready":
                    counts["processed"] += 1
                    print(f"Processed manifestation {manifestation.id}")
                else:
                    counts["failed"] += 1
                    print(f"Failed manifestation {manifestation.id}: pipeline did not produce a ready local copy")
            except Exception as exc:  # Operational backfill continues after per-row failures.
                db.session.rollback()
                counts["failed"] += 1
                print(f"Failed manifestation {manifestation.id}: {type(exc).__name__}")

        print("Summary: " + ", ".join(f"{name}={count}" for name, count in counts.items()))
        return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Process allowlisted sources; dry-run is the default")
    parser.add_argument("--confirm-target", help="Exact credential-free database target printed by dry-run")
    parser.add_argument("--limit", type=int, help="Maximum number of candidate manifestations to inspect")
    args = parser.parse_args()

    try:
        run_backfill(apply=args.apply, confirm_target=args.confirm_target, limit=args.limit)
    except (DatabaseConnectivityError, ValueError) as exc:
        print(f"Backfill not started: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # Do not expose connection strings or signed URLs in tracebacks.
        print(f"Backfill aborted: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
