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
Standalone data migration: migrate legacy manifestation-level wishlist items to UserWorkIntent.

Extracted from historical unbatched migration d35f2371cfba_add_work_level_intents.py.
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

from sqlalchemy import delete, select

from app import create_app
from app.db import db
from app.db.models import Expression, Item, Manifestation, UserWorkIntent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_wishlist_intents")


def migrate_wishlist_intents(batch_size: int = 500, dry_run: bool = False, app: Any = None) -> dict[str, int]:
    """Migrate items with collection_status='wish_list' to UserWorkIntent in batches."""
    app = app or create_app()

    stats = {
        "found_wishlist_items": 0,
        "created_intents": 0,
        "skipped_existing_intents": 0,
        "deleted_legacy_items": 0,
    }

    with app.app_context():
        while True:
            # Query legacy wishlist items
            stmt = (
                select(Item.id, Item.owner_id, Expression.work_id, Item.status)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .where(Item.collection_status == "wish_list")
                .limit(batch_size)
            )
            rows = db.session.execute(stmt).all()
            if not rows:
                break

            logger.info("Processing wishlist batch of %d items...", len(rows))
            item_ids_to_delete: list[int] = []

            for item_id, owner_id, work_id, status in rows:
                stats["found_wishlist_items"] += 1
                if not owner_id or not work_id:
                    item_ids_to_delete.append(item_id)
                    continue

                # Check if intent already exists
                existing = db.session.execute(
                    select(UserWorkIntent).where(
                        UserWorkIntent.user_id == owner_id,
                        UserWorkIntent.work_id == work_id,
                    )
                ).scalar_one_or_none()

                if not existing:
                    intent_status = status if status else "want_to_read"
                    if not dry_run:
                        new_intent = UserWorkIntent(
                            user_id=owner_id,
                            work_id=work_id,
                            status=intent_status,
                        )
                        db.session.add(new_intent)
                    stats["created_intents"] += 1
                else:
                    stats["skipped_existing_intents"] += 1

                item_ids_to_delete.append(item_id)

            if not dry_run and item_ids_to_delete:
                # Delete processed items
                del_stmt = delete(Item).where(Item.id.in_(item_ids_to_delete))
                db.session.execute(del_stmt)
                db.session.commit()
                stats["deleted_legacy_items"] += len(item_ids_to_delete)
                logger.info("Committed batch: created intents and removed %d legacy items.", len(item_ids_to_delete))
            elif dry_run:
                # Break to avoid infinite loop when dry running
                break

    logger.info("Migration complete: %s", stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy wishlist items to UserWorkIntent.")
    parser.add_argument("--batch-size", type=int, default=500, help="Number of records to process per batch")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and count changes without modifying database")
    args = parser.parse_args()

    migrate_wishlist_intents(batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
