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
"""Every referencing row must survive a merge and follow the survivor.

The companion to ``test_frbr_merge_coverage.py``: that file proves the map
*declares* every column, this one proves re-pointing actually *works* for every
kind of referencing row, on all three abstract FRBR tiers and through both entry
points.

These assertions exist because the aggregate counts of a previous test could not
distinguish a re-pointed row from a deleted one.  Two shipped defects hid there:

* ``merge_frbr_entities`` re-pointed only 2 of 13 Work-referencing columns, so
  deleting the source cascade-deleted a reader's wishlist entry, a box-set
  membership, a work expansion, a container aggregation, social feedback, a
  social note, and an escalation request.
* It also dropped the source's *unique* contributor, because
  ``db.session.delete()`` cascades ``delete-orphan`` over a ``lazy="selectin"``
  collection whose child FK was re-pointed at the column level.

SQLite does not enforce foreign keys by default, so ``PRAGMA foreign_keys=ON`` is
enabled per test to reproduce PostgreSQL's ``ON DELETE CASCADE``.  Both of the
defects above were confirmed on PostgreSQL 18 before being fixed.
"""

import uuid

import pytest

from app.core.frbr_merge import delete_source_row, repoint_references
from app.core.frbr_service import merge_frbr_entities
from app.db import db
from app.db.auth import User
from app.db.contributions import Contributor, WorkContribution, WorkPart
from app.db.core import (
    EntityAuditLog,
    Expression,
    Item,
    Manifestation,
    SemanticLink,
    UserWorkIntent,
    Work,
    WorkExpansionLink,
)
from app.db.games import ContainerAggregation
from app.db.social import EscalationRequest, SocialFeedback, SocialNote

#: Columns whose ON DELETE action determines whether a missed re-point destroys
#: or merely orphans the row.  Recorded in the assertion messages because the
#: two failure modes need different fixes.
CASCADE_COLUMNS = {
    "work": ("user_work_intents", "work_parts", "work_expansion_links", "container_aggregations"),
}


def _fk_enforcement_needed() -> bool:
    """Return whether this run needs SQLite's foreign keys switched on.

    PostgreSQL always enforces foreign keys, so ``make test-merge-integrity-pg``
    needs no pragma and must not issue one: ``PRAGMA`` is not valid there.
    """
    return db.engine.dialect.name == "sqlite"


def _enable_foreign_keys():
    """Turn on SQLite FK enforcement so CASCADE behaves as it does on PostgreSQL."""
    from sqlalchemy import text

    if _fk_enforcement_needed():
        db.session.execute(text("PRAGMA foreign_keys=ON"))


def _disable_foreign_keys():
    """Restore SQLite's default permissive FK behaviour for other tests."""
    from sqlalchemy import text

    if _fk_enforcement_needed():
        db.session.execute(text("PRAGMA foreign_keys=OFF"))


def _user(suffix: str) -> User:
    """Create a persisted user for ownership columns.

    The address carries a UUID because the PostgreSQL target
    (``make test-merge-integrity-pg``) reuses one throwaway database, so a run
    that is interrupted before teardown can leave a row behind.

    Args:
        suffix: Readable label distinguishing the caller.

    Returns:
        The persisted user.
    """
    unique = uuid.uuid4().hex[:12]
    user = User(email=f"merge-{suffix}-{unique}@iqoqo.local", display_name=f"Merge {suffix}")
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    return user


