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
"""Comprehensive tests for safe FRBR ETL with complete relationship coverage."""

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import db
from app.db.contributions import ManifestationContribution, WorkContribution, WorkPart
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
from app.db.models import Contributor, User
from app.db.social import EscalationRequest, SocialFeedback, SocialNote
from scripts.etl_frbr_safe import (
    build_manifestation_relationship_inventory,
    build_work_relationship_inventory,
    create_complete_backup,
    generate_manifestation_merge_plan,
    generate_work_merge_plan,
    run_safe_etl_pipeline,
    verify_backup_coverage,
)


@pytest.fixture
def comprehensive_work_fixture(app):
    """Create a comprehensive Work fixture with all dependent relationships."""
    with app.app_context():
        user1 = User(email="user1@iqoqo.local", display_name="User One")
        user2 = User(email="user2@iqoqo.local", display_name="User Two")
        db.session.add_all([user1, user2])
        db.session.flush()

        canonical_work = Work(title="Canonical Work", meta={"authors": ["Author One"]})
        db.session.add(canonical_work)
        db.session.flush()

        duplicate_work = Work(title="Canonical Work", meta={"authors": ["Author One"], "genre": "Fiction"})
        db.session.add(duplicate_work)
        db.session.flush()

        expr1 = Expression(work_id=duplicate_work.id, content_type="text", language="en")
        expr2 = Expression(work_id=duplicate_work.id, content_type="text", language="pl")
        db.session.add_all([expr1, expr2])
        db.session.flush()

        contributor1 = Contributor(name="Contributor One", type="person")
        contributor2 = Contributor(name="Contributor Two", type="person")
        db.session.add_all([contributor1, contributor2])
        db.session.flush()

        contrib1 = WorkContribution(work_id=duplicate_work.id, contributor_id=contributor1.id, role="author", sequence=1)
        contrib2 = WorkContribution(work_id=duplicate_work.id, contributor_id=contributor2.id, role="editor", sequence=2)
        db.session.add_all([contrib1, contrib2])
        db.session.flush()

        container_work = Work(title="Container Work")
        db.session.add(container_work)
        db.session.flush()

        work_part = WorkPart(container_work_id=container_work.id, part_work_id=duplicate_work.id, sequence=1)
        db.session.add(work_part)
        db.session.flush()

        expansion_work = Work(title="Expansion Work")
        db.session.add(expansion_work)
        db.session.flush()

        expansion_link = WorkExpansionLink(base_work_id=duplicate_work.id, expansion_work_id=expansion_work.id)
        db.session.add(expansion_link)
        db.session.flush()

        intent1 = UserWorkIntent(work_id=duplicate_work.id, user_id=user1.id, status="want_to_read")
        db.session.add(intent1)
        db.session.flush()

        feedback1 = SocialFeedback(work_id=duplicate_work.id, user_id=user2.id, rating=5, comment="Great work!")
        db.session.add(feedback1)
        db.session.flush()

        note1 = SocialNote(work_id=duplicate_work.id, user_id=user1.id, note="Important note")
        db.session.add(note1)
        db.session.flush()

        escalation1 = EscalationRequest(
            work_id=duplicate_work.id,
            user_id=user1.id,
            request_type="correction",
            field_name="author",
            suggested_value="Fixed Author",
            note="Fix author name",
        )
        db.session.add(escalation1)
        db.session.flush()

        audit1 = EntityAuditLog(
            entity_type="Work", entity_id=duplicate_work.id, actor_id=user1.id, change_type="create", diff={"title": "Canonical Work"}
        )
        db.session.add(audit1)
        db.session.flush()

        db.session.commit()

        return {
            "user1_id": user1.id,
            "user2_id": user2.id,
            "canonical_work_id": canonical_work.id,
            "duplicate_work_id": duplicate_work.id,
            "expression_ids": [expr1.id, expr2.id],
            "contribution_ids": [contrib1.id, contrib2.id],
            "work_part": work_part,
            "expansion_link": expansion_link,
            "intent_id": intent1.id,
            "feedback_id": feedback1.id,
            "note_id": note1.id,
            "escalation_id": escalation1.id,
            "audit_log_id": audit1.id,
        }


