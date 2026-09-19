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
"""Safe FRBR ETL Reconciliation with Complete Relationship Coverage.

This module implements relationship-complete FRBR duplicate reconciliation with:
- Complete dependency inventory for Work and Manifestation entities
- Explicit reparent/conflict policies for each relationship
- Dry-run merge plan generation showing all proposed changes
- Complete recovery boundary with backup verification
- Transactional application with rollback on failure
- Idempotent execution with conflict detection

Usage:
    python scripts/etl_frbr_safe.py [--dry-run] [--backup-dir DIR] [--verbose]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm.attributes import flag_modified

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.db import db  # noqa: E402
from app.db.contributions import (  # noqa: E402
    ExpressionContribution,
    ManifestationContribution,
    WorkContribution,
    WorkPart,
)
from app.db.core import (  # noqa: E402
    EntityAuditLog,
    Expression,
    ImageScan,
    Item,
    ItemStatusLog,
    Manifestation,
    UserWorkIntent,
    Work,
    WorkExpansionLink,
    _CATALOG_PFX,
    _INVENTORY_PFX,
)
from app.db.social import _SOCIAL_PFX  # noqa: E402
from app.db.social import (  # noqa: E402
    EscalationRequest,
    SharedCollection,
    SocialFeedback,
    SocialNote,
)

ISBN_CLEAN_PATTERN = re.compile(r"[^0-9X]")


class ReparentPolicy(Enum):
    """Policy for handling dependent records during merge."""

    REPARENT = "reparent"  # Move to canonical entity
    DELETE = "delete"  # Delete if duplicate would conflict
    ABORT = "abort"  # Abort merge if conflict detected
    MERGE_METADATA = "merge_metadata"  # Merge JSON metadata fields


@dataclass
class RelationshipInventory:
    """Complete inventory of relationships for an entity type."""

    entity_type: str  # "Work" or "Manifestation"
    relationships: list[dict[str, Any]] = field(default_factory=list)

    def add_relationship(
        self,
        model_class: str,
        fk_column: str,
        policy: ReparentPolicy,
        unique_constraint: str | None = None,
        notes: str = "",
    ) -> None:
        """Add a relationship to the inventory."""
        self.relationships.append(
            {
                "model": model_class,
                "fk_column": fk_column,
                "policy": policy.value,
                "unique_constraint": unique_constraint,
                "notes": notes,
            }
        )


@dataclass
class MergeOperation:
    """A single operation in a merge plan."""

    operation_type: str  # "reparent", "delete", "merge_metadata", "conflict"
    source_id: int
    target_id: int
    model_class: str
    record_count: int = 0
    conflict_details: str | None = None


@dataclass
class MergePlan:
    """Complete merge plan for a duplicate entity."""

    entity_type: str  # "Work" or "Manifestation"
    canonical_id: int
    duplicate_id: int
    operations: list[MergeOperation] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def add_operation(self, operation: MergeOperation) -> None:
        """Add an operation to the plan."""
        self.operations.append(operation)

    def add_conflict(self, conflict: str) -> None:
        """Add a conflict to the plan."""
        self.conflicts.append(conflict)

    def has_conflicts(self) -> bool:
        """Check if the plan has any conflicts."""
        return len(self.conflicts) > 0


def build_work_relationship_inventory() -> RelationshipInventory:
    """Build complete relationship inventory for Work entity."""
    inventory = RelationshipInventory(entity_type="Work")

    # Core FRBR relationships
    inventory.add_relationship(
        model_class="Expression",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Expressions are reparented to canonical Work",
    )

    # Contribution relationships
    inventory.add_relationship(
        model_class="WorkContribution",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Contributions are reparented to canonical Work",
    )

    # Work part relationships (container)
    inventory.add_relationship(
        model_class="WorkPart",
        fk_column="container_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Work parts where this Work is container are reparented",
    )

    # Work part relationships (member)
    inventory.add_relationship(
        model_class="WorkPart",
        fk_column="part_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Work parts where this Work is member are reparented",
    )

    # Expansion relationships
    inventory.add_relationship(
        model_class="WorkExpansionLink",
        fk_column="base_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Expansion links where this Work is base are reparented",
    )

    inventory.add_relationship(
        model_class="WorkExpansionLink",
        fk_column="expansion_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Expansion links where this Work is expansion are reparented",
    )

    # User intent relationships
    inventory.add_relationship(
        model_class="UserWorkIntent",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        unique_constraint="uq_user_work_intent",
        notes="User intents are reparented; conflicts abort merge",
    )

    # Social feedback relationships
    inventory.add_relationship(
        model_class="SocialFeedback",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        unique_constraint="uq_user_work_feedback",
        notes="Feedback is reparented; conflicts abort merge",
    )

    # Social note relationships
    inventory.add_relationship(
        model_class="SocialNote",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Notes are reparented to canonical Work",
    )

    # Escalation request relationships
    inventory.add_relationship(
        model_class="EscalationRequest",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Escalation requests are reparented",
    )

    # Audit log relationships
    inventory.add_relationship(
        model_class="EntityAuditLog",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Audit logs are reparented",
    )

    return inventory


def build_manifestation_relationship_inventory() -> RelationshipInventory:
    """Build complete relationship inventory for Manifestation entity."""
    inventory = RelationshipInventory(entity_type="Manifestation")

    # Core FRBR relationships
    inventory.add_relationship(
        model_class="Item",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Items are reparented to canonical Manifestation",
    )

    # Image scan relationships
    inventory.add_relationship(
        model_class="ImageScan",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Image scans are reparented to canonical Manifestation",
    )

    # Contribution relationships
    inventory.add_relationship(
        model_class="ManifestationContribution",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Contributions are reparented to canonical Manifestation",
    )

    # Item status log relationships
    inventory.add_relationship(
        model_class="ItemStatusLog",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Status logs are reparented",
    )

    # Item tag relationships (via Item)
    inventory.add_relationship(
        model_class="ItemTag",
        fk_column="item_id",
        policy=ReparentPolicy.REPARENT,
        notes="Item tags follow Item reparenting",
    )

    # Social feedback relationships
    inventory.add_relationship(
        model_class="SocialFeedback",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        unique_constraint="uq_user_manifestation_feedback",
        notes="Feedback is reparented; conflicts abort merge",
    )

    # Social note relationships
    inventory.add_relationship(
        model_class="SocialNote",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Notes are reparented to canonical Manifestation",
    )

    # Escalation request relationships
    inventory.add_relationship(
        model_class="EscalationRequest",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Escalation requests are reparented",
    )

    # Metadata reparenting
    inventory.add_relationship(
        model_class="Manifestation",
        fk_column="meta",
        policy=ReparentPolicy.MERGE_METADATA,
        notes="JSON metadata is merged from duplicate to canonical",
    )

    return inventory


def isbn10_to_isbn13(isbn10: str) -> str | None:
    """Convert a valid 10-digit ISBN into a standard 13-digit EAN-13 ISBN.

    :param isbn10: Raw or formatted 10-digit ISBN string
    :return: Normalized 13-digit ISBN string or None if invalid
    """
    cleaned = ISBN_CLEAN_PATTERN.sub("", isbn10.upper())
    if len(cleaned) != 10:
        return None

    # Validate 10-digit checksum
    if not (cleaned[:9].isdigit() and (cleaned[9].isdigit() or cleaned[9] == "X")):
        return None
    total10 = sum((10 - idx) * (10 if char == "X" else int(char)) for idx, char in enumerate(cleaned))
    if total10 % 11 != 0:
        return None

    # Construct 13-digit prefix (978 + first 9 digits)
    core = f"978{cleaned[:9]}"
    total13 = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(core))
    check13 = (10 - (total13 % 10)) % 10
    return f"{core}{check13}"


def normalize_to_isbn13(raw_isbn: str) -> str | None:
    """Normalize any ISBN (10-digit or 13-digit) to a canonical 13-digit string.

    :param raw_isbn: Raw ISBN string containing possible hyphens or spaces
    :return: Normalized 13-digit ISBN or None if invalid
    """
    cleaned = ISBN_CLEAN_PATTERN.sub("", raw_isbn.upper())
    if len(cleaned) == 10:
        return isbn10_to_isbn13(cleaned)
    if len(cleaned) == 13 and cleaned.isdigit():
        total = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(cleaned[:12]))
        expected_check = (10 - (total % 10)) % 10
        if int(cleaned[12]) == expected_check:
            return cleaned
    return None


# Alias for cleaner API
normalize_isbn = normalize_to_isbn13


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
            "works": [
                {"id": w.id, "title": w.title, "meta": w.meta, "raw_payload": w.raw_payload}
                for w in works
            ],
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
    except Exception as exc:
        raise RuntimeError(f"Failed to write backup snapshot to {backup_file}: {exc}") from exc

    # Verify backup exists and is readable
    if not backup_file.exists() or backup_file.stat().st_size == 0:
        raise RuntimeError(f"Backup verification failed: file {backup_file} is missing or empty")

    # Verify backup can be loaded
    try:
        loaded = json.loads(backup_file.read_text(encoding="utf-8"))
        if "coverage" not in loaded or "entities" not in loaded:
            raise RuntimeError("Backup verification failed: missing required sections")
    except Exception as exc:
        raise RuntimeError(f"Backup verification failed: cannot parse backup: {exc}") from exc

    return backup_file


def verify_backup_coverage(backup_file: Path) -> dict[str, Any]:
    """Verify that a backup file has complete coverage.

    :param backup_file: Path to the backup file
    :return: Verification result with coverage details
    """
    try:
        data = json.loads(backup_file.read_text(encoding="utf-8"))
    except Exception as exc:
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


def generate_work_merge_plan(canonical_work: Work, duplicate_work: Work) -> MergePlan:
    """Generate a complete merge plan for duplicate Works.

    :param canonical_work: The Work to keep
    :param duplicate_work: The Work to merge into canonical
    :return: Complete merge plan with all operations
    """
    plan = MergePlan(
        entity_type="Work",
        canonical_id=canonical_work.id,
        duplicate_id=duplicate_work.id,
    )

    # Check for Expression reparenting
    dup_expressions = db.session.execute(
        select(Expression).where(Expression.work_id == duplicate_work.id)
    ).scalars().all()
    if dup_expressions:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="Expression",
                record_count=len(dup_expressions),
            )
        )

    # Check for WorkContribution reparenting
    dup_contributions = db.session.execute(
        select(WorkContribution).where(WorkContribution.work_id == duplicate_work.id)
    ).scalars().all()
    if dup_contributions:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="WorkContribution",
                record_count=len(dup_contributions),
            )
        )

    # Check for WorkPart reparenting (as container)
    dup_parts_container = db.session.execute(
        select(WorkPart).where(WorkPart.container_work_id == duplicate_work.id)
    ).scalars().all()
    if dup_parts_container:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="WorkPart.container",
                record_count=len(dup_parts_container),
            )
        )

    # Check for WorkPart reparenting (as part)
    dup_parts_member = db.session.execute(
        select(WorkPart).where(WorkPart.part_work_id == duplicate_work.id)
    ).scalars().all()
    if dup_parts_member:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="WorkPart.member",
                record_count=len(dup_parts_member),
            )
        )

    # Check for WorkExpansionLink reparenting
    dup_expansions = db.session.execute(
        select(WorkExpansionLink).where(
            (WorkExpansionLink.base_work_id == duplicate_work.id)
            | (WorkExpansionLink.expansion_work_id == duplicate_work.id)
        )
    ).scalars().all()
    if dup_expansions:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="WorkExpansionLink",
                record_count=len(dup_expansions),
            )
        )

    # Check for UserWorkIntent conflicts
    dup_intents = db.session.execute(
        select(UserWorkIntent).where(UserWorkIntent.work_id == duplicate_work.id)
    ).scalars().all()
    for intent in dup_intents:
        # Check if canonical already has intent from same user
        existing = db.session.execute(
            select(UserWorkIntent).where(
                UserWorkIntent.work_id == canonical_work.id,
                UserWorkIntent.user_id == intent.user_id,
            )
        ).scalars().first()
        if existing:
            plan.add_conflict(
                f"UserWorkIntent conflict: user {intent.user_id} has intent on both works"
            )
        else:
            plan.add_operation(
                MergeOperation(
                    operation_type="reparent",
                    source_id=duplicate_work.id,
                    target_id=canonical_work.id,
                    model_class="UserWorkIntent",
                    record_count=1,
                )
            )

    # Check for SocialFeedback conflicts
    dup_feedback = db.session.execute(
        select(SocialFeedback).where(SocialFeedback.work_id == duplicate_work.id)
    ).scalars().all()
    for feedback in dup_feedback:
        # Check if canonical already has feedback from same user
        existing = db.session.execute(
            select(SocialFeedback).where(
                SocialFeedback.work_id == canonical_work.id,
                SocialFeedback.user_id == feedback.user_id,
            )
        ).scalars().first()
        if existing:
            plan.add_conflict(
                f"SocialFeedback conflict: user {feedback.user_id} has feedback on both works"
            )
        else:
            plan.add_operation(
                MergeOperation(
                    operation_type="reparent",
                    source_id=duplicate_work.id,
                    target_id=canonical_work.id,
                    model_class="SocialFeedback",
                    record_count=1,
                )
            )

    # Check for SocialNote reparenting
    dup_notes = db.session.execute(
        select(SocialNote).where(SocialNote.work_id == duplicate_work.id)
    ).scalars().all()
    if dup_notes:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="SocialNote",
                record_count=len(dup_notes),
            )
        )

    # Check for EscalationRequest reparenting
    dup_escalations = db.session.execute(
        select(EscalationRequest).where(EscalationRequest.work_id == duplicate_work.id)
    ).scalars().all()
    if dup_escalations:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="EscalationRequest",
                record_count=len(dup_escalations),
            )
        )

    # Check for EntityAuditLog reparenting
    dup_audit_logs = db.session.execute(
        select(EntityAuditLog).where(
            EntityAuditLog.entity_type == "Work",
            EntityAuditLog.entity_id == duplicate_work.id,
        )
    ).scalars().all()
    if dup_audit_logs:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="EntityAuditLog",
                record_count=len(dup_audit_logs),
            )
        )

    # Metadata merge
    if duplicate_work.meta and isinstance(duplicate_work.meta, dict):
        plan.add_operation(
            MergeOperation(
                operation_type="merge_metadata",
                source_id=duplicate_work.id,
                target_id=canonical_work.id,
                model_class="Work",
                record_count=1,
            )
        )

    # Final deletion
    plan.add_operation(
        MergeOperation(
            operation_type="delete",
            source_id=duplicate_work.id,
            target_id=canonical_work.id,
            model_class="Work",
            record_count=1,
        )
    )

    return plan


def generate_manifestation_merge_plan(
    canonical_manif: Manifestation, duplicate_manif: Manifestation
) -> MergePlan:
    """Generate a complete merge plan for duplicate Manifestations.

    :param canonical_manif: The Manifestation to keep
    :param duplicate_manif: The Manifestation to merge into canonical
    :return: Complete merge plan with all operations
    """
    plan = MergePlan(
        entity_type="Manifestation",
        canonical_id=canonical_manif.id,
        duplicate_id=duplicate_manif.id,
    )

    # Check for Item reparenting
    dup_items = db.session.execute(
        select(Item).where(Item.manifestation_id == duplicate_manif.id)
    ).scalars().all()
    if dup_items:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_manif.id,
                target_id=canonical_manif.id,
                model_class="Item",
                record_count=len(dup_items),
            )
        )

    # Check for ImageScan reparenting
    dup_scans = db.session.execute(
        select(ImageScan).where(ImageScan.manifestation_id == duplicate_manif.id)
    ).scalars().all()
    if dup_scans:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_manif.id,
                target_id=canonical_manif.id,
                model_class="ImageScan",
                record_count=len(dup_scans),
            )
        )

    # Check for ManifestationContribution reparenting
    dup_contributions = db.session.execute(
        select(ManifestationContribution).where(
            ManifestationContribution.manifestation_id == duplicate_manif.id
        )
    ).scalars().all()
    if dup_contributions:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_manif.id,
                target_id=canonical_manif.id,
                model_class="ManifestationContribution",
                record_count=len(dup_contributions),
            )
        )

    # Check for ItemStatusLog reparenting (via Item)
    dup_items = db.session.execute(
        select(Item).where(Item.manifestation_id == duplicate_manif.id)
    ).scalars().all()
    dup_item_ids = [item.id for item in dup_items]
    if dup_item_ids:
        dup_status_logs = db.session.execute(
            select(ItemStatusLog).where(ItemStatusLog.item_id.in_(dup_item_ids))
        ).scalars().all()
        if dup_status_logs:
            plan.add_operation(
                MergeOperation(
                    operation_type="reparent",
                    source_id=duplicate_manif.id,
                    target_id=canonical_manif.id,
                    model_class="ItemStatusLog",
                    record_count=len(dup_status_logs),
                )
            )

    # Check for SocialFeedback conflicts
    dup_feedback = db.session.execute(
        select(SocialFeedback).where(SocialFeedback.manifestation_id == duplicate_manif.id)
    ).scalars().all()
    for feedback in dup_feedback:
        # Check if canonical already has feedback from same user
        existing = db.session.execute(
            select(SocialFeedback).where(
                SocialFeedback.manifestation_id == canonical_manif.id,
                SocialFeedback.user_id == feedback.user_id,
            )
        ).scalars().first()
        if existing:
            plan.add_conflict(
                f"SocialFeedback conflict: user {feedback.user_id} has feedback on both manifestations"
            )
        else:
            plan.add_operation(
                MergeOperation(
                    operation_type="reparent",
                    source_id=duplicate_manif.id,
                    target_id=canonical_manif.id,
                    model_class="SocialFeedback",
                    record_count=1,
                )
            )

    # Check for SocialNote reparenting
    dup_notes = db.session.execute(
        select(SocialNote).where(SocialNote.manifestation_id == duplicate_manif.id)
    ).scalars().all()
    if dup_notes:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_manif.id,
                target_id=canonical_manif.id,
                model_class="SocialNote",
                record_count=len(dup_notes),
            )
        )

    # Check for EscalationRequest reparenting
    dup_escalations = db.session.execute(
        select(EscalationRequest).where(
            EscalationRequest.manifestation_id == duplicate_manif.id
        )
    ).scalars().all()
    if dup_escalations:
        plan.add_operation(
            MergeOperation(
                operation_type="reparent",
                source_id=duplicate_manif.id,
                target_id=canonical_manif.id,
                model_class="EscalationRequest",
                record_count=len(dup_escalations),
            )
        )

    # Metadata merge
    if duplicate_manif.meta and isinstance(duplicate_manif.meta, dict):
        plan.add_operation(
            MergeOperation(
                operation_type="merge_metadata",
                source_id=duplicate_manif.id,
                target_id=canonical_manif.id,
                model_class="Manifestation",
                record_count=1,
            )
        )

    # Final deletion
    plan.add_operation(
        MergeOperation(
            operation_type="delete",
            source_id=duplicate_manif.id,
            target_id=canonical_manif.id,
            model_class="Manifestation",
            record_count=1,
        )
    )

    return plan


def apply_work_merge_plan(plan: MergePlan, dry_run: bool = False) -> dict[str, int]:
    """Apply a Work merge plan transactionally.

    :param plan: The merge plan to apply
    :param dry_run: If True, simulate without committing
    :return: Statistics dictionary
    """
    stats = {
        "reparented_expressions": 0,
        "reparented_contributions": 0,
        "reparented_work_parts": 0,
        "reparented_expansions": 0,
        "reparented_intents": 0,
        "reparented_feedback": 0,
        "reparented_notes": 0,
        "reparented_escalations": 0,
        "reparented_audit_logs": 0,
        "merged_metadata": 0,
        "deleted_works": 0,
    }

    if plan.has_conflicts():
        if not dry_run:
            raise RuntimeError(f"Cannot apply merge plan with conflicts: {plan.conflicts}")
        return stats

    canonical_work = db.session.get(Work, plan.canonical_id)
    duplicate_work = db.session.get(Work, plan.duplicate_id)

    if not canonical_work or not duplicate_work:
        raise RuntimeError(f"Work {plan.canonical_id} or {plan.duplicate_id} not found")

    for operation in plan.operations:
        if operation.operation_type == "reparent":
            if operation.model_class == "Expression":
                db.session.execute(
                    text("UPDATE " + _CATALOG_PFX + "expressions SET work_id = :target WHERE work_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_expressions"] += operation.record_count
            elif operation.model_class == "WorkContribution":
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "work_contributions SET work_id = :target WHERE work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_contributions"] += operation.record_count
            elif operation.model_class == "WorkPart.container":
                # Use raw SQL to update WorkPart records where this Work is the container
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "work_parts SET container_work_id = :target WHERE container_work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_work_parts"] += operation.record_count
            elif operation.model_class == "WorkPart.member":
                # Use raw SQL to update WorkPart records where this Work is a member
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "work_parts SET part_work_id = :target WHERE part_work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_work_parts"] += operation.record_count
            elif operation.model_class == "WorkExpansionLink":
                # Use raw SQL to update WorkExpansionLink records
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "work_expansion_links SET base_work_id = :target WHERE base_work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "work_expansion_links SET expansion_work_id = :target WHERE expansion_work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_expansions"] += operation.record_count
            elif operation.model_class == "UserWorkIntent":
                db.session.execute(
                    text(
                        "UPDATE " + _INVENTORY_PFX + "user_work_intents SET work_id = :target WHERE work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_intents"] += operation.record_count
            elif operation.model_class == "SocialFeedback":
                db.session.execute(
                    text(
                        "UPDATE " + _SOCIAL_PFX + "social_feedbacks SET work_id = :target WHERE work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_feedback"] += operation.record_count
            elif operation.model_class == "SocialNote":
                db.session.execute(
                    text("UPDATE " + _SOCIAL_PFX + "social_notes SET work_id = :target WHERE work_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_notes"] += operation.record_count
            elif operation.model_class == "EscalationRequest":
                db.session.execute(
                    text(
                        "UPDATE " + _SOCIAL_PFX + "escalation_requests SET work_id = :target WHERE work_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_escalations"] += operation.record_count
            elif operation.model_class == "EntityAuditLog":
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "entity_audit_logs SET entity_id = :target WHERE entity_type = 'Work' AND entity_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_audit_logs"] += operation.record_count
        elif operation.operation_type == "merge_metadata":
            if duplicate_work.meta and isinstance(duplicate_work.meta, dict):
                canon_meta = dict(canonical_work.meta or {})
                for k, v in duplicate_work.meta.items():
                    if k not in canon_meta:
                        canon_meta[k] = v
                canonical_work.meta = canon_meta
                flag_modified(canonical_work, "meta")
                stats["merged_metadata"] += 1
        elif operation.operation_type == "delete":
            # Use raw SQL to delete the duplicate Work to avoid ORM cascade issues
            db.session.execute(
                text("DELETE FROM " + _CATALOG_PFX + "works WHERE id = :source"),
                {"source": plan.duplicate_id},
            )
            stats["deleted_works"] += 1

    if not dry_run:
        db.session.flush()

    return stats


def apply_manifestation_merge_plan(
    plan: MergePlan, dry_run: bool = False
) -> dict[str, int]:
    """Apply a Manifestation merge plan transactionally.

    :param plan: The merge plan to apply
    :param dry_run: If True, simulate without committing
    :return: Statistics dictionary
    """
    stats = {
        "reparented_items": 0,
        "reparented_scans": 0,
        "reparented_contributions": 0,
        "reparented_status_logs": 0,
        "reparented_feedback": 0,
        "reparented_notes": 0,
        "reparented_escalations": 0,
        "merged_metadata": 0,
        "deleted_manifestations": 0,
    }

    if plan.has_conflicts():
        if not dry_run:
            raise RuntimeError(f"Cannot apply merge plan with conflicts: {plan.conflicts}")
        return stats

    canonical_manif = db.session.get(Manifestation, plan.canonical_id)
    duplicate_manif = db.session.get(Manifestation, plan.duplicate_id)

    if not canonical_manif or not duplicate_manif:
        raise RuntimeError(f"Manifestation {plan.canonical_id} or {plan.duplicate_id} not found")

    for operation in plan.operations:
        if operation.operation_type == "reparent":
            if operation.model_class == "Item":
                db.session.execute(
                    text(
                        "UPDATE " + _INVENTORY_PFX + "items SET manifestation_id = :target WHERE manifestation_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_items"] += operation.record_count
            elif operation.model_class == "ImageScan":
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "image_scans SET manifestation_id = :target WHERE manifestation_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_scans"] += operation.record_count
            elif operation.model_class == "ManifestationContribution":
                db.session.execute(
                    text(
                        "UPDATE " + _CATALOG_PFX + "manifestation_contributions SET manifestation_id = :target WHERE manifestation_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_contributions"] += operation.record_count
            elif operation.model_class == "ItemStatusLog":
                # ItemStatusLog is linked to Item, not Manifestation
                # Since we already reparented Items, the status logs follow automatically
                # No explicit update needed
                pass
            elif operation.model_class == "SocialFeedback":
                db.session.execute(
                    text(
                        "UPDATE " + _SOCIAL_PFX + "social_feedbacks SET manifestation_id = :target WHERE manifestation_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_feedback"] += operation.record_count
            elif operation.model_class == "SocialNote":
                db.session.execute(
                    text(
                        "UPDATE " + _SOCIAL_PFX + "social_notes SET manifestation_id = :target WHERE manifestation_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_notes"] += operation.record_count
            elif operation.model_class == "EscalationRequest":
                db.session.execute(
                    text(
                        "UPDATE " + _SOCIAL_PFX + "escalation_requests SET manifestation_id = :target WHERE manifestation_id = :source"
                    ),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_escalations"] += operation.record_count
        elif operation.operation_type == "merge_metadata":
            if duplicate_manif.meta and isinstance(duplicate_manif.meta, dict):
                canon_meta = dict(canonical_manif.meta or {})
                for k, v in duplicate_manif.meta.items():
                    if k not in canon_meta:
                        canon_meta[k] = v
                canonical_manif.meta = canon_meta
                flag_modified(canonical_manif, "meta")
                stats["merged_metadata"] += 1
        elif operation.operation_type == "delete":
            db.session.delete(duplicate_manif)
            stats["deleted_manifestations"] += 1

    if not dry_run:
        db.session.flush()

    return stats


def run_safe_etl_pipeline(
    dry_run: bool = False,
    backup_dir: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute the safe FRBR ETL pipeline with complete relationship coverage.

    :param dry_run: If True, generate merge plans without applying them
    :param backup_dir: Directory where backup is created
    :param verbose: If True, print detailed operational output
    :return: Statistics and merge plan summary
    """
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "backup_file": None,
        "backup_verification": None,
        "work_merge_plans": [],
        "manifestation_merge_plans": [],
        "conflicts": [],
        "stats": {
            "reconciled_works": 0,
            "reconciled_manifestations": 0,
            "reparented_expressions": 0,
            "reparented_items": 0,
            "reparented_scans": 0,
            "reparented_contributions": 0,
            "reparented_intents": 0,
            "reparented_feedback": 0,
            "reparented_notes": 0,
            "reparented_escalations": 0,
            "reparented_audit_logs": 0,
            "reparented_status_logs": 0,
            "merged_metadata": 0,
            "normalized_isbns": 0,
            "relocated_work_isbns": 0,
        },
    }

    # Step 0: Create and verify complete backup
    if not dry_run:
        b_dir = backup_dir or Path("exports/backups")
        try:
            backup_path = create_complete_backup(b_dir)
            result["backup_file"] = str(backup_path)

            # Verify backup coverage
            verification = verify_backup_coverage(backup_path)
            result["backup_verification"] = verification

            if not verification["valid"]:
                raise RuntimeError(f"Backup verification failed: {verification['error']}")

            if verbose:
                print(f"[BACKUP] Complete snapshot created at: {backup_path}")
                print(f"[BACKUP] Coverage verified: {verification['counts']}")
        except Exception as exc:
            raise RuntimeError(f"Backup creation/verification failed: {exc}") from exc

    # Step 1: Normalize ISBNs and relocate Work-level ISBNs
    works = db.session.execute(select(Work)).scalars().all()
    for work in works:
        if not work.meta or not isinstance(work.meta, dict):
            continue

        work_meta = dict(work.meta)
        misplaced_isbn = None
        for key in ("isbn", "isbn13", "ISBN", "ISBN13"):
            if key in work_meta and work_meta[key]:
                misplaced_isbn = str(work_meta[key]).strip()
                del work_meta[key]

        if misplaced_isbn:
            normalized = normalize_to_isbn13(misplaced_isbn)
            work.meta = work_meta
            flag_modified(work, "meta")
            result["stats"]["relocated_work_isbns"] += 1

            if normalized:
                existing_manif = db.session.execute(
                    select(Manifestation).where(Manifestation.isbn13 == normalized)
                ).scalars().first()
                if not existing_manif:
                    child_exprs = db.session.execute(
                        select(Expression).where(Expression.work_id == work.id)
                    ).scalars().all()
                    assigned = False
                    for expr in child_exprs:
                        if assigned:
                            break
                        child_manifs = db.session.execute(
                            select(Manifestation).where(Manifestation.expression_id == expr.id)
                        ).scalars().all()
                        for manif in child_manifs:
                            if not manif.isbn13:
                                manif.isbn13 = normalized
                                assigned = True
                                result["stats"]["normalized_isbns"] += 1
                                if verbose:
                                    print(f"[NORMALIZE] Assigned ISBN {normalized} to Manifestation {manif.id}")
                                break

    if not dry_run:
        db.session.flush()

    # Step 2: Deduplicate Manifestations
    all_manifs = db.session.execute(select(Manifestation)).scalars().all()
    isbn_groups: dict[str, list[tuple[Manifestation, str]]] = defaultdict(list)
    for m in all_manifs:
        if m.isbn13:
            norm_isbn = normalize_to_isbn13(m.isbn13) or ISBN_CLEAN_PATTERN.sub("", m.isbn13.upper())
            if norm_isbn:
                isbn_groups[norm_isbn].append((m, norm_isbn))

    for isbn_key, group in isbn_groups.items():
        if len(group) == 1:
            m, target_isbn = group[0]
            if m.isbn13 != target_isbn:
                m.isbn13 = target_isbn
                result["stats"]["normalized_isbns"] += 1
                if verbose:
                    print(f"[NORMALIZE] Manifestation {m.id}: '{m.isbn13}' -> '{target_isbn}'")
            continue

        # Canonical manifestation: select record with highest item count or oldest id
        group_with_counts = []
        for m, target_isbn in group:
            item_count = len(
                db.session.execute(select(Item).where(Item.manifestation_id == m.id)).scalars().all()
            )
            group_with_counts.append((item_count, -m.id, m, target_isbn))
        group_with_counts.sort(reverse=True)

        canonical = group_with_counts[0][2]
        canonical_target = group_with_counts[0][3]
        duplicates = [item[2] for item in group_with_counts[1:]]

        if canonical.isbn13 != canonical_target:
            canonical.isbn13 = canonical_target
            result["stats"]["normalized_isbns"] += 1

        for dup in duplicates:
            # Generate merge plan
            plan = generate_manifestation_merge_plan(canonical, dup)
            result["manifestation_merge_plans"].append(
                {
                    "canonical_id": plan.canonical_id,
                    "duplicate_id": plan.duplicate_id,
                    "operations": len(plan.operations),
                    "conflicts": plan.conflicts,
                }
            )
            result["conflicts"].extend(plan.conflicts)

            if plan.has_conflicts():
                if verbose:
                    print(f"[CONFLICT] Manifestation merge {dup.id} -> {canonical.id}: {plan.conflicts}")
                continue

            if dry_run:
                if verbose:
                    print(f"[DRY RUN] Would merge Manifestation {dup.id} into {canonical.id}")
            else:
                # Apply merge plan
                try:
                    stats = apply_manifestation_merge_plan(plan, dry_run=False)
                    for key, value in stats.items():
                        result["stats"][key] = result["stats"].get(key, 0) + value
                    result["stats"]["reconciled_manifestations"] += 1
                    if verbose:
                        print(f"[MERGE] Manifestation {dup.id} merged into {canonical.id}")
                except Exception as exc:
                    db.session.rollback()
                    raise RuntimeError(f"Manifestation merge failed: {exc}") from exc

    if not dry_run:
        db.session.flush()

    # Step 3: Deduplicate Works
    all_works = db.session.execute(select(Work)).scalars().all()
    work_groups: dict[str, list[Work]] = defaultdict(list)
    for w in all_works:
        authors: list[str] = []
        if w.meta and isinstance(w.meta, dict):
            raw_authors = w.meta.get("authors") or w.meta.get("Authors") or []
            if isinstance(raw_authors, list):
                authors = sorted(str(a).strip().lower() for a in raw_authors if str(a).strip())
        norm_title = (w.title or "").strip().lower()
        key = f"{norm_title}||{'|'.join(authors)}"
        work_groups[key].append(w)

    for cluster_key, w_group in work_groups.items():
        if len(w_group) <= 1 or not cluster_key.strip("|"):
            continue

        # Canonical work: select oldest id
        w_group.sort(key=lambda item: item.id)
        canonical_work = w_group[0]
        duplicate_works = w_group[1:]

        for dup_work in duplicate_works:
            # Generate merge plan
            plan = generate_work_merge_plan(canonical_work, dup_work)
            result["work_merge_plans"].append(
                {
                    "canonical_id": plan.canonical_id,
                    "duplicate_id": plan.duplicate_id,
                    "operations": len(plan.operations),
                    "conflicts": plan.conflicts,
                }
            )
            result["conflicts"].extend(plan.conflicts)

            if plan.has_conflicts():
                if verbose:
                    print(f"[CONFLICT] Work merge {dup_work.id} -> {canonical_work.id}: {plan.conflicts}")
                continue

            if dry_run:
                if verbose:
                    print(f"[DRY RUN] Would merge Work {dup_work.id} into {canonical_work.id}")
            else:
                # Apply merge plan
                try:
                    stats = apply_work_merge_plan(plan, dry_run=False)
                    for key, value in stats.items():
                        result["stats"][key] = result["stats"].get(key, 0) + value
                    result["stats"]["reconciled_works"] += 1
                    if verbose:
                        print(f"[MERGE] Work {dup_work.id} merged into {canonical_work.id}")
                except Exception as exc:
                    db.session.rollback()
                    raise RuntimeError(f"Work merge failed: {exc}") from exc

    if dry_run:
        db.session.rollback()
        if verbose:
            print("\n[DRY RUN] Simulation complete. No database modifications were committed.")
    else:
        db.session.commit()
        if verbose:
            print("\n[LIVE] ETL transaction committed successfully.")

    return result


