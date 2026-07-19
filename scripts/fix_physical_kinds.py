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
Interactive CLI tool for auditing and fixing non-canonical physical kind
(format) values in the iqoqo database.

Usage modes
-----------

**Audit (default):** ``make fix-physical-kinds``

Scans ``Manifestation.meta['format']`` and prints a table of all
non-canonical values grouped by (format_value, content_type).

**Interactive:** ``make fix-physical-kinds ARGS="--interactive"``

Walks you through each distinct non-canonical value, prompts for a
canonical mapping, and writes selections to ``shared/format_mappings.yaml``.

**Apply:** ``make fix-physical-kinds ARGS="--apply"``

Reads ``shared/format_mappings.yaml`` and executes SQL UPDATEs to fix all
matching ``Manifestation.meta`` rows.

**Dry-run apply:** ``make fix-physical-kinds ARGS="--apply --dry-run"``

Shows the SQL statements and affected row counts without modifying the
database.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.core.format_normalizer import _CANONICAL_FORMATS  # noqa: E402
from app.core.taxonomy import FORMAT_TO_CATEGORY  # noqa: E402
from app.db import db  # noqa: E402
from app.db.core import Expression, Manifestation  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
MAPPINGS_FILE = ROOT_DIR / "shared" / "format_mappings.yaml"


# ---------------------------------------------------------------------------
# --- Database queries -------------------------------------------------------
# ---------------------------------------------------------------------------


def get_non_canonical_rows(content_type: str | None = None, limit: int | None = None):
    """Query manifestations with non-canonical or NULL format values.

    Returns a list of dicts: ``{format_value, content_type, count, titles}``.
    """
    canonical_list = list(_CANONICAL_FORMATS)

    # Non-canonical (non-NULL) formats
    q_nc = db.session.query(
        Manifestation.meta["format"].as_string().label("format_value"),  # pylint: disable=not-callable
        Expression.content_type.label("content_type"),
        db.func.count(Manifestation.id).label("cnt"),  # pylint: disable=not-callable
    )
    q_nc = q_nc.join(Expression, Manifestation.expression_id == Expression.id)
    q_nc = q_nc.filter(Manifestation.meta["format"].as_string().isnot(None))  # pylint: disable=not-callable
    if content_type:
        q_nc = q_nc.filter(Expression.content_type == content_type)
    if canonical_list:
        q_nc = q_nc.filter(Manifestation.meta["format"].as_string().notin_(canonical_list))  # pylint: disable=not-callable
    q_nc = q_nc.group_by(Manifestation.meta["format"].as_string(), Expression.content_type)  # pylint: disable=not-callable

    # NULL formats
    q_null = db.session.query(
        db.literal(None).label("format_value"),
        Expression.content_type.label("content_type"),
        db.func.count(Manifestation.id).label("cnt"),  # pylint: disable=not-callable
    )
    q_null = q_null.join(Expression, Manifestation.expression_id == Expression.id)
    q_null = q_null.filter(Manifestation.meta["format"].as_string().is_(None))  # pylint: disable=not-callable
    if content_type:
        q_null = q_null.filter(Expression.content_type == content_type)
    q_null = q_null.group_by(Expression.content_type)

    # Union
    q_union = q_nc.union_all(q_null)
    if limit:
        q_union = q_union.limit(limit)
    rows = q_union.all()

    # Build table with example titles
    result = []
    for fmt_val, ct, cnt in rows:
        # Get example titles for this (format_value, content_type) combo
        titles: list[str] = []
        tq = db.session.query(Manifestation.id, Manifestation.meta["title"].as_string().label("title"))  # pylint: disable=not-callable
        tq = tq.join(Expression, Manifestation.expression_id == Expression.id)
        if ct:
            tq = tq.filter(Expression.content_type == ct)
        if fmt_val is not None:
            tq = tq.filter(Manifestation.meta["format"].as_string() == fmt_val)  # pylint: disable=not-callable
        else:
            tq = tq.filter(Manifestation.meta["format"].as_string().is_(None))  # pylint: disable=not-callable
        title_rows = tq.limit(3).all()
        for _mid, title in title_rows:
            titles.append(title or "(no title)")

        result.append(
            {
                "format_value": fmt_val,
                "content_type": ct,
                "count": cnt,
                "titles": titles,
            }
        )

    return result