@pytest.fixture
def comprehensive_manifestation_fixture(app):
    """Create a comprehensive Manifestation fixture with all dependent relationships."""
    with app.app_context():
        user = User(email="manifestation_user@iqoqo.local", display_name="Manifestation User")
        db.session.add(user)
        db.session.flush()

        work = Work(title="Test Work")
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text")
        db.session.add(expression)
        db.session.flush()

        canonical_manif = Manifestation(
            expression_id=expression.id, isbn13="9780306406157", publisher="Publisher One", meta={"format": "hardcover"}
        )
        db.session.add(canonical_manif)
        db.session.flush()

        duplicate_manif = Manifestation(
            expression_id=expression.id,
            isbn13="978-0-306-40615-7",
            publisher="Publisher One",
            meta={"format": "paperback", "pages": 300},
        )
        db.session.add(duplicate_manif)
        db.session.flush()

        item1 = Item(owner_id=user.id, manifestation_id=duplicate_manif.id, status="read")
        item2 = Item(owner_id=user.id, manifestation_id=duplicate_manif.id, status="wish_list")
        db.session.add_all([item1, item2])
        db.session.flush()

        scan1 = ImageScan(manifestation_id=duplicate_manif.id, file_path="scans/cover.jpg", scan_type="cover")
        scan2 = ImageScan(manifestation_id=duplicate_manif.id, file_path="scans/back.jpg", scan_type="back")
        db.session.add_all([scan1, scan2])
        db.session.flush()

        contributor = Contributor(name="Publisher Contributor", type="organization")
        db.session.add(contributor)
        db.session.flush()

        manif_contrib = ManifestationContribution(
            manifestation_id=duplicate_manif.id, contributor_id=contributor.id, role="publisher", sequence=1
        )
        db.session.add(manif_contrib)
        db.session.flush()

        status_log = ItemStatusLog(item_id=item1.id, user_id=user.id, old_status=None, new_status="read")
        db.session.add(status_log)
        db.session.flush()

        feedback = SocialFeedback(manifestation_id=duplicate_manif.id, user_id=user.id, rating=4, comment="Good edition")
        db.session.add(feedback)
        db.session.flush()

        note = SocialNote(manifestation_id=duplicate_manif.id, user_id=user.id, note="Important note about this edition")
        db.session.add(note)
        db.session.flush()

        escalation = EscalationRequest(
            manifestation_id=duplicate_manif.id,
            user_id=user.id,
            request_type="correction",
            field_name="publisher",
            suggested_value="Fixed Publisher",
            note="Fix publisher",
        )
        db.session.add(escalation)
        db.session.flush()

        db.session.commit()

        return {
            "user_id": user.id,
            "canonical_manif_id": canonical_manif.id,
            "duplicate_manif_id": duplicate_manif.id,
            "item_ids": [item1.id, item2.id],
            "scan_ids": [scan1.id, scan2.id],
            "contribution_id": manif_contrib.id,
            "status_log_id": status_log.id,
            "feedback_id": feedback.id,
            "note_id": note.id,
            "escalation_id": escalation.id,
        }


class TestRelationshipInventory:
    """Test relationship inventory generation."""

    def test_work_relationship_inventory_complete(self, app):
        """Verify Work relationship inventory covers all dependent relationships."""
        with app.app_context():
            inventory = build_work_relationship_inventory()
            assert inventory.entity_type == "Work"
            assert len(inventory.relationships) >= 10
            relationship_models = [r["model"] for r in inventory.relationships]
            assert "Expression" in relationship_models
            assert "WorkContribution" in relationship_models
            assert "WorkPart" in relationship_models
            assert "WorkExpansionLink" in relationship_models
            assert "UserWorkIntent" in relationship_models
            assert "SocialFeedback" in relationship_models
            assert "SocialNote" in relationship_models
            assert "EscalationRequest" in relationship_models
            assert "EntityAuditLog" in relationship_models

    def test_manifestation_relationship_inventory_complete(self, app):
        """Verify Manifestation relationship inventory covers all dependent relationships."""
        with app.app_context():
            inventory = build_manifestation_relationship_inventory()
            assert inventory.entity_type == "Manifestation"
            assert len(inventory.relationships) >= 8
            relationship_models = [r["model"] for r in inventory.relationships]
            assert "Item" in relationship_models
            assert "ImageScan" in relationship_models
            assert "ManifestationContribution" in relationship_models
            assert "ItemStatusLog" in relationship_models
            assert "SocialFeedback" in relationship_models
            assert "SocialNote" in relationship_models
            assert "EscalationRequest" in relationship_models