def test_work_merge_preserves_every_referencing_row():
    """Re-pointing a Work must move, never destroy, all thirteen references."""
    _enable_foreign_keys()
    try:
        source = Work(title="Source Work")
        target = Work(title="Target Work")
        member = Work(title="Member Work")
        expansion = Work(title="Expanded Work")
        db.session.add_all([source, target, member, expansion])
        db.session.commit()
        user = _user("work")

        wishlist = UserWorkIntent(user_id=user.id, work_id=source.id, status="want_to_read")
        part = WorkPart(container_work_id=source.id, part_work_id=member.id, sequence=0)
        expansion_link = WorkExpansionLink(base_work_id=source.id, expansion_work_id=expansion.id, link_type="expanded_by")
        aggregation = ContainerAggregation(
            container_work_id=source.id, aggregated_type="work", aggregated_work_id=member.id, component_name="board"
        )
        feedback = SocialFeedback(user_id=user.id, work_id=source.id, comment="probe")
        note = SocialNote(user_id=user.id, work_id=source.id, note="probe")
        escalation = EscalationRequest(
            user_id=user.id,
            work_id=source.id,
            field_name="title",
            suggested_value="Source Work",
            request_type="metadata_correction",
            status="pending",
        )
        expression = Expression(work_id=source.id, language="en", content_type="text", meta={})
        db.session.add_all([wishlist, part, expansion_link, aggregation, feedback, note, escalation, expression])
        db.session.commit()

        source_id, target_id = source.id, target.id
        db.session.expire_all()

        merge_frbr_entities("work", source_id, target_id)
        db.session.expire_all()

        assert db.session.get(Work, source_id) is None
        # Every ON DELETE CASCADE column must have followed the survivor.
        assert db.session.get(UserWorkIntent, wishlist.id) is not None, "wishlist entry was cascade-deleted"
        assert db.session.get(WorkPart, {"container_work_id": target_id, "part_work_id": member.id}) is not None
        assert db.session.get(Expression, expression.id).work_id == target_id
        assert db.session.get(SocialFeedback, feedback.id).work_id == target_id
        assert db.session.get(SocialNote, note.id).work_id == target_id
        assert db.session.get(EscalationRequest, escalation.id).work_id == target_id
        assert db.session.get(WorkExpansionLink, expansion_link.id).base_work_id == target_id
        assert db.session.get(ContainerAggregation, aggregation.id).container_work_id == target_id
    finally:
        _disable_foreign_keys()


def test_work_merge_migrates_a_source_only_contributor():
    """A contributor unique to the source must follow the survivor.

    Regression: the delete-orphan cascade on ``Work.contributions``
    (``lazy="selectin"``) deleted this row instead of migrating it, so a co-author
    silently disappeared from the merged Work.  The aggregate row count alone
    cannot detect this, which is why the three shapes are asserted separately.
    """
    source = Work(title="Source Work")
    target = Work(title="Target Work")
    db.session.add_all([source, target])
    db.session.commit()
    alice = Contributor(name="Merge Alice", type="person")
    bob = Contributor(name="Merge Bob", type="person")
    db.session.add_all([alice, bob])
    db.session.commit()

    # source-only, target-only, and a duplicated natural key.
    source_only = WorkContribution(work_id=source.id, contributor_id=bob.id, role="author", sequence=1)
    target_only = WorkContribution(work_id=target.id, contributor_id=bob.id, role="translator", sequence=2)
    dup_source = WorkContribution(work_id=source.id, contributor_id=alice.id, role="author", sequence=0)
    dup_target = WorkContribution(work_id=target.id, contributor_id=alice.id, role="author", sequence=0)
    db.session.add_all([source_only, target_only, dup_source, dup_target])
    db.session.commit()

    source_only_id, target_id = source_only.id, target.id
    db.session.expire_all()

    merge_frbr_entities("work", source.id, target_id)
    db.session.expire_all()

    # The unique source contributor migrated...
    migrated = db.session.get(WorkContribution, source_only_id)
    assert migrated is not None, "the source's unique contributor was deleted by the delete-orphan cascade"
    assert migrated.work_id == target_id
    # ...the target-only contributor is untouched...
    assert db.session.get(WorkContribution, target_only.id).work_id == target_id
    # ...and the duplicate collapsed to a single row.
    survivors = WorkContribution.query.filter_by(work_id=target_id, contributor_id=alice.id).all()
    assert len(survivors) == 1


