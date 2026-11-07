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
"""Audit and repair AI-generated cover bindings attached to wrong manifestations.

Inspects FRBR F3 Manifestation cover_url fields pointing to AI-generated images
(_gemini, _openai, _localsd, _dalle) and cross-checks them against Manifestation.isbn13,
Manifestation.id, and Item.manifestation_id. When a mismatch from historical database
migrations or ID shifts is detected, unbinds the cover and records an EntityAuditLog entry.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from urllib.parse import urlparse

# Add project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app import create_app
from app.db import db
from app.db.core import EntityAuditLog
from app.db.models import Item, Manifestation
from app.utils.isbn import canonicalize_isbn

AI_COVER_PATTERN = re.compile(
    r"^(?P<identifier>.+?)_(?P<suffix>gemini|openai|localsd|dalle|local)\.(?:jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)

GENERIC_COVER_PATTERN = re.compile(
    r"^(?P<identifier>.+?)\.(?:jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)


def inspect_manifestation_cover(manif: Manifestation) -> tuple[bool, str | None]:
    """Inspect a manifestation's cover_url for AI cover mismatches.

    Parameters
    ----------
    manif:
        The Manifestation record to inspect.

    Returns
    -------
    tuple[bool, str | None]
        (is_mismatch, reason_if_mismatch)
    """
    cover_url = manif.cover_url
    if not cover_url:
        return False, None

    parsed_path = urlparse(cover_url).path
    filename = os.path.basename(parsed_path)
    if not filename:
        return False, None

    match = AI_COVER_PATTERN.match(filename)
    is_llm_source = bool(manif.meta and isinstance(manif.meta, dict) and str(manif.meta.get("cover_source", "")).startswith("llm_"))

    if not match and not is_llm_source:
        return False, None

    if match:
        identifier = match.group("identifier")
    else:
        gen_match = GENERIC_COVER_PATTERN.match(filename)
        if not gen_match:
            return False, None
        identifier = gen_match.group("identifier")

    # 1. Item-prefixed identifier: item_<id>
    item_match = re.match(r"^item_(\d+)$", identifier, re.IGNORECASE)
    if item_match:
        target_item_id = int(item_match.group(1))
        item = db.session.execute(select(Item).where(Item.id == target_item_id)).scalar()
        if item and item.manifestation_id != manif.id:
            return (
                True,
                f"Cover keyed for Item #{target_item_id} (belonging to Manifestation #{item.manifestation_id}), "
                f"but bound to Manifestation #{manif.id}",
            )
        if not item:
            # Check if any attached item of this manifestation matches
            manif_item_ids = {it.id for it in getattr(manif, "items", [])}
            if manif_item_ids and target_item_id not in manif_item_ids:
                return (
                    True,
                    f"Cover keyed for missing Item #{target_item_id} not belonging to Manifestation #{manif.id}",
                )

    # 2. Manifestation-prefixed identifier: manifestation_<id> or manif_<id>
    manif_match = re.match(r"^(?:manifestation|manif)_(\d+)$", identifier, re.IGNORECASE)
    if manif_match:
        target_manif_id = int(manif_match.group(1))
        if target_manif_id != manif.id:
            return (
                True,
                f"Cover keyed for Manifestation #{target_manif_id}, but bound to Manifestation #{manif.id}",
            )

    # 3. ISBN-formatted identifier or 10/13 digit code
    raw_digits = re.sub(r"[^\dX]", "", identifier.upper())
    is_isbn_candidate = len(raw_digits) in (10, 13) or bool(canonicalize_isbn(identifier))
    if is_isbn_candidate:
        cover_isbn = canonicalize_isbn(identifier) or raw_digits
        manif_raw = re.sub(r"[^\dX]", "", manif.isbn13.upper()) if manif.isbn13 else None
        manif_isbn = (canonicalize_isbn(manif.isbn13) if manif.isbn13 else None) or manif_raw
        if manif_isbn and manif_isbn != cover_isbn:
            return (
                True,
                f"Cover ISBN {cover_isbn} does not match Manifestation #{manif.id} ISBN {manif_isbn}",
            )
        if not manif_isbn:
            other_id = db.session.execute(
                select(Manifestation.id).where(
                    db.or_(
                        Manifestation.isbn13 == cover_isbn,
                        Manifestation.isbn13 == raw_digits,
                    )
                )
            ).scalar()
            if other_id and other_id != manif.id:
                return (
                    True,
                    f"Cover ISBN {cover_isbn} belongs to Manifestation #{other_id}, " f"but bound to Manifestation #{manif.id}",
                )

    # 4. Pure integer identifier (could be legacy manifestation ID or item ID)
    if identifier.isdigit() and len(identifier) < 9:
        val = int(identifier)
        if val != manif.id:
            other_manif = db.session.execute(select(Manifestation.id).where(Manifestation.id == val)).scalar()
            if other_manif and other_manif != manif.id:
                return (
                    True,
                    f"Cover keyed for Manifestation #{val}, but bound to Manifestation #{manif.id}",
                )
            item = db.session.execute(select(Item).where(Item.id == val)).scalar()
            if item and item.manifestation_id != manif.id:
                return (
                    True,
                    f"Cover keyed for Item #{val} (belonging to Manifestation #{item.manifestation_id}), "
                    f"but bound to Manifestation #{manif.id}",
                )

    return False, None


def verify_and_repair_ai_covers(
    apply_changes: bool = False,
    batch_size: int = 500,
    requeue: bool = False,
) -> tuple[int, int]:
    """Inspect and optionally repair mismatched AI cover bindings.

    Parameters
    ----------
    apply_changes:
        If True, unbinds mismatched covers and records EntityAuditLog. If False, runs in dry-run mode.
    batch_size:
        Number of Manifestation records to process per batch for constant memory usage.
    requeue:
        If True, also resets cover_status on attached items for fresh generation.

    Returns
    -------
    tuple[int, int]
        (inspected_count, mismatch_count)
    """
    total_count_stmt = select(func.count()).select_from(Manifestation)  # pylint: disable=not-callable
    inspected = db.session.execute(total_count_stmt).scalar() or 0
    mismatch_count = 0

    mode_label = "APPLY" if apply_changes else "DRY RUN"
    print(f"Scanning {inspected} manifestations (Mode: {mode_label})...")

    offset = 0
    while True:
        stmt = (
            select(Manifestation)
            .options(
                selectinload(Manifestation.items),
            )
            .order_by(Manifestation.id)
            .offset(offset)
            .limit(batch_size)
        )
        batch: Sequence[Manifestation] = db.session.execute(stmt).scalars().all()
        if not batch:
            break

        batch_repaired = 0
        for manif in batch:
            is_mismatch, reason = inspect_manifestation_cover(manif)
            if not is_mismatch:
                continue

            mismatch_count += 1
            old_cover = manif.cover_url
            label = manif.label or f"Manifestation #{manif.id}"
            print(f"  [MISMATCH] Manifestation #{manif.id} ({label}): {reason}")

            if apply_changes:
                batch_repaired += 1
                manif.cover_url = None
                meta = dict(manif.meta or {})
                if "cover_source" in meta:
                    meta.pop("cover_source", None)
                manif.meta = meta
                flag_modified(manif, "meta")

                audit_log = EntityAuditLog(
                    entity_type="manifestation",
                    entity_id=manif.id,
                    change_type="ai_cover_unbind",
                    diff={
                        "cover_url": {"old": old_cover, "new": None},
                        "reason": reason,
                    },
                    logged_at=datetime.now(UTC),
                )
                db.session.add(audit_log)

                if requeue:
                    for item in getattr(manif, "items", []):
                        item.cover_status = "pending"
                        item.cover_url = None

        if apply_changes and batch_repaired > 0:
            db.session.commit()

        offset += len(batch)
        if len(batch) < batch_size:
            break

    if apply_changes:
        print(f"Repair complete: {mismatch_count} mismatched AI covers unbound and committed.")
    else:
        print(f"Dry run complete: {mismatch_count} mismatched AI covers detected. Run with --apply to execute changes.")

    return inspected, mismatch_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and repair AI cover bindings on FRBR Manifestations.")
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply repair changes to database. Default is dry-run mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Explicitly run in dry-run mode (default behavior).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for database pagination (default: 500).",
    )
    parser.add_argument(
        "--requeue",
        action="store_true",
        default=False,
        help="Reset cover_status on attached items for fresh generation.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Bypass interactive production confirmation prompt.",
    )
    args = parser.parse_args()

    apply_mode = args.apply and not args.dry_run

    app = create_app()
    with app.app_context():
        # Operational script guard for production environments
        is_production = os.environ.get("FLASK_ENV") == "production"
        is_test = "pytest" in sys.modules

        if apply_mode and is_production and not is_test and not args.force:
            if os.environ.get("ALLOW_PROD_REPAIR") != "1":
                db_name = db.engine.url.database or "iqoqo"
                print(
                    f"\n⚠️  WARNING: Running destructive cover unbinding in PRODUCTION on database '{db_name}'.",
                    file=sys.stderr,
                )
                try:
                    confirm = input(f"Type '{db_name}' to confirm AI cover repair: ")
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted by user.", file=sys.stderr)
                    sys.exit(1)
                if confirm.strip() != db_name:
                    print("Database name mismatch. Aborted.", file=sys.stderr)
                    sys.exit(1)

        verify_and_repair_ai_covers(
            apply_changes=apply_mode,
            batch_size=args.batch_size,
            requeue=args.requeue,
        )


if __name__ == "__main__":
    main()
