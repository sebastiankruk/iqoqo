import os
import sys
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.db.models import Manifestation
from app.utils.covers import process_cover_pipeline

app = create_app()


def run_batch():
    with app.app_context():
        # Resumable: Only fetch items where cover_path is NULL
        missing_covers = Manifestation.query.filter(Manifestation.cover_path.is_(None)).all()
        print(f"Found {len(missing_covers)} items needing covers.")

        try:
            for index, man in enumerate(missing_covers):
                # Extract metadata safely
                isbn = man.isbn13 or (man.meta.get("isbn") if man.meta else f"item_{man.id}")

                # Navigate FRBR hierarchy: Manifestation -> Expression -> Work
                work = man.expression.work if (man.expression and man.expression.work) else None
                title = work.title if work else "Unknown Title"
                # Simplified author extraction
                author = (
                    work.meta.get("authors", ["Unknown Author"])[0]
                    if (work and work.meta and work.meta.get("authors"))
                    else "Unknown Author"
                )

                print(f"[{index+1}/{len(missing_covers)}] Processing: {title} ({isbn})")

                # Run synchronously to avoid rate limits
                process_cover_pipeline(man.id, isbn, title, author)
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nBatch generation paused. Run script again to resume.")
            sys.exit(0)


if __name__ == "__main__":
    run_batch()