def test_work_merge_collapses_duplicate_wishlist_entries():
    """Two wishlist rows that become identical after the merge collapse to one."""
    source = Work(title="Source Work")
    target = Work(title="Target Work")
    db.session.add_all([source, target])
    db.session.commit()
    user = _user("collapse")

    db.session.add_all(
        [
            UserWorkIntent(user_id=user.id, work_id=source.id, status="want_to_read"),
            UserWorkIntent(user_id=user.id, work_id=target.id, status="want_to_read"),
        ]
    )
    db.session.commit()
    target_id = target.id
    db.session.expire_all()

    merge_frbr_entities("work", source.id, target_id)
    db.session.expire_all()

    rows = UserWorkIntent.query.filter_by(user_id=user.id).all()
    assert len(rows) == 1, f"expected the duplicate wishlist row to collapse, found {len(rows)}"
    assert rows[0].work_id == target_id


def test_work_merge_repoints_semantic_links():
    """Polymorphic SemanticLink rows must follow the survivor."""
    source = Work(title="Source Work")
    target = Work(title="Target Work")
    db.session.add_all([source, target])
    db.session.commit()
    link = SemanticLink(
        entity_type="work",
        entity_id=source.id,
        authority="wikidata",
        external_uri="http://www.wikidata.org/Q42",
    )
    db.session.add(link)
    db.session.commit()
    target_id, link_id = target.id, link.id
    db.session.expire_all()

    merge_frbr_entities("work", source.id, target_id)
    db.session.expire_all()

    moved = db.session.get(SemanticLink, link_id)
    assert moved.entity_id == target_id
    assert moved.external_uri == "http://www.wikidata.org/Q42"


def test_expression_merge_preserves_every_referencing_row():
    """Re-pointing an Expression must preserve its Manifestations and relations."""
    _enable_foreign_keys()
    try:
        work = Work(title="Shared Work")
        db.session.add(work)
        db.session.commit()
        source = Expression(work_id=work.id, language="en", content_type="text", meta={})
        target = Expression(work_id=work.id, language="en", content_type="text", meta={})
        db.session.add_all([source, target])
        db.session.commit()
        user = _user("expression")

        child = Manifestation(expression_id=source.id, meta={})
        wishlist = UserWorkIntent(user_id=user.id, work_id=work.id, expression_id=source.id, status="want_to_read")
        feedback = SocialFeedback(user_id=user.id, expression_id=source.id, comment="probe")
        note = SocialNote(user_id=user.id, expression_id=source.id, note="probe")
        db.session.add_all([child, wishlist, feedback, note])
        db.session.commit()

        target_id = target.id
        db.session.expire_all()

        merge_frbr_entities("expression", source.id, target_id)
        db.session.expire_all()

        assert db.session.get(Expression, source.id) is None
        assert db.session.get(Manifestation, child.id).expression_id == target_id
        # UserWorkIntent.expression_id is SET NULL; a user targeting one
        # realization must follow the survivor rather than be orphaned.
        assert db.session.get(UserWorkIntent, wishlist.id).expression_id == target_id
        assert db.session.get(SocialFeedback, feedback.id).expression_id == target_id
        assert db.session.get(SocialNote, note.id).expression_id == target_id
    finally:
        _disable_foreign_keys()


def test_manifestation_merge_preserves_every_referencing_row():
    """Re-pointing a Manifestation must preserve its Items and user intent."""
    _enable_foreign_keys()
    try:
        work = Work(title="Shared Work")
        db.session.add(work)
        db.session.commit()
        expression = Expression(work_id=work.id, language="en", content_type="text", meta={})
        db.session.add(expression)
        db.session.commit()
        source = Manifestation(expression_id=expression.id, meta={})
        target = Manifestation(expression_id=expression.id, meta={})
        db.session.add_all([source, target])
        db.session.commit()
        user = _user("manifestation")

        item = Item(owner_id=user.id, manifestation_id=source.id)
        wishlist = UserWorkIntent(user_id=user.id, work_id=work.id, manifestation_id=source.id, status="want_to_read")
        feedback = SocialFeedback(user_id=user.id, manifestation_id=source.id, comment="probe")
        db.session.add_all([item, wishlist, feedback])
        db.session.commit()

        target_id = target.id
        db.session.expire_all()

        merge_frbr_entities("manifestation", source.id, target_id)
        db.session.expire_all()

        assert db.session.get(Manifestation, source.id) is None
        assert db.session.get(Item, item.id).manifestation_id == target_id
        assert db.session.get(UserWorkIntent, wishlist.id).manifestation_id == target_id
        assert db.session.get(SocialFeedback, feedback.id).manifestation_id == target_id
    finally:
        _disable_foreign_keys()


