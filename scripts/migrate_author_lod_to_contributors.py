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
"""Backfill legacy Work-attached author LOD links onto Contributor entities.

Legacy releases attached DBpedia person SemanticLinks directly to Works
(``entity_type="work"``, ``attributes["role"] == "author"`` or ``dbo:Person``),
causing cross-work ``owl:sameAs`` collapse in RDF exports.  This script
idempotently resolves or creates a matching :class:`~app.db.contributions.Contributor`
and :class:`~app.db.contributions.WorkContribution` for each legacy row, re-points
the surviving link to ``entity_type="contributor"``, deduplicates conflicts by
deterministic precedence, and logs changes to :class:`~app.db.core.EntityAuditLog`.

Usage:
    python scripts/migrate_author_lod_to_contributors.py --dry-run
    python scripts/migrate_author_lod_to_contributors.py --apply [--yes]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.contributions import Contributor, WorkContribution
from app.db.core import EntityAuditLog, SemanticLink, Work

logger = logging.getLogger(__name__)


def _is_legacy_author_link(link: SemanticLink) -> bool:
    """Return True when a Work-scoped SemanticLink represents a legacy author/person link."""
    if link.entity_type != "work":
        return False
    attrs = link.attributes if isinstance(link.attributes, dict) else {}
    if str(attrs.get("role", "")).strip().lower() == "author":
        return True
    for key in ("entity_type", "type", "dbo_type", "rdf_type", "dbpedia_type"):
        raw = str(attrs.get(key, "")).strip().lower()
        if raw in {"person", "dbo:person", "foaf:person", "schema:person"} or "person" in raw:
            return True
    return False


def _rank_link(link: SemanticLink) -> tuple[int, int, int, float, int]:
    """Deterministic precedence: verified > accepted > suggested > higher confidence > older id."""
    status = (link.status or "").strip().lower()
    return (
        1 if link.verified else 0,
        1 if status == "accepted" else 0,
        1 if status == "suggested" else 0,
        float(link.confidence or 0.0),
        -(link.id or 0),
    )


def _pick_author_name(link: SemanticLink, work: Work | None) -> str | None:
    """Extract the most specific author display name for a legacy Work author link."""
    if link.pref_label and link.pref_label.strip():
        return link.pref_label.strip()
    if work and isinstance(work.meta, dict):
        authors = work.meta.get("authors")
        if isinstance(authors, list):
            for entry in authors:
                if isinstance(entry, str) and entry.strip():
                    return entry.strip()
        single = work.meta.get("author")
        if isinstance(single, str) and single.strip():
            return single.strip()
    return None


def _get_or_create_contributor(session: Session, work: Work | None, author_name: str) -> Contributor:
    """Resolve existing person Contributor (preferring WorkContribution on work) or create one."""
    clean_name = author_name.strip()
    lowered = clean_name.lower()

    if work is not None:
        for wc in sorted(work.contributions or [], key=lambda item: (item.sequence or 0, item.id or 0)):
            if wc.contributor and (wc.contributor.name or "").strip().lower() == lowered:
                return wc.contributor

    existing = (
        session.execute(
            select(Contributor)
            .where(func.lower(func.trim(Contributor.name)) == lowered, Contributor.type == "person")
            .order_by(Contributor.id.asc())
        )
        .scalars()
        .first()
    )
    if existing is not None:
        return existing

    try:
        with session.begin_nested():
            contributor = Contributor(name=clean_name, type="person")
            session.add(contributor)
            session.flush()
            return contributor
    except IntegrityError:
        resolved = (
            session.execute(select(Contributor).where(Contributor.name == clean_name, Contributor.type == "person")).scalars().first()
        )
        if resolved is None:
            raise
        return resolved


def migrate_author_lod_links(
    session: Session,
    *,
    dry_run: bool = False,
    actor_user_id: Any = None,
) -> dict[str, int]:
    """Migrate legacy Work-scoped author SemanticLinks onto Contributor rows.

    Returns counts for ``scanned``, ``migrated``, ``deduplicated``, and ``skipped``.
    """
    work_links = (
        session.execute(select(SemanticLink).where(SemanticLink.entity_type == "work").order_by(SemanticLink.id.asc())).scalars().all()
    )
    legacy_links = [link for link in work_links if _is_legacy_author_link(link)]

    summary: dict[str, int] = {
        "scanned": len(legacy_links),
        "migrated": 0,
        "deduplicated": 0,
        "skipped": 0,
    }
    planned_keys: set[tuple[str, str, str]] = set()

    for link in legacy_links:
        if session.get(SemanticLink, link.id) is None:
            # Already removed in an earlier deduplication step in this loop
            continue

        work = session.get(Work, link.entity_id)
        author_name = _pick_author_name(link, work)
        if not author_name:
            summary["skipped"] += 1
            continue

        if dry_run:
            plan_key = (author_name.lower(), str(link.authority), str(link.external_uri))
            existing_contrib = (
                session.execute(
                    select(Contributor)
                    .where(func.lower(func.trim(Contributor.name)) == author_name.lower(), Contributor.type == "person")
                    .order_by(Contributor.id.asc())
                )
                .scalars()
                .first()
            )
            has_db_conflict = False
            if existing_contrib is not None:
                conflict = session.execute(
                    select(SemanticLink).where(
                        SemanticLink.entity_type == "contributor",
                        SemanticLink.entity_id == existing_contrib.id,
                        SemanticLink.authority == link.authority,
                        SemanticLink.external_uri == link.external_uri,
                    )
                ).scalar_one_or_none()
                has_db_conflict = conflict is not None
            if has_db_conflict or plan_key in planned_keys:
                summary["deduplicated"] += 1
            else:
                planned_keys.add(plan_key)
                summary["migrated"] += 1
            continue

        contributor = _get_or_create_contributor(session, work, author_name)
        if work is not None:
            existing_wc = (
                session.execute(
                    select(WorkContribution).where(
                        WorkContribution.work_id == work.id,
                        WorkContribution.contributor_id == contributor.id,
                    )
                )
                .scalars()
                .first()
            )
            if existing_wc is None:
                session.add(
                    WorkContribution(
                        work_id=work.id,
                        contributor_id=contributor.id,
                        role="author",
                        sequence=0,
                    )
                )
                session.flush()

        existing_target = (
            session.execute(
                select(SemanticLink)
                .where(
                    SemanticLink.entity_type == "contributor",
                    SemanticLink.entity_id == contributor.id,
                    SemanticLink.authority == link.authority,
                    SemanticLink.external_uri == link.external_uri,
                )
                .order_by(SemanticLink.id.asc())
            )
            .scalars()
            .first()
        )

        if existing_target is not None:
            winner, loser = (link, existing_target) if _rank_link(link) > _rank_link(existing_target) else (existing_target, link)
            old_entity_type = loser.entity_type
            old_entity_id = loser.entity_id
            loser_id = loser.id

            if winner is link:
                # Copy winner scalar fields onto the kept row only after freeing or deleting loser cleanly
                winner.entity_type = "contributor"
                winner.entity_id = contributor.id
            session.delete(loser)
            session.flush()
            summary["deduplicated"] += 1
            session.add(
                EntityAuditLog(
                    entity_type="contributor",
                    entity_id=contributor.id,
                    actor_id=actor_user_id,
                    change_type="semantic_link_deduplicated",
                    diff={
                        "kept_link_id": winner.id,
                        "deleted_link_id": loser_id,
                        "from_entity_type": old_entity_type,
                        "from_entity_id": old_entity_id,
                        "authority": winner.authority,
                        "external_uri": winner.external_uri,
                    },
                )
            )
        else:
            old_work_id = link.entity_id
            link.entity_type = "contributor"
            link.entity_id = contributor.id
            summary["migrated"] += 1
            session.add(
                EntityAuditLog(
                    entity_type="contributor",
                    entity_id=contributor.id,
                    actor_id=actor_user_id,
                    change_type="semantic_link_migrated_to_contributor",
                    diff={
                        "link_id": link.id,
                        "from_entity_type": "work",
                        "from_entity_id": old_work_id,
                        "to_entity_type": "contributor",
                        "to_entity_id": contributor.id,
                        "authority": link.authority,
                        "external_uri": link.external_uri,
                    },
                )
            )

    if not dry_run:
        session.commit()

    return summary


def _confirm_production_execution() -> None:
    """Require explicit confirmation of target DB name when running against production."""
    if os.environ.get("FLASK_ENV") != "production":
        return
    db_url = os.environ.get("DATABASE_URL", "")
    target_name = db_url.rsplit("/", 1)[-1].split("?")[0] or "iqoqo"
    entered = input(f"Production environment detected. Type target database name '{target_name}' to proceed: ").strip()
    if entered != target_name:
        raise RuntimeError(f"Confirmation mismatch: expected '{target_name}', got '{entered}'. Aborting.")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for author LOD contributor backfill."""
    parser = argparse.ArgumentParser(description="Backfill legacy Work author SemanticLinks onto Contributor records.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", help="Inspect and report changes without mutating DB rows (default).")
    mode_group.add_argument("--apply", action="store_true", help="Persist Contributor backfill and deduplication changes.")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation in non-production environments.")
    args = parser.parse_args(argv)

    dry_run = not args.apply
    if not dry_run:
        _confirm_production_execution()

    from app import create_app
    from app.db import db

    app = create_app()
    with app.app_context():
        result = migrate_author_lod_links(db.session, dry_run=dry_run)
        mode_label = "DRY RUN" if dry_run else "APPLIED"
        print(
            f"[{mode_label}] scanned={result['scanned']} migrated={result['migrated']} deduplicated={result['deduplicated']} skipped={result['skipped']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