# ---------------------------------------------------------------------------
# --- Audit mode -------------------------------------------------------------
# ---------------------------------------------------------------------------


def audit_mode(content_type: str | None = None, limit: int | None = None):
    """Print an audit table of non-canonical format values."""
    rows = get_non_canonical_rows(content_type=content_type, limit=limit)

    if not rows:
        print("\n✅ No non-canonical or NULL format values found. Everything looks good!")
        return 0

    # Determine column widths
    fmt_width = max(len(str(r["format_value"])) for r in rows)
    ct_width = max(len(str(r["content_type"])) for r in rows)
    fmt_width = max(fmt_width, 16)
    ct_width = max(ct_width, 12)

    print(f"\n{'=' * 80}")
    print("  AUDIT: Non-canonical & NULL format values")
    print(f"  {'=' * 78}")

    # Header
    header = f"  {'STORED VALUE':<{fmt_width}}  {'CONTENT TYPE':<{ct_width}}  {'COUNT':>7}  {'EXAMPLE TITLES'}"
    print(header)
    print(f"  {'-' * fmt_width}  {'-' * ct_width}  {'-' * 7}  {'-' * 40}")

    for r in rows:
        fmt_str = str(r["format_value"]) if r["format_value"] is not None else "NULL"
        ct_str = str(r["content_type"]) if r["content_type"] else "-"
        count_str = str(r["count"])
        title_bits = "; ".join(r["titles"][:3])
        if not title_bits:
            title_bits = "(no titles)"
        if len(title_bits) > 50:
            title_bits = title_bits[:47] + "..."

        print(f"  {fmt_str:<{fmt_width}}  {ct_str:<{ct_width}}  {count_str:>7}  {title_bits}")

    print(f"\n  Total distinct (value, content_type) pairs: {len(rows)}")
    total_items = sum(r["count"] for r in rows)
    print(f"  Total items affected: {total_items}")
    print("\n  Run with --interactive to build mappings, then --apply to fix.")
    return 0


# ---------------------------------------------------------------------------
# --- Interactive mode -------------------------------------------------------
# ---------------------------------------------------------------------------


def _get_valid_formats_for_category(category: str | None) -> list[str]:
    """Return list of valid MediaFormat IDs for the given content type."""
    if not category:
        return list(_CANONICAL_FORMATS)
    return sorted(fmt_id for fmt_id, cat in FORMAT_TO_CATEGORY.items() if cat == category)


