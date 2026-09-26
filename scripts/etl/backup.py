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
"""FRBR ETL backup snapshot creation and coverage verification.

Handles complete database state snapshots prior to destructive or reconciliation
operations, and verifies integrity and coverage of generated backups.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db import db
from app.db.contributions import (
    ManifestationContribution,
    WorkContribution,
    WorkPart,
)
from app.db.core import (
    EntityAuditLog,
    Expression,
    ImageScan,
    Item,
    ItemStatusLog,
    Manifestation,
    UserWorkIntent,
    Work,
    WorkExpansionLink,
)
from app.db.social import (
    EscalationRequest,
    SocialFeedback,
    SocialNote,
)


def create_complete_backup(backup_dir: Path) -> Path:
    """Create a complete verified backup covering all affected tables.

    :param backup_dir: Destination directory for the backup archive
    :return: Path to the generated and verified backup file
    :raises RuntimeError: If backup generation or verification fails
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"frbr_complete_snapshot_{timestamp}.json"

    # Core FRBR entities
    works = db.session.execute(select(Work)).scalars().all()
    expressions = db.session.execute(select(Expression)).scalars().all()
    manifestations = db.session.execute(select(Manifestation)).scalars().all()
    items = db.session.execute(select(Item)).scalars().all()

    # Dependent entities
    work_contributions = db.session.execute(select(WorkContribution)).scalars().all()
    manifestation_contributions = db.session.execute(select(ManifestationContribution)).scalars().all()
    work_parts = db.session.execute(select(WorkPart)).scalars().all()
    expansion_links = db.session.execute(select(WorkExpansionLink)).scalars().all()
    user_intents = db.session.execute(select(UserWorkIntent)).scalars().all()
    image_scans = db.session.execute(select(ImageScan)).scalars().all()
    social_feedback = db.session.execute(select(SocialFeedback)).scalars().all()
    social_notes = db.session.execute(select(SocialNote)).scalars().all()
    escalation_requests = db.session.execute(select(EscalationRequest)).scalars().all()
    audit_logs = db.session.execute(select(EntityAuditLog)).scalars().all()
    item_status_logs = db.session.execute(select(ItemStatusLog)).scalars().all()

    snapshot_data: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "2.0",
        "coverage": {
            "core_frbr": ["works", "expressions", "manifestations", "items"],
            "contributions": ["work_contributions", "manifestation_contributions"],
            "relationships": ["work_parts", "expansion_links"],
            "user_data": ["user_intents", "social_feedback", "social_notes"],
            "inventory": ["image_scans", "item_status_logs"],
            "audit": ["escalation_requests", "audit_logs"],
        },
        "counts": {
            "works": len(works),
            "expressions": len(expressions),
            "manifestations": len(manifestations),
            "items": len(items),
            "work_contributions": len(work_contributions),
            "manifestation_contributions": len(manifestation_contributions),
            "work_parts": len(work_parts),
            "expansion_links": len(expansion_links),
            "user_intents": len(user_intents),
            "image_scans": len(image_scans),
            "social_feedback": len(social_feedback),
            "social_notes": len(social_notes),
            "escalation_requests": len(escalation_requests),
            "audit_logs": len(audit_logs),
            "item_status_logs": len(item_status_logs),
        },
        "entities": {
            "works": [{"id": w.id, "title": w.title, "meta": w.meta, "raw_payload": w.raw_payload} for w in works],
            "expressions": [
                {
                    "id": e.id,
                    "work_id": e.work_id,
                    "content_type": e.content_type,
                    "language": e.language,
                    "kind": e.kind,
                }
                for e in expressions
            ],
            "manifestations": [
                {
                    "id": m.id,
                    "expression_id": m.expression_id,
                    "isbn13": m.isbn13,
                    "publisher": m.publisher,
                    "meta": m.meta,
                    "raw_payload": m.raw_payload,
                }
                for m in manifestations
            ],
            "items": [
                {
                    "id": i.id,
                    "manifestation_id": i.manifestation_id,
                    "owner_id": str(i.owner_id) if i.owner_id is not None else None,
                    "status": getattr(i, "status", None),
                }
                for i in items
            ],
            "work_contributions": [
                {
                    "id": wc.id,
                    "work_id": wc.work_id,
                    "contributor_id": wc.contributor_id,
                    "role": wc.role,
                    "sequence": wc.sequence,
                }
                for wc in work_contributions
            ],
            "manifestation_contributions": [
                {
                    "id": mc.id,
                    "manifestation_id": mc.manifestation_id,
                    "contributor_id": mc.contributor_id,
                    "role": mc.role,
                    "sequence": mc.sequence,
                }
                for mc in manifestation_contributions
            ],
            "work_parts": [
                {
                    "container_work_id": wp.container_work_id,
                    "part_work_id": wp.part_work_id,
                    "sequence": wp.sequence,
                }
                for wp in work_parts
            ],
            "expansion_links": [
                {
                    "id": el.id,
                    "base_work_id": el.base_work_id,
                    "expansion_work_id": el.expansion_work_id,
                }
                for el in expansion_links
            ],
            "user_intents": [
                {
                    "id": ui.id,
                    "work_id": ui.work_id,
                    "user_id": str(ui.user_id),
                    "status": ui.status,
                }
                for ui in user_intents
            ],
            "image_scans": [
                {
                    "id": isc.id,
                    "manifestation_id": isc.manifestation_id,
                    "file_path": isc.file_path,
                    "scan_type": isc.scan_type,
                }
                for isc in image_scans
            ],
            "social_feedback": [
                {
                    "id": sf.id,
                    "work_id": sf.work_id,
                    "manifestation_id": sf.manifestation_id,
                    "user_id": str(sf.user_id),
                    "rating": sf.rating,
                }
                for sf in social_feedback
            ],
            "social_notes": [
                {
                    "id": sn.id,
                    "work_id": sn.work_id,
                    "manifestation_id": sn.manifestation_id,
                    "user_id": str(sn.user_id),
                    "note": sn.note,
                }
                for sn in social_notes
            ],
            "escalation_requests": [
                {
                    "id": er.id,
                    "work_id": er.work_id,
                    "manifestation_id": er.manifestation_id,
                    "user_id": str(er.user_id),
                    "status": er.status,
                }
                for er in escalation_requests
            ],
            "audit_logs": [
                {
                    "id": al.id,
                    "entity_type": al.entity_type,
                    "entity_id": al.entity_id,
                    "change_type": al.change_type,
                }
                for al in audit_logs
            ],
            "item_status_logs": [
                {
                    "id": isl.id,
                    "item_id": isl.item_id,
                    "old_status": isl.old_status,
                    "new_status": isl.new_status,
                }
                for isl in item_status_logs
            ],
        },
    }

    try:
        backup_file.write_text(
            json.dumps(snapshot_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except OSError as exc:
        raise RuntimeError(f"Failed to write backup snapshot to {backup_file}: {exc}") from exc

    # Verify backup exists and is readable
    if not backup_file.exists() or backup_file.stat().st_size == 0:
        raise RuntimeError(f"Backup verification failed: file {backup_file} is missing or empty")

    # Verify backup can be loaded
    try:
        loaded = json.loads(backup_file.read_text(encoding="utf-8"))
        if "coverage" not in loaded or "entities" not in loaded:
            raise RuntimeError("Backup verification failed: missing required sections")
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Backup verification failed: cannot parse backup: {exc}") from exc

    return backup_file


def verify_backup_coverage(backup_file: Path) -> dict[str, Any]:
    """Verify that a backup file has complete coverage.

    :param backup_file: Path to the backup file
    :return: Verification result with coverage details
    """
    try:
        data = json.loads(backup_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"valid": False, "error": f"Cannot parse backup: {exc}"}

    # Check version first
    version = data.get("version", "1.0")
    if version < "2.0":
        return {"valid": False, "error": f"Backup version {version} is too old; requires 2.0+"}

    required_sections = ["coverage", "counts", "entities"]
    missing_sections = [s for s in required_sections if s not in data]
    if missing_sections:
        return {"valid": False, "error": f"Missing sections: {missing_sections}"}

    # Check coverage
    coverage = data["coverage"]
    required_coverage = [
        "core_frbr",
        "contributions",
        "relationships",
        "user_data",
        "inventory",
        "audit",
    ]
    missing_coverage = [c for c in required_coverage if c not in coverage]
    if missing_coverage:
        return {"valid": False, "error": f"Missing coverage: {missing_coverage}"}

    # Check entity counts
    counts = data["counts"]
    required_entities = [
        "works",
        "expressions",
        "manifestations",
        "items",
        "work_contributions",
        "manifestation_contributions",
        "work_parts",
        "expansion_links",
        "user_intents",
        "image_scans",
        "social_feedback",
        "social_notes",
    ]
    missing_entities = [e for e in required_entities if e not in counts]
    if missing_entities:
        return {"valid": False, "error": f"Missing entity counts: {missing_entities}"}

    return {
        "valid": True,
        "version": version,
        "timestamp": data.get("timestamp"),
        "counts": counts,
    }
