"""Maintenance script for cover images.

Two complementary processes:

1. **archive_orphaned_covers** — moves image files that exist on disk but are
   no longer referenced by any Manifestation row into an archive directory.

2. **schedule_missing_covers** — finds Manifestation rows whose cover_url is
   NULL or points to a file that no longer exists on disk, then runs the full
   cover-generation pipeline for each one.  Generation is performed serially
   within this process; for large libraries consider wrapping each call in a
   thread or task queue.
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

import os
import shutil
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.db.models import Manifestation

COVERS_DIR = os.path.join(Config.BASE_DIR, "app", "static", "covers")


def archive_orphaned_covers(app=None):
    """Move on-disk cover files not referenced in the DB to an archive folder."""
    # Allow configuration via env var, default to static/archive/covers
    default_archive = os.path.join(Config.BASE_DIR, "app", "static", "archive", "covers")
    archive_dir = os.environ.get("COVERS_ARCHIVE_DIR", default_archive)
    os.makedirs(archive_dir, exist_ok=True)

    if app is None:
        app = create_app()

    with app.app_context():
        # Collect all basenames referenced by the DB
        valid_paths = {os.path.basename(m.cover_url) for m in Manifestation.query.filter(Manifestation.cover_url.isnot(None)).all()}

        archived_count = 0
        for filename in os.listdir(COVERS_DIR):
            if filename.startswith("."):
                continue

            if filename not in valid_paths:
                src = os.path.join(COVERS_DIR, filename)
                dst = os.path.join(archive_dir, filename)
                shutil.move(src, dst)
                archived_count += 1

        print(f"✅ Archived {archived_count} orphaned cover images.")


def schedule_missing_covers(app=None):
    """Find manifestations with no usable cover and trigger the generation pipeline.

    A cover is considered missing when:
    * ``cover_url`` is NULL, or
    * ``cover_url`` references a file that does not exist on disk.

    Each missing manifestation is passed through :func:`process_cover_pipeline`
    which tries (in order): External APIs → LLM generation.  If all tiers fail
    the row is left unchanged and ``cover_status`` is set to ``"failed"``
    rather than writing an empty placeholder image.
    """
    # Import here so the script works even if the pipeline hasn't been
    # initialised at module-load time (avoids circular-import issues in tests).
    # We keep a reference to the module so tests can patch the function at
    # ``app.utils.covers.process_cover_pipeline``.
    import app.utils.covers as _covers  # noqa: PLC0415

    if app is None:
        app = create_app()

    with app.app_context():
        all_manifestations = Manifestation.query.all()

        missing = []
        for manif in all_manifestations:
            if manif.cover_url is None:
                missing.append(manif)
                continue
            # Resolve absolute path from the "/static/covers/<file>" URL stored in DB
            abs_path = os.path.join(Config.BASE_DIR, "app", manif.cover_url.lstrip("/"))
            if not os.path.exists(abs_path):
                missing.append(manif)

        print(f"Found {len(missing)} manifestation(s) with missing covers.")

        scheduled = 0
        for manif in missing:
            isbn = manif.isbn13 or str(manif.id)

            work = manif.expression.work if (manif.expression and manif.expression.work) else None
            title = work.title if work else "Unknown Title"
            author = (
                work.meta.get("authors", ["Unknown Author"])[0] if (work and work.meta and work.meta.get("authors")) else "Unknown Author"
            )

            print(f"  Scheduling cover generation for ISBN {isbn} (id={manif.id}) …")
            # process_cover_pipeline manages its own app context when called
            # outside one; calling it here while already inside app.app_context()
            # is also safe (it will reuse the existing context).
            _covers.process_cover_pipeline(manif.id, isbn, title, author)
            scheduled += 1

        print(f"✅ Processed {scheduled} missing cover(s).")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cover maintenance utilities.")
    parser.add_argument(
        "--archive-orphans",
        action="store_true",
        default=False,
        help="Move on-disk cover files not in the DB to the archive directory.",
    )
    parser.add_argument(
        "--schedule-missing",
        action="store_true",
        default=False,
        help="Find manifestations with missing covers and run generation pipeline.",
    )
    args = parser.parse_args()

    # Default: run both tasks when no flag is given
    run_all = not args.archive_orphans and not args.schedule_missing
    if args.archive_orphans or run_all:
        archive_orphaned_covers()
    if args.schedule_missing or run_all:
        schedule_missing_covers()
