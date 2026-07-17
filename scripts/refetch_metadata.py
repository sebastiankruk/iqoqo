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
import logging
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.db import db
from app.db.core import Expression, Manifestation, MetadataRefetchLog, Work
from app.utils.bgg import fetch_bgg_metadata
from app.utils.discogs import fetch_discogs_by_id, fetch_discogs_metadata
from app.utils.igdb import fetch_game_metadata
from app.utils.isbn import fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata
from app.utils.tmdb import fetch_video_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IQOQO_VERSION = "0.7.10"

RATE_LIMITS = {
    "tmdb": 0.025,
    "discogs": 1.0,
    "bgg": 0.5,
    "igdb": 0.25,
    "musicbrainz": 1.0,
    "google_books": 0.0,
}


def get_gap_query(gap: str, content_type: str | None = None):
    q = db.session.query(Manifestation).join(Expression).join(Work)
    if content_type:
        q = q.filter(Expression.content_type == content_type)

    if gap == "format":
        # manifestation.meta->>'format' IS NULL
        q = q.filter(text("manifestations.meta->>'format' IS NULL"))
    elif gap == "publisher":
        # publisher IS NULL AND meta->>'publisher' IS NULL
        q = q.filter(
            and_(
                or_(Manifestation.publisher.is_(None), Manifestation.publisher == ""),
                text("manifestations.meta->>'publisher' IS NULL"),
            )
        )
    elif gap == "genres":
        # work.meta->>'genres' IS NULL/empty AND work.meta->>'categories' IS NULL/empty
        q = q.filter(
            and_(
                or_(
                    text("works.meta->>'genres' IS NULL"),
                    text("works.meta->>'genres' = '[]'"),
                    text("works.meta->>'genres' = ''"),
                ),
                or_(
                    text("works.meta->>'categories' IS NULL"),
                    text("works.meta->>'categories' = '[]'"),
                    text("works.meta->>'categories' = ''"),
                ),
            )
        )
    elif gap == "cover":
        q = q.filter(or_(Manifestation.cover_url.is_(None), Manifestation.cover_url == ""))

    return q


def determine_strategy(man: Manifestation) -> str | None:
    ct = man.expression.content_type if man.expression else None
    if ct == "movie":
        return "tmdb"
    if ct == "music":
        return "discogs" if man.meta and man.meta.get("discogs_id") else "musicbrainz"
    if ct == "board_game":
        return "bgg"
    if ct == "video_game":
        return "igdb"
    if ct == "text":
        return "google_books"
    return None


def run_refetch(gap: str, content_type: str | None, dry_run: bool, force: bool, limit: int | None):
    app = create_app()
    with app.app_context():
        gaps = ["format", "publisher", "genres", "cover"] if gap == "all" else [gap]
        processed = 0

        for g in gaps:
            query = get_gap_query(g, content_type)
            items = query.all()

            for man in items:
                if limit and processed >= limit:
                    break

                strategy = determine_strategy(man)
                if not strategy:
                    continue

                if not force:
                    log_entry = MetadataRefetchLog.query.filter_by(entity_type="manifestation", entity_id=man.id, strategy=strategy).first()
                    if log_entry and log_entry.iqoqo_version == IQOQO_VERSION:
                        continue

                identifier = man.resolved_identifier
                if dry_run:
                    content_type_str = man.expression.content_type if man.expression else "unknown"
                    print(f"| {man.id:<6} | {content_type_str:<10} | {g:<10} | {strategy:<12} | {identifier}")
                    processed += 1
                    continue

                time.sleep(RATE_LIMITS.get(strategy, 0.0))

                found_fields: dict[str, Any] = {}
                error_msg = None

                try:
                    if strategy == "google_books":
                        # We use ISBN for books
                        if identifier:
                            res = fetch_isbn_metadata(identifier)
                            if res:
                                found_fields = res
                    elif strategy == "tmdb":
                        title = man.expression.work.title if man.expression and man.expression.work else None
                        if identifier:
                            res = fetch_video_metadata(identifier)  # Assume query can be barcode/UPC
                            if res:
                                found_fields = res
                        elif title:
                            res = fetch_video_metadata(title)
                            if res:
                                found_fields = res
                    elif strategy == "bgg":
                        title = man.expression.work.title if man.expression and man.expression.work else None
                        if title:
                            res = fetch_bgg_metadata(title)
                            if res:
                                found_fields = res
                    elif strategy == "igdb":
                        title = man.expression.work.title if man.expression and man.expression.work else None
                        if title:
                            res = fetch_game_metadata(title)
                            if res:
                                found_fields = res
                    elif strategy == "musicbrainz":
                        if identifier:
                            res = fetch_audio_metadata(identifier)
                            if res:
                                found_fields = res
                    elif strategy == "discogs":
                        discogs_id = man.meta.get("discogs_id") if man.meta else None
                        if discogs_id:
                            res = fetch_discogs_by_id(str(discogs_id))
                            if res:
                                found_fields = res
                        elif identifier:
                            res = fetch_discogs_metadata(identifier)
                            if res:
                                found_fields = res

                    # Apply updates
                    if found_fields:
                        if found_fields.get("publisher") and not man.publisher and not (man.meta and man.meta.get("publisher")):
                            man.publisher = found_fields["publisher"]
                        if found_fields.get("cover_url") and not man.cover_url:
                            man.cover_url = found_fields["cover_url"]
                        if found_fields.get("format") and not (man.meta and man.meta.get("format")):
                            man.update_meta({"format": found_fields["format"]})

                        genres = found_fields.get("genres") or found_fields.get("categories")
                        if genres and man.expression and man.expression.work:
                            work = man.expression.work
                            existing_g = work.meta.get("genres", []) if work.meta else []
                            existing_c = work.meta.get("categories", []) if work.meta else []
                            if not existing_g and not existing_c:
                                work.update_meta({"genres": genres})

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Error fetching %s via %s: %s", identifier, strategy, e)
                    error_msg = str(e)

                log_entry = MetadataRefetchLog.query.filter_by(entity_type="manifestation", entity_id=man.id, strategy=strategy).first()
                if not log_entry:
                    log_entry = MetadataRefetchLog(entity_type="manifestation", entity_id=man.id, strategy=strategy)
                    db.session.add(log_entry)
                log_entry.checked_at = datetime.now(UTC)
                log_entry.iqoqo_version = IQOQO_VERSION
                log_entry.found_fields = found_fields if found_fields else None
                log_entry.error = error_msg

                db.session.commit()
                processed += 1

        if not dry_run:
            logger.info("Refetch completed for %d items.", processed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refetch missing metadata from external APIs.")
    parser.add_argument(
        "--gap", type=str, choices=["format", "publisher", "genres", "cover", "all"], default="all", help="Which missing field to target"
    )
    parser.add_argument(
        "--content-type",
        type=str,
        choices=["text", "music", "movie", "board_game", "video_game", "puzzle"],
        default=None,
        help="Restrict to specific content type",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print items that would be fetched without making API calls")
    parser.add_argument("--force", action="store_true", help="Force refetch even if already logged for this version")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to process")

    args = parser.parse_args()
    run_refetch(gap=args.gap, content_type=args.content_type, dry_run=args.dry_run, force=args.force, limit=args.limit)