def main() -> None:
    """CLI entrypoint for safe FRBR ETL operations."""
    parser = argparse.ArgumentParser(description="Safe FRBR Database ETL with Complete Relationship Coverage.")
    parser.add_argument("--dry-run", action="store_true", help="Generate merge plans without applying them.")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("exports/backups"),
        help="Directory for backup snapshots.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed operation steps.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        result = run_safe_etl_pipeline(
            dry_run=args.dry_run,
            backup_dir=args.backup_dir,
            verbose=args.verbose,
        )

    print("=" * 64)
    print("SAFE FRBR ETL EXECUTION SUMMARY" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 64)
    print(f"Reconciled Works:                  {result['stats']['reconciled_works']}")
    print(f"Reconciled Manifestations:         {result['stats']['reconciled_manifestations']}")
    print(f"Reparented Expressions:            {result['stats']['reparented_expressions']}")
    print(f"Reparented Items:                  {result['stats']['reparented_items']}")
    print(f"Reparented Image Scans:            {result['stats']['reparented_scans']}")
    print(f"Reparented Contributions:          {result['stats']['reparented_contributions']}")
    print(f"Reparented User Intents:           {result['stats']['reparented_intents']}")
    print(f"Reparented Social Feedback:        {result['stats']['reparented_feedback']}")
    print(f"Reparented Social Notes:           {result['stats']['reparented_notes']}")
    print(f"Reparented Escalation Requests:    {result['stats']['reparented_escalations']}")
    print(f"Reparented Audit Logs:             {result['stats']['reparented_audit_logs']}")
    print(f"Reparented Status Logs:            {result['stats']['reparented_status_logs']}")
    print(f"Merged Metadata:                   {result['stats']['merged_metadata']}")
    print(f"Normalized ISBNs:                  {result['stats']['normalized_isbns']}")
    print(f"Relocated Work ISBNs:              {result['stats']['relocated_work_isbns']}")
    print(f"Conflicts Detected:                {len(result['conflicts'])}")
    if result["backup_file"]:
        print(f"Backup File:                       {result['backup_file']}")
    print("=" * 64)

    if result["conflicts"]:
        print("\nConflicts:")
        for conflict in result["conflicts"]:
            print(f"  - {conflict}")


if __name__ == "__main__":
    main()
