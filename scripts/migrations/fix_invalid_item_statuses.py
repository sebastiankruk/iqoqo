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
Standalone data repair script: normalize invalid item statuses and collection statuses.

Extracted from historical unbatched migration 88d8fcbeb3df_fix_invalid_item_statuses.py.
Processes records in configurable batches with progress logging.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select

from app import create_app
from app.db import db
from app.db.models import Expression, Item, Manifestation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fix_invalid_item_statuses")

CATEGORY_PROGRESS: dict[str, set[str]] = {
    "text": {"want_to_read", "reading", "read", "dnf"},
    "audiobook": {"want_to_listen", "listening", "listened", "dnf"},
    "music": {"want_to_listen", "listened"},
    "movie": {"want_to_watch", "watched", "dnf"},
    "board_game": {"want_to_play", "playing", "played"},
    "puzzle": {"want_to_play", "playing", "played"},
}

CATEGORY_DEFAULTS: dict[str, str] = {
    "text": "want_to_read",
    "audiobook": "want_to_listen",
    "music": "want_to_listen",
    "movie": "want_to_watch",
    "board_game": "want_to_play",
    "puzzle": "want_to_play",
}

KNOWN_COLLECTION_STATUSES: set[str] = {"wish_list", "ordered", "available", "lent", "damaged", "lost"}


def repair_item_status(status: str | None, collection_status: str | None, content_type: str | None) -> tuple[str | None, str | None]:
    """Calculate normalized (status, collection_status) if needed."""
    ct = content_type or "text"
    valid_for_category = CATEGORY_PROGRESS.get(ct, set())

    new_status: str | None = None
    new_coll_status: str | None = None

    if status == "unread":
        new_status = CATEGORY_DEFAULTS.get(ct, "want_to_read")
    elif status == "available":
        new_coll_status = "available"
        new_status = CATEGORY_DEFAULTS.get(ct, "want_to_read")
    elif status in KNOWN_COLLECTION_STATUSES:
        new_coll_status = status
        new_status = CATEGORY_DEFAULTS.get(ct, "want_to_read")
    elif status not in valid_for_category:
        if status and any(term in status for term in ("read", "watch", "listen", "play")):
            prefix = "want_to_" if "want_to_" in status else ""
            suffix = "ing" if status.endswith("ing") else ("ed" if status.endswith("ed") else "")

            if prefix:
                new_status = CATEGORY_DEFAULTS.get(ct, "want_to_read")
            elif suffix == "ing":
                if ct == "text":
                    new_status = "reading"
                elif ct == "music":
                    new_status = "listening"
                elif ct == "movie":
                    new_status = "watching"
                else:
                    new_status = "playing"
            elif suffix == "ed":
                if ct == "text":
                    new_status = "read"
                elif ct == "music":
                    new_status = "listened"
                elif ct == "movie":
                    new_status = "watched"
                else:
                    new_status = "played"
            else:
                new_status = CATEGORY_DEFAULTS.get(ct, "want_to_read")
        else:
            new_status = CATEGORY_DEFAULTS.get(ct, "want_to_read")

    final_status = new_status if (new_status and new_status != status) else None
    final_coll_status = new_coll_status if (new_coll_status and new_coll_status != collection_status) else None
    return final_status, final_coll_status


def fix_invalid_item_statuses(batch_size: int = 500, dry_run: bool = False, app: Any = None) -> dict[str, int]:
    """Inspect and fix item statuses in chunked batches."""
    app = app or create_app()

    stats = {
        "processed_items": 0,
        "updated_items": 0,
        "fixed_status": 0,
        "fixed_collection_status": 0,
    }

    with app.app_context():
        offset = 0
        while True:
            stmt = (
                select(Item.id, Item.status, Item.collection_status, Expression.content_type)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .order_by(Item.id)
                .offset(offset)
                .limit(batch_size)
            )
            rows = db.session.execute(stmt).all()
            if not rows:
                break

            logger.info("Processing items batch offset %d (count: %d)...", offset, len(rows))
            batch_updated = 0

            for item_id, status, coll_status, content_type in rows:
                stats["processed_items"] += 1
                new_status, new_coll_status = repair_item_status(status, coll_status, content_type)

                if new_status or new_coll_status:
                    stats["updated_items"] += 1
                    if new_status:
                        stats["fixed_status"] += 1
                    if new_coll_status:
                        stats["fixed_collection_status"] += 1

                    if not dry_run:
                        item = db.session.get(Item, item_id)
                        if item:
                            if new_status:
                                item.status = new_status
                            if new_coll_status:
                                item.collection_status = new_coll_status
                            db.session.add(item)
                    batch_updated += 1

            if not dry_run and batch_updated > 0:
                db.session.commit()
                logger.info("Committed %d item status repairs in batch.", batch_updated)

            offset += batch_size

    logger.info("Status repair complete: %s", stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair invalid item progress and collection statuses.")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of records to process per batch")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and count changes without modifying database")
    args = parser.parse_args()

    fix_invalid_item_statuses(batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
