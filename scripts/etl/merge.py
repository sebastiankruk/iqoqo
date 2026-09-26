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
"""FRBR merge plan generation and transactional application.

Defines MergeOperation, MergePlan, dry-run plan generators for Work and
Manifestation entities, and transactional execution logic.
"""

from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.orm.attributes import flag_modified

from app.db import db
from app.db.contributions import (
    ManifestationContribution,
    WorkContribution,
    WorkPart,
)
from app.db.core import (
    _CATALOG_PFX,
    _INVENTORY_PFX,
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
    _SOCIAL_PFX,
    EscalationRequest,
    SocialFeedback,
    SocialNote,
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
    dup_expressions = db.session.execute(select(Expression).where(Expression.work_id == duplicate_work.id)).scalars().all()
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
    dup_contributions = db.session.execute(select(WorkContribution).where(WorkContribution.work_id == duplicate_work.id)).scalars().all()
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
    dup_parts_container = db.session.execute(select(WorkPart).where(WorkPart.container_work_id == duplicate_work.id)).scalars().all()
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
    dup_parts_member = db.session.execute(select(WorkPart).where(WorkPart.part_work_id == duplicate_work.id)).scalars().all()
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
    dup_expansions = (
        db.session.execute(
            select(WorkExpansionLink).where(
                (WorkExpansionLink.base_work_id == duplicate_work.id) | (WorkExpansionLink.expansion_work_id == duplicate_work.id)
            )
        )
        .scalars()
        .all()
    )
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
    dup_intents = db.session.execute(select(UserWorkIntent).where(UserWorkIntent.work_id == duplicate_work.id)).scalars().all()
    for intent in dup_intents:
        # Check if canonical already has intent from same user
        existing = (
            db.session.execute(
                select(UserWorkIntent).where(
                    UserWorkIntent.work_id == canonical_work.id,
                    UserWorkIntent.user_id == intent.user_id,
                )
            )
            .scalars()
            .first()
        )
        if existing:
            plan.add_conflict(f"UserWorkIntent conflict: user {intent.user_id} has intent on both works")
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
    dup_feedback = db.session.execute(select(SocialFeedback).where(SocialFeedback.work_id == duplicate_work.id)).scalars().all()
    for feedback in dup_feedback:
        # Check if canonical already has feedback from same user
        existing = (
            db.session.execute(
                select(SocialFeedback).where(
                    SocialFeedback.work_id == canonical_work.id,
                    SocialFeedback.user_id == feedback.user_id,
                )
            )
            .scalars()
            .first()
        )
        if existing:
            plan.add_conflict(f"SocialFeedback conflict: user {feedback.user_id} has feedback on both works")
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
    dup_notes = db.session.execute(select(SocialNote).where(SocialNote.work_id == duplicate_work.id)).scalars().all()
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
    dup_escalations = db.session.execute(select(EscalationRequest).where(EscalationRequest.work_id == duplicate_work.id)).scalars().all()
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
    dup_audit_logs = (
        db.session.execute(
            select(EntityAuditLog).where(
                EntityAuditLog.entity_type == "Work",
                EntityAuditLog.entity_id == duplicate_work.id,
            )
        )
        .scalars()
        .all()
    )
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


def generate_manifestation_merge_plan(canonical_manif: Manifestation, duplicate_manif: Manifestation) -> MergePlan:
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
    dup_items = db.session.execute(select(Item).where(Item.manifestation_id == duplicate_manif.id)).scalars().all()
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
    dup_scans = db.session.execute(select(ImageScan).where(ImageScan.manifestation_id == duplicate_manif.id)).scalars().all()
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
    dup_contributions = (
        db.session.execute(select(ManifestationContribution).where(ManifestationContribution.manifestation_id == duplicate_manif.id))
        .scalars()
        .all()
    )
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
    dup_items = db.session.execute(select(Item).where(Item.manifestation_id == duplicate_manif.id)).scalars().all()
    dup_item_ids = [item.id for item in dup_items]
    if dup_item_ids:
        dup_status_logs = db.session.execute(select(ItemStatusLog).where(ItemStatusLog.item_id.in_(dup_item_ids))).scalars().all()
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
    dup_feedback = db.session.execute(select(SocialFeedback).where(SocialFeedback.manifestation_id == duplicate_manif.id)).scalars().all()
    for feedback in dup_feedback:
        # Check if canonical already has feedback from same user
        existing = (
            db.session.execute(
                select(SocialFeedback).where(
                    SocialFeedback.manifestation_id == canonical_manif.id,
                    SocialFeedback.user_id == feedback.user_id,
                )
            )
            .scalars()
            .first()
        )
        if existing:
            plan.add_conflict(f"SocialFeedback conflict: user {feedback.user_id} has feedback on both manifestations")
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
    dup_notes = db.session.execute(select(SocialNote).where(SocialNote.manifestation_id == duplicate_manif.id)).scalars().all()
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
    dup_escalations = (
        db.session.execute(select(EscalationRequest).where(EscalationRequest.manifestation_id == duplicate_manif.id)).scalars().all()
    )
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
                    text("UPDATE " + _CATALOG_PFX + "work_contributions SET work_id = :target WHERE work_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_contributions"] += operation.record_count
            elif operation.model_class == "WorkPart.container":
                # Use raw SQL to update WorkPart records where this Work is the container
                db.session.execute(
                    text("UPDATE " + _CATALOG_PFX + "work_parts SET container_work_id = :target WHERE container_work_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_work_parts"] += operation.record_count
            elif operation.model_class == "WorkPart.member":
                # Use raw SQL to update WorkPart records where this Work is a member
                db.session.execute(
                    text("UPDATE " + _CATALOG_PFX + "work_parts SET part_work_id = :target WHERE part_work_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_work_parts"] += operation.record_count
            elif operation.model_class == "WorkExpansionLink":
                # Use raw SQL to update WorkExpansionLink records
                db.session.execute(
                    text("UPDATE " + _CATALOG_PFX + "work_expansion_links SET base_work_id = :target WHERE base_work_id = :source"),
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
                    text("UPDATE " + _INVENTORY_PFX + "user_work_intents SET work_id = :target WHERE work_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_intents"] += operation.record_count
            elif operation.model_class == "SocialFeedback":
                db.session.execute(
                    text("UPDATE " + _SOCIAL_PFX + "social_feedbacks SET work_id = :target WHERE work_id = :source"),
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
                    text("UPDATE " + _SOCIAL_PFX + "escalation_requests SET work_id = :target WHERE work_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_escalations"] += operation.record_count
            elif operation.model_class == "EntityAuditLog":
                db.session.execute(
                    text(
                        "UPDATE "
                        + _CATALOG_PFX
                        + "entity_audit_logs SET entity_id = :target WHERE entity_type = 'Work' AND entity_id = :source"
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


def apply_manifestation_merge_plan(plan: MergePlan, dry_run: bool = False) -> dict[str, int]:
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
                    text("UPDATE " + _INVENTORY_PFX + "items SET manifestation_id = :target WHERE manifestation_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_items"] += operation.record_count
            elif operation.model_class == "ImageScan":
                db.session.execute(
                    text("UPDATE " + _CATALOG_PFX + "image_scans SET manifestation_id = :target WHERE manifestation_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_scans"] += operation.record_count
            elif operation.model_class == "ManifestationContribution":
                db.session.execute(
                    text(
                        "UPDATE "
                        + _CATALOG_PFX
                        + "manifestation_contributions SET manifestation_id = :target WHERE manifestation_id = :source"
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
                    text("UPDATE " + _SOCIAL_PFX + "social_feedbacks SET manifestation_id = :target WHERE manifestation_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_feedback"] += operation.record_count
            elif operation.model_class == "SocialNote":
                db.session.execute(
                    text("UPDATE " + _SOCIAL_PFX + "social_notes SET manifestation_id = :target WHERE manifestation_id = :source"),
                    {"target": plan.canonical_id, "source": plan.duplicate_id},
                )
                stats["reparented_notes"] += operation.record_count
            elif operation.model_class == "EscalationRequest":
                db.session.execute(
                    text("UPDATE " + _SOCIAL_PFX + "escalation_requests SET manifestation_id = :target WHERE manifestation_id = :source"),
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