class TestCompleteBackup:
    """Test complete backup creation and verification."""

    def test_create_complete_backup(self, app, tmp_path):
        """Verify complete backup covers all affected tables."""
        with app.app_context():
            work = Work(title="Backup Test Work")
            db.session.add(work)
            db.session.flush()
            expression = Expression(work_id=work.id, content_type="text")
            db.session.add(expression)
            db.session.flush()
            manifestation = Manifestation(expression_id=expression.id, isbn13="9780306406157")
            db.session.add(manifestation)
            db.session.flush()
            db.session.commit()

            backup_file = create_complete_backup(tmp_path)
            assert backup_file.exists()
            assert backup_file.stat().st_size > 0

            data = json.loads(backup_file.read_text(encoding="utf-8"))
            assert data["version"] == "2.0"
            assert "coverage" in data
            assert "counts" in data
            assert "entities" in data

    def test_verify_backup_coverage_valid(self, app, tmp_path):
        """Verify backup coverage validation accepts valid backups."""
        with app.app_context():
            backup_file = create_complete_backup(tmp_path)
            verification = verify_backup_coverage(backup_file)
            assert verification["valid"] is True
            assert verification["version"] == "2.0"

    def test_verify_backup_coverage_invalid_version(self, app, tmp_path):
        """Verify backup coverage validation rejects old versions."""
        with app.app_context():
            old_backup = tmp_path / "old_backup.json"
            old_data = {"version": "1.0", "timestamp": "2024-01-01T00:00:00", "counts": {"works": 0}, "entities": {}}
            old_backup.write_text(json.dumps(old_data))
            verification = verify_backup_coverage(old_backup)
            assert verification["valid"] is False
            assert "too old" in verification["error"]


class TestMergePlanGeneration:
    """Test merge plan generation for Works and Manifestations."""

    def test_generate_work_merge_plan_complete(self, app, comprehensive_work_fixture):
        """Verify Work merge plan includes all dependent relationships."""
        with app.app_context():
            fixture = comprehensive_work_fixture
            canonical = db.session.get(Work, fixture["canonical_work_id"])
            duplicate = db.session.get(Work, fixture["duplicate_work_id"])
            plan = generate_work_merge_plan(canonical, duplicate)
            assert plan.entity_type == "Work"
            assert plan.canonical_id == canonical.id
            assert plan.duplicate_id == duplicate.id
            assert len(plan.operations) > 0
            operation_models = [op.model_class for op in plan.operations]
            assert "Expression" in operation_models
            assert "WorkContribution" in operation_models
            assert "UserWorkIntent" in operation_models
            assert "SocialFeedback" in operation_models
            assert "Work" in operation_models

    def test_generate_manifestation_merge_plan_complete(self, app, comprehensive_manifestation_fixture):
        """Verify Manifestation merge plan includes all dependent relationships."""
        with app.app_context():
            fixture = comprehensive_manifestation_fixture
            canonical = db.session.get(Manifestation, fixture["canonical_manif_id"])
            duplicate = db.session.get(Manifestation, fixture["duplicate_manif_id"])
            plan = generate_manifestation_merge_plan(canonical, duplicate)
            assert plan.entity_type == "Manifestation"
            assert plan.canonical_id == canonical.id
            assert plan.duplicate_id == duplicate.id
            assert len(plan.operations) > 0
            operation_models = [op.model_class for op in plan.operations]
            assert "Item" in operation_models
            assert "ImageScan" in operation_models
            assert "ManifestationContribution" in operation_models
            assert "Manifestation" in operation_models

    def test_work_merge_plan_detects_intent_conflicts(self, app):
        """Verify Work merge plan detects UserWorkIntent conflicts."""
        with app.app_context():
            user = User(email="conflict_user@iqoqo.local", display_name="Conflict User")
            db.session.add(user)
            db.session.flush()
            canonical = Work(title="Conflict Work")
            duplicate = Work(title="Conflict Work")
            db.session.add_all([canonical, duplicate])
            db.session.flush()
            intent1 = UserWorkIntent(work_id=canonical.id, user_id=user.id, status="want_to_read")
            intent2 = UserWorkIntent(work_id=duplicate.id, user_id=user.id, status="reading")
            db.session.add_all([intent1, intent2])
            db.session.commit()
            plan = generate_work_merge_plan(canonical, duplicate)
            assert plan.has_conflicts()
            assert any("UserWorkIntent conflict" in c for c in plan.conflicts)