def _write_mappings_file(mappings: dict[str, Any]) -> None:
    """Write the formatted mappings dict to shared/format_mappings.yaml."""
    MAPPINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(mappings, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _read_existing_mappings() -> dict[str, Any]:
    """Read existing mappings from shared/format_mappings.yaml."""
    if not MAPPINGS_FILE.exists():
        return {"format_normalizations": {}}
    with open(MAPPINGS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {"format_normalizations": {}}
    if "format_normalizations" not in data:
        data["format_normalizations"] = {}
    return data


def interactive_mode(content_type: str | None = None, limit: int | None = None):
    """Walk the user through each non-canonical value and build mappings."""
    rows = get_non_canonical_rows(content_type=content_type, limit=limit)
    if not rows:
        print("\n✅ No non-canonical or NULL format values found.")
        return 0

    existing = _read_existing_mappings()
    norms = existing["format_normalizations"]
    if norms is None:
        norms = {}
    # Ensure null key is a dict
    null_mappings: dict[str, str] = {}
    if isinstance(norms.get("null"), dict):
        null_mappings = dict(norms["null"])

    changes = 0
    skipped = 0

    for r in rows:
        fmt_val = r["format_value"]
        ct = r["content_type"]
        cnt = r["count"]

        if fmt_val is not None:
            # Check if already mapped
            fmt_key = str(fmt_val)
            if fmt_key in norms:
                print(f"\n  '{fmt_key}' already mapped to '{norms[fmt_key]}' — skipping")
                skipped += 1
                continue

            # Prompt for mapping
            print(f"\n{'-' * 60}")
            print(f"  Stored value: '{fmt_val}'")
            print(f"  Content type:  {ct or '-'}")
            print(f"  Count:         {cnt}")
            print(f"  Examples:      {'; '.join(r['titles'][:3])}")

            valid_formats = _get_valid_formats_for_category(ct)
            if not valid_formats:
                valid_formats = sorted(_CANONICAL_FORMATS)

            print("\n  Choose canonical format:")
            for i, fmt_id in enumerate(valid_formats, 1):
                label = fmt_id  # simpler display
                print(f"    {i:>2}. {label}")
            print("    0. Skip")

            while True:
                try:
                    choice = input(f"  Enter number (1-{len(valid_formats)}, 0 to skip): ").strip()
                    if choice == "0":
                        print(f"  Skipping '{fmt_val}'")
                        skipped += 1
                        break
                    idx = int(choice) - 1
                    if 0 <= idx < len(valid_formats):
                        selected = valid_formats[idx]
                        if selected not in _CANONICAL_FORMATS:
                            print(f"  ⚠ '{selected}' is not a valid canonical format. Try again.")
                            continue
                        norms[fmt_key] = selected
                        changes += 1
                        print(f"  ✅ Mapped '{fmt_val}' → '{selected}'")
                        break
                    print(f"  Invalid choice. Enter 1-{len(valid_formats)} or 0.")
                except (ValueError, EOFError, KeyboardInterrupt):
                    print("\n  Aborting interactive mode.")
                    _write_mappings_file(existing)
                    print(f"\n  Saved {changes} mapping(s). Run again with --interactive to continue.")
                    return 0
        else:
            # NULL value
            print(f"\n{'-' * 60}")
            print("  NULL format")
            print(f"  Content type:  {ct or '-'}")
            print(f"  Count:         {cnt}")
            print(f"  Examples:      {'; '.join(r['titles'][:3])}")

            # Check if already mapped in null section
            ct_str = str(ct) if ct else "__none__"
            if ct_str in null_mappings:
                print(f"  Already mapped NULL for '{ct}' to '{null_mappings[ct_str]}' — skipping")
                skipped += 1
                continue

            valid_formats = _get_valid_formats_for_category(ct)
            if not valid_formats:
                valid_formats = sorted(_CANONICAL_FORMATS)

            # Bulk option for large counts
            bulk_hint = ""
            if cnt >= 100:
                bulk_hint = f" (bulk: {cnt} items)"

            print(f"\n  Map NULL format for '{ct}'{bulk_hint} to which physical kind?")
            for i, fmt_id in enumerate(valid_formats, 1):
                print(f"    {i:>2}. {fmt_id}")
            print("    0. Skip")

            while True:
                try:
                    choice = input(f"  Enter number (1-{len(valid_formats)}, 0 to skip): ").strip()
                    if choice == "0":
                        print(f"  Skipping NULL for '{ct}'")
                        skipped += 1
                        break
                    idx = int(choice) - 1
                    if 0 <= idx < len(valid_formats):
                        selected = valid_formats[idx]
                        if selected not in _CANONICAL_FORMATS:
                            print(f"  ⚠ '{selected}' is not a valid canonical format. Try again.")
                            continue
                        null_mappings[ct_str] = selected
                        changes += 1
                        print(f"  ✅ Mapped NULL/{ct} → '{selected}'")
                        break
                    print(f"  Invalid choice. Enter 1-{len(valid_formats)} or 0.")
                except (ValueError, EOFError, KeyboardInterrupt):
                    print("\n  Aborting interactive mode.")
                    if null_mappings:
                        norms["null"] = null_mappings
                    else:
                        norms.pop("null", None)
                    _write_mappings_file(existing)
                    print(f"\n  Saved {changes} mapping(s). Run again with --interactive to continue.")
                    return 0

    # Write all mappings
    if null_mappings:
        norms["null"] = null_mappings
    elif "null" in norms:
        del norms["null"]
    existing["format_normalizations"] = norms
    _write_mappings_file(existing)

    print(f"\n{'=' * 60}")
    print("  Interactive mapping complete.")
    print(f"  New mappings written: {changes}")
    print(f"  Skipped:              {skipped}")
    print(f"  File:                 {MAPPINGS_FILE}")
    print("\n  Run with --apply to fix the database, or --apply --dry-run to preview.")
    return 0


# ---------------------------------------------------------------------------
# --- Apply mode helpers -----------------------------------------------------
# ---------------------------------------------------------------------------


def _update_manifestation_format(raw_val: str, target: str) -> int:
    """Update a single manifestation's meta['format'] in-place.

    Uses PostgreSQL jsonb_set when available, falls back to SQLAlchemy
    model-level update for SQLite (test environment).
    """
    is_pg = db.engine.dialect.name == "postgresql"

    if is_pg:
        update_sql = """
            UPDATE catalog.manifestations
            SET meta = jsonb_set(meta, '{format}', to_jsonb(:target::text), true)
            WHERE meta ->> 'format' = :raw_val
        """
        result = db.session.execute(db.text(update_sql), {"target": target, "raw_val": raw_val})
        db.session.commit()
        return result.rowcount or 0

    # SQLite fallback: use SQLAlchemy model update
    mfns = Manifestation.query.filter(Manifestation.meta["format"].as_string() == raw_val).all()  # pylint: disable=not-callable
    count = 0
    for m in mfns:
        m.meta["format"] = target
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(m, "meta")
        count += 1
    db.session.commit()
    return count


def _update_null_format(ct: str, target: str) -> int:
    """Update NULL format manifestations for a given content type."""
    is_pg = db.engine.dialect.name == "postgresql"

    if is_pg:
        update_sql = """
            UPDATE catalog.manifestations
            SET meta = jsonb_set(meta, '{format}', to_jsonb(:target::text), true)
            FROM catalog.expressions
            WHERE catalog.manifestations.expression_id = catalog.expressions.id
              AND catalog.manifestations.meta ->> 'format' IS NULL
              AND catalog.expressions.content_type = :ct
        """
        result = db.session.execute(db.text(update_sql), {"target": target, "ct": ct})
        db.session.commit()
        return result.rowcount or 0

    # SQLite fallback
    mfns = (
        Manifestation.query.join(Expression, Manifestation.expression_id == Expression.id)
        .filter(Manifestation.meta["format"].as_string().is_(None))  # pylint: disable=not-callable
        .filter(Expression.content_type == ct)
        .all()
    )
    count = 0
    for m in mfns:
        if m.meta is None:
            m.meta = {}
        m.meta["format"] = target
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(m, "meta")
        count += 1
    db.session.commit()
    return count


# ---------------------------------------------------------------------------
# --- Apply mode -------------------------------------------------------------
# ---------------------------------------------------------------------------


def apply_mode(dry_run: bool = False):
    """Read format_mappings.yaml and execute UPDATEs to fix non-canonical values.

    Args:
        dry_run: If True, print SQL and counts without modifying DB.
    """
    if not MAPPINGS_FILE.exists():
        print("❌ No format_mappings.yaml found. Run with --interactive first.")
        return 1

    with open(MAPPINGS_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        print("❌ format_mappings.yaml is not a valid dict.")
        return 1

    norms = data.get("format_normalizations")
    if not norms or not isinstance(norms, dict):
        print("❌ No format_normalizations defined in format_mappings.yaml. Run with --interactive first.")
        return 1

    total_updated = 0

    def _validate_target(target: str) -> bool:
        if target not in _CANONICAL_FORMATS:
            print(f"❌ Invalid target format '{target}' — not a canonical MediaFormat value.")
            return False
        return True

    # Apply exact-match mappings
    for raw_val, target in norms.items():
        if raw_val == "null":
            continue
        if not isinstance(target, str):
            continue
        if not _validate_target(target):
            continue

        # Count
        count_q = db.session.query(db.func.count(Manifestation.id)).filter(Manifestation.meta["format"].as_string() == raw_val)  # pylint: disable=not-callable,line-too-long
        affected = count_q.scalar() or 0

        if affected == 0:
            print(f"  (no rows match '{raw_val}')")
            continue

        if dry_run:
            print(f"\n  [DRY RUN] UPDATE {affected} rows: 'meta'->>'format' = '{raw_val}' → '{target}'")
            print("    -- update manifestations set meta['format'] = '{target}'")
            print(f"    -- where meta->>'format' = '{raw_val}';")
        else:
            updated = _update_manifestation_format(raw_val, target)
            print(f"  ✅ Updated {updated} rows: '{raw_val}' → '{target}'")
            total_updated += updated

    # Apply NULL + content_type mappings
    null_mappings = norms.get("null")
    if isinstance(null_mappings, dict):
        for ct, target in null_mappings.items():
            if not isinstance(target, str):
                continue
            if not _validate_target(target):
                continue

            # Count
            count_q = (
                db.session.query(db.func.count(Manifestation.id))  # pylint: disable=not-callable
                .join(Expression, Manifestation.expression_id == Expression.id)
                .filter(Manifestation.meta["format"].as_string().is_(None))  # pylint: disable=not-callable
                .filter(Expression.content_type == ct)
            )
            affected = count_q.scalar() or 0

            if affected == 0:
                print(f"  (no NULL rows match content_type='{ct}')")
                continue

            if dry_run:
                print(f"\n  [DRY RUN] UPDATE {affected} NULL rows (content_type='{ct}'): → '{target}'")
                print("    -- update manifestations set meta['format'] = '{target}'")
                print("    -- where meta->>'format' is null")
                print(f"    -- and expression.content_type = '{ct}';")
            else:
                updated = _update_null_format(ct, target)
                print(f"  ✅ Updated {updated} NULL rows (content_type='{ct}'): → '{target}'")
                total_updated += updated

    if dry_run:
        print("\n  [DRY RUN] Complete. Run without --dry-run to apply changes.")
    else:
        print(f"\n  ✅ Apply complete. Total rows updated: {total_updated}")
        print("  💡 Consider rebuilding the search index if FTS indexes meta['format'].")

    return 0


# ---------------------------------------------------------------------------
# --- Main entry point -------------------------------------------------------
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and fix non-canonical physical kind (format) values in the iqoqo database.")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Walk through each distinct value and build format mappings.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply format_mappings.yaml to fix the database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --apply: preview SQL and affected counts without modifying database.",
    )
    parser.add_argument(
        "--content-type",
        type=str,
        default=None,
        help="Restrict to specific content type (e.g., movie, music, text).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of distinct (format, content_type) pairs.",
    )

    args = parser.parse_args()

    # Mutually exclusive-ish modes
    if args.apply and args.interactive:
        print("❌ Cannot use --interactive and --apply together.")
        return 1

    if args.dry_run and not args.apply:
        print("⚠ --dry-run requires --apply.")
        return 1

    app = create_app()
    with app.app_context():
        if args.interactive:
            return interactive_mode(content_type=args.content_type, limit=args.limit)
        if args.apply:
            return apply_mode(dry_run=args.dry_run)
        return audit_mode(content_type=args.content_type, limit=args.limit)


if __name__ == "__main__":
    sys.exit(main())
