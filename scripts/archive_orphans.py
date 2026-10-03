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
from app.db.models import Manifestation, db

COVERS_DIR = os.path.join(Config.BASE_DIR, "app", "static", "covers")

# MOD-OPS-16: rows fetched per server-side cursor batch. 1000 keeps each
# round-trip small enough to stay responsive while avoiding the per-row
# round-trip cost of a batch size of 1.
STREAM_BATCH_SIZE = 1000


def archive_orphaned_covers(app=None):
    """Move on-disk cover files not referenced in the DB to an archive folder."""
    # Allow configuration via env var, default to static/archive/covers
    default_archive = os.path.join(Config.BASE_DIR, "app", "static", "archive", "covers")
    archive_dir = os.environ.get("COVERS_ARCHIVE_DIR", default_archive)
    os.makedirs(archive_dir, exist_ok=True)

    if app is None:
        app = create_app()

    with app.app_context():
        # MOD-OPS-16: stream the candidate set in chunks.
        #
        # `.all()` instantiated one Manifestation object per row — the whole
        # table plus per-row ORM overhead in memory simultaneously. On a large
        # library that is hundreds of thousands of objects for a maintenance
        # script whose only output is a set of basenames, and the Oracle Free
        # Tier boxes iqoqo targets have 1 GB of RAM. `yield_per` additionally
        # asks the driver to fetch rows in batches rather than letting the
        # client buffer the entire result set.
        #
        # Only the `cover_url` column is selected, so no whole entities cross
        # the wire and none are constructed.
        valid_paths = {
            os.path.basename(row[0])
            for row in db.session.execute(
                db.select(Manifestation.cover_url).where(Manifestation.cover_url.isnot(None)).execution_options(yield_per=STREAM_BATCH_SIZE)
            )
            if row[0]
        }

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
        # MOD-OPS-16: two passes instead of one `.all()`.
        #
        # Pass 1 streams only the (id, cover_url) pairs in batches, so the
        # resident set is bounded by STREAM_BATCH_SIZE rows rather than the
        # whole table. Deliberately *not* done with a single `yield_per` query
        # consumed lazily: pass 2 writes to the database via
        # process_cover_pipeline, and a commit invalidates any server-side
        # cursor still being iterated — with a lazy cursor that surfaces as a
        # mid-loop error or a silently truncated work list.
        #
        # Collecting scalar ids first keeps the memory bound and makes the
        # snapshot explicit, so the work list cannot shift underneath us.
        candidates = list(
            db.session.execute(db.select(Manifestation.id, Manifestation.cover_url).execution_options(yield_per=STREAM_BATCH_SIZE))
        )

        missing = []
        for manif_id, cover_url in candidates:
            if cover_url is None:
                missing.append(manif_id)
                continue
            # Resolve absolute path from the "/static/covers/<file>" URL stored in DB
            abs_path = os.path.join(Config.BASE_DIR, "app", cover_url.lstrip("/"))
            if not os.path.exists(abs_path):
                missing.append(manif_id)

        print(f"Found {len(missing)} manifestation(s) with missing covers.")

        scheduled = 0
        for manif_id in missing:
            # Re-read each row individually. This is a primary-key lookup, so
            # it is cheap, and it guarantees a fresh object that reflects any
            # state written by the previous pipeline run rather than an
            # identity-map instance pinned to the snapshot.
            manif = db.session.get(Manifestation, manif_id)
            if manif is None:
                # Deleted between the scan and now; nothing left to fix.
                continue

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
            _covers.process_cover_pipeline(
                manif.id,
                isbn,
                title,
                author,
                llm_permissions={
                    "allow_generate_cover": True,
                    "allow_cloud_llm": True,
                },
            )
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