@pytest.mark.parametrize("entity_type", ["work", "expression", "manifestation"])
def test_merge_rejects_self_and_cross_tier_merges(entity_type):
    """Self-merges and cross-tier merges must be refused without any write."""
    work = Work(title="Only Work")
    db.session.add(work)
    db.session.commit()
    work_id = work.id

    with pytest.raises(ValueError, match="with itself"):
        merge_frbr_entities(entity_type, work_id, work_id)
    with pytest.raises(ValueError, match="Invalid entity_type"):
        merge_frbr_entities("item", work_id, work_id)

    assert Work.query.filter_by(id=work_id).count() == 1


def test_merge_rolls_back_completely_on_failure():
    """A mid-merge failure must leave both entities and all children untouched."""
    source = Work(title="Source Work")
    target = Work(title="Target Work")
    db.session.add_all([source, target])
    db.session.commit()
    expression = Expression(work_id=source.id, language="en", content_type="text", meta={})
    db.session.add(expression)
    db.session.commit()
    source_id, target_id, expression_id = source.id, target.id, expression.id
    db.session.expire_all()

    from app.core import frbr_merge

    original = frbr_merge.repoint_semantic_links
    calls = {"n": 0}

    def explode(entity_type, src, dst):
        calls["n"] += 1
        raise RuntimeError("boom")

    frbr_merge.repoint_semantic_links = explode
    try:
        with pytest.raises(RuntimeError):
            merge_frbr_entities("work", source_id, target_id)
    finally:
        frbr_merge.repoint_semantic_links = original

    db.session.expire_all()
    assert calls["n"] == 1, "the failure must occur inside the re-point loop"
    assert db.session.get(Work, source_id) is not None, "source Work was deleted despite the failure"
    assert db.session.get(Work, target_id) is not None
    assert db.session.get(Expression, expression_id).work_id == source_id, "child was moved despite the rollback"


def test_audit_uses_tier_specific_change_type():
    """Both entry points must write the same audit vocabulary."""
    source = Work(title="Source Work")
    target = Work(title="Target Work")
    db.session.add_all([source, target])
    db.session.commit()
    target_id = target.id
    db.session.expire_all()

    merge_frbr_entities("work", source.id, target_id)
    db.session.expire_all()

    audit = EntityAuditLog.query.filter_by(change_type="merge_work").all()
    assert len(audit) == 1
    assert audit[0].entity_type == "work"
    assert audit[0].diff["target_id"] == target_id
    assert "migrated_children" in audit[0].diff
    assert "repointed" in audit[0].diff, "the audit must record the per-table re-point counters"


def test_delete_source_row_does_not_cascade():
    """``delete_source_row`` must bypass ORM cascade processing.

    This is the invariant that keeps a re-pointed ``lazy="selectin"`` child from
    being deleted along with its former parent.
    """
    source = Work(title="Source Work")
    target = Work(title="Target Work")
    db.session.add_all([source, target])
    db.session.commit()
    contributor = Contributor(name="Cascade Probe", type="person")
    db.session.add(contributor)
    db.session.commit()
    contribution = WorkContribution(work_id=source.id, contributor_id=contributor.id, role="author", sequence=0)
    db.session.add(contribution)
    db.session.commit()
    source_id, target_id, contribution_id = source.id, target.id, contribution.id

    repoint_references("work", source_id, target_id)
    delete_source_row(source)
    db.session.commit()
    db.session.expire_all()

    assert db.session.get(Work, source_id) is None
    assert db.session.get(WorkContribution, contribution_id) is not None, "Core-level delete cascaded to the child"
    assert db.session.get(WorkContribution, contribution_id).work_id == target_id
