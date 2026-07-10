#!/usr/bin/env python3
"""
Script to retry cover processing for items that failed due to Celery/PostgreSQL issues.
This finds manifestations where:
- cover_url (DB column) is NULL/empty
- meta["cover_url"] exists (external URL was fetched during scan)
- cover_status is not "ready" (hasn't been processed yet)

Run via: docker compose exec web python scripts/retry_missing_covers.py [--limit N]
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

import argparse
import os
import sys
import time

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from app import create_app
from app.db import db
from app.db.models import Manifestation
from app.utils.covers import process_cover_pipeline


def retry_missing_covers(batch_limit=None, dry_run=False):
    app = create_app()
    with app.app_context():
        query = Manifestation.query.filter(
            db.or_(Manifestation.cover_url.is_(None), Manifestation.cover_url == ""),
            Manifestation.meta["cover_url"].as_string() != "",
            Manifestation.meta["cover_url"].isnot(None),
            db.or_(
                Manifestation.meta["cover_status"].as_string() != "ready",
                Manifestation.meta["cover_status"].is_(None),
            ),
        )

        if batch_limit:
            query = query.limit(batch_limit)

        missing = query.all()
        print(f"Found {len(missing)} manifestations with missing covers that have meta['cover_url']")

        if dry_run:
            print("DRY RUN - no changes will be made")
            for m in missing[:10]:
                meta_cover = m.meta.get("cover_url") if m.meta else "None"
                meta_cover_text = str(meta_cover)
                meta_title = m.meta.get("title", "Unknown") if m.meta else "Unknown"
                meta_title_text = str(meta_title)
                print(f"  ID {m.id}: {meta_title_text[:40]} -> {meta_cover_text[:50]}...")
            return

        processed = 0
        failed = 0

        for index, man in enumerate(missing):
            work = man.expression.work if (man.expression and man.expression.work) else None
            title = work.title if work else (man.meta.get("title") if man.meta else "Unknown")
            isbn = man.isbn13 or (man.meta.get("isbn") if man.meta else None) or f"item_{man.id}"
            author = (
                work.meta.get("authors", ["Unknown"])[0]
                if (work and work.meta and work.meta.get("authors"))
                else (man.meta.get("author") if man.meta else "Unknown")
            )

            external_url = man.meta.get("cover_url") if man.meta else None
            print(f"[{index + 1}/{len(missing)}] Processing: {title[:40]} ({isbn})")
            print(f"         External: {external_url[:60] if external_url else 'None'}...")

            try:
                process_cover_pipeline(
                    man.id,
                    isbn,
                    title,
                    author,
                    llm_permissions={
                        "allow_generate_cover": True,
                        "allow_cloud_llm": True,
                    },
                )
                processed += 1
            except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError, RuntimeError) as e:
                print(f"  -> Error: {str(e)[:100]}")
                failed += 1

            time.sleep(0.5)

        print(f"\nCompleted: {processed} processed, {failed} failed")


def main():
    parser = argparse.ArgumentParser(description="Retry cover processing for failed items")
    parser.add_argument("--limit", type=int, help="Maximum items to process", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without changes")
    args = parser.parse_args()

    retry_missing_covers(batch_limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
