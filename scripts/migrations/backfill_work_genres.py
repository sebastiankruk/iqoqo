#!/usr/bin/env python3
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
"""
Standalone data migration: backfill Work.meta['genres'] from Manifestation.meta.

Extracted from historical unbatched migration 20260521_backfill_work_genres.py.
Processes records in configurable batches with progress logging to prevent OOM errors.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select, update

from app import create_app
from app.db import db
from app.db.models import Expression, Manifestation, Work

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_work_genres")


def _extract_genres_from_meta(meta: dict[str, Any]) -> list[str]:
    """Extract genre strings from a Manifestation.meta dict."""
    genres: list[str] = []
    for key in ("Categories", "genres", "genre", "Genre"):
        raw = meta.get(key)
        if isinstance(raw, list):
            for v in raw:
                if isinstance(v, str) and v.strip():
                    genres.append(v.strip())
        elif isinstance(raw, str) and raw.strip():
            genres.append(raw.strip())
    return genres


def backfill_work_genres(batch_size: int = 500, dry_run: bool = False, app: Any = None) -> dict[str, int]:
    """Backfill Work.meta['genres'] from Manifestation.meta in chunked batches."""
    app = app or create_app()

    stats = {
        "processed_manifestations": 0,
        "updated_works": 0,
        "skipped_already_has_genres": 0,
        "skipped_no_genre_data": 0,
        "skipped_no_work": 0,
    }

    with app.app_context():
        offset = 0
        while True:
            stmt = (
                select(Manifestation.id, Manifestation.expression_id, Manifestation.meta)
                .where(Manifestation.meta.is_not(None))
                .order_by(Manifestation.id)
                .offset(offset)
                .limit(batch_size)
            )
            rows = db.session.execute(stmt).all()
            if not rows:
                break

            logger.info("Processing manifestations batch offset %d (count: %d)...", offset, len(rows))
            batch_updated = 0

            for _manif_id, expression_id, raw_meta in rows:
                stats["processed_manifestations"] += 1
                if not raw_meta:
                    stats["skipped_no_genre_data"] += 1
                    continue

                if isinstance(raw_meta, str):
                    try:
                        man_meta = json.loads(raw_meta)
                    except (json.JSONDecodeError, TypeError):
                        man_meta = {}
                elif isinstance(raw_meta, dict):
                    man_meta = raw_meta
                else:
                    man_meta = {}

                if not isinstance(man_meta, dict):
                    stats["skipped_no_genre_data"] += 1
                    continue

                genres = _extract_genres_from_meta(man_meta)
                if not genres:
                    stats["skipped_no_genre_data"] += 1
                    continue

                if not expression_id:
                    stats["skipped_no_work"] += 1
                    continue

                expr = db.session.get(Expression, expression_id)
                if not expr or not expr.work_id:
                    stats["skipped_no_work"] += 1
                    continue

                work = db.session.get(Work, expr.work_id)
                if not work:
                    stats["skipped_no_work"] += 1
                    continue

                work_meta = dict(work.meta or {})
                if work_meta.get("genres") or work_meta.get("genre"):
                    stats["skipped_already_has_genres"] += 1
                    continue

                work_meta["genres"] = genres
                if not dry_run:
                    work.meta = work_meta
                    db.session.add(work)

                stats["updated_works"] += 1
                batch_updated += 1

            if not dry_run and batch_updated > 0:
                db.session.commit()
                logger.info("Committed %d work genre updates in batch.", batch_updated)

            offset += batch_size

    logger.info("Backfill complete: %s", stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Work.meta['genres'] from Manifestation.meta.")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of records to process per batch")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and count changes without modifying database")
    args = parser.parse_args()

    backfill_work_genres(batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