class TestDryRunIsolation:
    """Test dry-run mode ensures no database writes."""

    def test_dry_run_no_database_writes(self, app, comprehensive_work_fixture, tmp_path):
        """Verify dry-run mode does not modify the database."""
        with app.app_context():
            fixture = comprehensive_work_fixture
            duplicate_id = fixture["duplicate_work_id"]
            expressions_before = db.session.execute(select(Expression).where(Expression.work_id == duplicate_id)).scalars().all()
            assert len(expressions_before) > 0
            result = run_safe_etl_pipeline(dry_run=True, backup_dir=tmp_path, verbose=False)
            assert result["dry_run"] is True
            duplicate_still_exists = db.session.execute(select(Work).where(Work.id == duplicate_id)).scalars().first()
            assert duplicate_still_exists is not None
            expressions_after = db.session.execute(select(Expression).where(Expression.work_id == duplicate_id)).scalars().all()
            assert len(expressions_after) == len(expressions_before)

    def test_dry_run_generates_merge_plans(self, app, comprehensive_work_fixture, tmp_path):
        """Verify dry-run mode generates merge plans without applying them."""
        with app.app_context():
            result = run_safe_etl_pipeline(dry_run=True, backup_dir=tmp_path, verbose=False)
            assert result["dry_run"] is True
            assert len(result["work_merge_plans"]) > 0 or len(result["manifestation_merge_plans"]) > 0
            # Verify no backup file in dry-run mode
            assert result["backup_file"] is None


class TestLiveModeWithBackup:
    """Test live mode requires and verifies complete backup."""

    def test_live_mode_creates_and_verifies_backup(self, app, comprehensive_work_fixture, tmp_path):
        """Verify live mode creates complete backup and verifies coverage."""
        with app.app_context():
            result = run_safe_etl_pipeline(dry_run=False, backup_dir=tmp_path, verbose=False)
            assert result["dry_run"] is False
            assert result["backup_file"] is not None
            assert result["backup_verification"] is not None
            assert result["backup_verification"]["valid"] is True  # type: ignore[index]  # pylint: disable=unsubscriptable-object

    def test_live_mode_applies_merge_plans(self, app, comprehensive_work_fixture, tmp_path):
        """Verify live mode applies merge plans and reparents all dependents."""
        with app.app_context():
            fixture = comprehensive_work_fixture
            canonical_id = fixture["canonical_work_id"]
            duplicate_id = fixture["duplicate_work_id"]
            result = run_safe_etl_pipeline(dry_run=False, backup_dir=tmp_path, verbose=False)
            assert result["stats"]["reconciled_works"] >= 1
            duplicate_deleted = db.session.execute(select(Work).where(Work.id == duplicate_id)).scalars().first()
            assert duplicate_deleted is None
            reparented_expressions = db.session.execute(select(Expression).where(Expression.work_id == canonical_id)).scalars().all()
            assert len(reparented_expressions) >= 2


class TestConflictHandling:
    """Test conflict detection and abort behavior."""

    def test_work_merge_aborts_on_intent_conflict(self, app, tmp_path):
        """Verify Work merge aborts when UserWorkIntent conflict exists."""
        with app.app_context():
            user = User(email="abort_user@iqoqo.local", display_name="Abort User")
            db.session.add(user)
            db.session.flush()
            canonical = Work(title="Abort Test Work")
            duplicate = Work(title="Abort Test Work")
            db.session.add_all([canonical, duplicate])
            db.session.flush()
            intent1 = UserWorkIntent(work_id=canonical.id, user_id=user.id, status="want_to_read")
            intent2 = UserWorkIntent(work_id=duplicate.id, user_id=user.id, status="reading")
            db.session.add_all([intent1, intent2])
            db.session.commit()
            result = run_safe_etl_pipeline(dry_run=False, backup_dir=tmp_path, verbose=False)
            assert len(result["conflicts"]) > 0
            assert any("UserWorkIntent conflict" in c for c in result["conflicts"])
            duplicate_still_exists = db.session.execute(select(Work).where(Work.id == duplicate.id)).scalars().first()
            assert duplicate_still_exists is not None


class TestIdempotence:
    """Test idempotent execution."""

    def test_idempotent_rerun_after_successful_merge(self, app, comprehensive_work_fixture, tmp_path):
        """Verify rerunning ETL after successful merge produces no changes."""
        with app.app_context():
            result1 = run_safe_etl_pipeline(dry_run=False, backup_dir=tmp_path, verbose=False)
            _ = result1["stats"]["reconciled_works"]  # noqa: F841
            result2 = run_safe_etl_pipeline(dry_run=False, backup_dir=tmp_path, verbose=False)
            reconciled_works_2 = result2["stats"]["reconciled_works"]
            assert reconciled_works_2 == 0
