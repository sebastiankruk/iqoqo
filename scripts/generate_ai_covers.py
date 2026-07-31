"""Batch AI cover generation and watermarking automation CLI.

Provides automated batch processing for missing or unwatermarked AI media covers
per openspec release-0-7-13 Section 7.
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
import logging
import os
from typing import Any, cast

from app.config import Config
from app.db.models import Manifestation, db
from app.utils.llm_covers import apply_corner_watermark, fetch_llm_cover

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_PROMPT_SPEC_PATH = os.path.join(Config.BASE_DIR, ".context", "notes", "llm-watermark-prompt-spec.md")
DEFAULT_WATERMARK_ICON_PATH = os.path.join(Config.BASE_DIR, "app", "static", "watermark.png")


def load_prompt_spec(prompt_path: str | None = None) -> str:
    """Load prompt spec template from file or return FRBR-aligned fallback."""
    path = prompt_path or DEFAULT_PROMPT_SPEC_PATH
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError as e:
            logger.warning("Could not read prompt spec from %s: %s", path, e)

    return "A high-quality minimalist FRBR media cover for '{title}' by {author}."


def get_unwatermarked_manifestations(limit: int | None = None) -> list[Manifestation]:
    """Return manifestations missing covers or holding unwatermarked AI covers."""
    query = Manifestation.query.filter(
        db.or_(
            Manifestation.cover_url.is_(None),
            Manifestation.cover_url == "",
            Manifestation.meta["cover_source"].as_string().like("llm_%"),
        )
    )
    if limit:
        query = query.limit(limit)
    return cast(list[Manifestation], query.all())


def process_batch(
    manifestations: list[Manifestation],
    dry_run: bool = False,
    watermark_only: bool = False,
    user_id: str = "system_batch",
    force_retry: bool = False,
) -> dict[str, Any]:
    """Batch process list of manifestations for AI cover generation and corner watermarking."""
    total = len(manifestations)
    stats = {"total": total, "processed": 0, "generated": 0, "watermarked": 0, "skipped": 0, "failed": 0}

    logger.info("Starting batch cover processing for %d manifestations (dry_run=%s)", total, dry_run)

    for idx, manif in enumerate(manifestations, start=1):
        # Circuit breaker: skip items that have failed too many times
        failed_attempts = (manif.meta or {}).get("failed_llm_attempts", 0)
        if failed_attempts >= 3 and not force_retry:
            stats["skipped"] += 1
            logger.info("[%d/%d] Skipping manifestation %d: circuit breaker triggered (%d failures)", idx, total, manif.id, failed_attempts)
            continue

        work_title = manif.expression.work.title if (manif.expression and manif.expression.work) else "Unknown Title"
        author_name = manif.meta.get("author") or manif.meta.get("artist") or ""
        format_type = manif.format or (manif.meta.get("format") if manif.meta else None)
        cover_url = manif.cover_url or (manif.meta.get("cover_url") if manif.meta else None)
        cover_source = (manif.meta.get("cover_source") if manif.meta else "") or ""

        logger.info("[%d/%d] Manifestation %d: '%s' (Format: %s)", idx, total, manif.id, work_title, format_type)

        if dry_run:
            stats["skipped"] += 1
            continue

        # Watermark-only path for existing AI covers
        if watermark_only or (cover_url and cover_source.startswith("llm_") and not cover_source.endswith("_watermarked")):
            if cover_url and os.path.isfile(DEFAULT_WATERMARK_ICON_PATH):
                filename = os.path.basename(cover_url)
                local_path = os.path.join(Config.BASE_DIR, "app", "static", "covers", filename)
                if os.path.isfile(local_path):
                    apply_corner_watermark(local_path, DEFAULT_WATERMARK_ICON_PATH, local_path)
                    meta = dict(manif.meta or {})
                    meta["cover_source"] = f"{cover_source}_watermarked" if cover_source else "llm_watermarked"
                    manif.meta = meta
                    db.session.commit()
                    stats["watermarked"] += 1
                    stats["processed"] += 1
                    logger.info("Applied corner watermark to manifestation %d", manif.id)
                    continue

        # AI Cover Generation path
        identifier = str(manif.barcode or manif.isbn13 or manif.id)
        result = fetch_llm_cover(
            identifier=identifier,
            title=work_title,
            author=author_name,
            user_id=user_id,
            format_type=format_type,
            allow_cloud_llm=True,
        )

        if result:
            img_path, source = result
            # Apply watermark if watermark image exists
            if os.path.isfile(DEFAULT_WATERMARK_ICON_PATH):
                local_file = os.path.join(Config.BASE_DIR, "app", "static", "covers", os.path.basename(img_path))
                apply_corner_watermark(local_file, DEFAULT_WATERMARK_ICON_PATH, local_file)
                source = f"{source}_watermarked"

            manif.cover_url = img_path
            meta = dict(manif.meta or {})
            meta["cover_url"] = img_path
            meta["cover_source"] = source
            if force_retry:
                meta["failed_llm_attempts"] = 0
            manif.meta = meta
            db.session.commit()

            stats["generated"] += 1
            stats["processed"] += 1
            logger.info("Generated AI cover for manifestation %d: %s", manif.id, img_path)
        else:
            stats["failed"] += 1
            logger.warning("Failed to generate cover for manifestation %d", manif.id)
            # Track failure for circuit breaker
            meta = dict(manif.meta or {})
            meta["failed_llm_attempts"] = meta.get("failed_llm_attempts", 0) + 1
            manif.meta = meta
            db.session.commit()

    logger.info("Batch completed: %s", stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch AI Cover Generation and Watermarking CLI")
    parser.add_argument("--batch-all-unwatermarked", action="store_true", help="Process all missing or unwatermarked AI covers")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of manifestations to process")
    parser.add_argument(
        "--dry-run", action="store_true", help="Log eligible manifestations without modifying database or generating images"
    )
    parser.add_argument("--watermark-only", action="store_true", help="Only watermark existing AI covers without invoking generation")
    parser.add_argument("--prompt-spec", type=str, default=None, help="Path to custom prompt specification markdown file")
    parser.add_argument(
        "--force-retry", action="store_true", help="Bypass the circuit breaker and retry all items regardless of failure count"
    )

    args = parser.parse_args()

    from run import app

    with app.app_context():
        manifestations = get_unwatermarked_manifestations(limit=args.limit)
        process_batch(manifestations, dry_run=args.dry_run, watermark_only=args.watermark_only, force_retry=args.force_retry)


if __name__ == "__main__":
    main()
