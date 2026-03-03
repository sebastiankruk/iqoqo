import argparse
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, or_

from app import create_app
from app.db.models import Manifestation
from app.utils.covers import process_cover_pipeline


def run_batch(batch_limit=None, force=False, app=None):
    if app is None:
        app = create_app()
    with app.app_context():
        query = Manifestation.query.filter(Manifestation.cover_path.is_(None))
        if not force:
            cover_status = func.json_extract_path_text(Manifestation.meta, "cover_status")
            query = query.filter(or_(cover_status.is_(None), cover_status != "failed"))

        if batch_limit:
            query = query.limit(batch_limit)

        missing_covers = query.all()
        print(f"Found {len(missing_covers)} items needing covers in this batch.")

        try:
            for index, man in enumerate(missing_covers):
                isbn = man.isbn13 or (man.meta.get("isbn") if man.meta else f"item_{man.id}")
                work = man.expression.work if (man.expression and man.expression.work) else None
                title = work.title if work else "Unknown Title"
                author = (
                    work.meta.get("authors", ["Unknown Author"])[0]
                    if (work and work.meta and work.meta.get("authors"))
                    else "Unknown Author"
                )

                print(f"[{index+1}/{len(missing_covers)}] Processing: {title} ({isbn})")

                try:
                    # Catch individual item failures so the batch continues
                    process_cover_pipeline(man.id, isbn, title, author)
                except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError, RuntimeError) as e:
                    print(f"  -> Error processing {isbn}: {str(e)}")

                time.sleep(1)

        except KeyboardInterrupt:
            print("\nBatch generation paused. Run script again to resume.")
            sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch missing covers.")
    parser.add_argument("--limit", type=int, help="Maximum number of covers to process in this run", default=None)
    parser.add_argument("--force", action="store_true", help="Force reprocessing of covers even if previously failed")
    args = parser.parse_args()

    run_batch(batch_limit=args.limit, force=args.force)
