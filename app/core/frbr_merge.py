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
"""Shared FRBR merge primitives: re-point every reference, then drop the source.

Consolidating two entities at the same FRBR level is one operation with two
halves, and iqoqo used to have two implementations of it that disagreed about
what a merge meant.  This module is the single place that answers "what must
move when a Work, Expression, or Manifestation is consolidated", so the manual
merge entry point and the duplicate-review queue cannot drift apart.

The reference maps below are exhaustive by construction and are checked against
the database schema by ``tests/test_frbr_merge_coverage.py``.  Counts as of this
writing:

* Work: 13 foreign keys across 10 tables, plus ``SemanticLink``
* Expression: 7 foreign keys across 7 tables, plus ``SemanticLink``
* Manifestation: 9 foreign keys across 9 tables, plus ``SemanticLink``

A column may only be absent from its tier's map by appearing in that tier's
``ALLOWED_OMISSIONS`` tuple with a justification, because every omission is a
place where a merge would silently destroy or orphan a row.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, literal, select

from app.db import db
from app.db.contributions import (
    ExpressionContribution,
    ManifestationContribution,
    WorkContribution,
    WorkPart,
)
from app.db.core import (
    Expression,
    ImageScan,
    Item,
    Manifestation,
    SemanticLink,
    UserWorkIntent,
    WorkExpansionLink,
)
from app.db.games import ContainerAggregation
from app.db.roadmap import RoadmapItem
from app.db.settings import ScanTelemetry
from app.db.social import EscalationRequest, SocialFeedback, SocialNote

__all__ = [
    "ALLOWED_OMISSIONS",
    "REFPOINTS_BY_TIER",
    "RefPoint",
    "consolidate_manifestation_identifiers",
    "delete_source_row",
    "lock_pair",
    "repoint_references",
]


@dataclass(frozen=True)
class RefPoint:
    """One column that must follow a merged entity onto the survivor.

    Attributes:
        model: Model class declaring the foreign key.
        fk_attribute: Name of the foreign-key column on ``model``.
        unique_attributes: Columns forming the natural key.  When non-empty, a
            source row whose key already exists on the target is deleted rather
            than re-pointed, because the constraint would reject the move.
        polymorphic: True for :class:`SemanticLink`, which is keyed by an
            ``(entity_type, entity_id)`` pair rather than a real foreign key.
    """

    model: type
    fk_attribute: str
    unique_attributes: tuple[str, ...] = ()
    polymorphic: bool = False


#: FRBR Group 1 tier keys used by :data:`REFPOINTS_BY_TIER`.
TIER_WORK = "work"
TIER_EXPRESSION = "expression"
TIER_MANIFESTATION = "manifestation"

_WORK_REFPOINTS: tuple[RefPoint, ...] = (
    # The direct child, plus the FRBRoo relation tables that hang off it.
    RefPoint(Expression, "work_id"),
    RefPoint(WorkContribution, "work_id", ("contributor_id", "role")),
    RefPoint(WorkPart, "container_work_id", ("part_work_id",)),
    RefPoint(WorkPart, "part_work_id", ("container_work_id",)),
    RefPoint(WorkExpansionLink, "base_work_id", ("expansion_work_id",)),
    RefPoint(WorkExpansionLink, "expansion_work_id", ("base_work_id",)),
    RefPoint(ContainerAggregation, "container_work_id", ("aggregated_type", "aggregated_work_id", "aggregated_item_id", "component_name")),
    RefPoint(ContainerAggregation, "aggregated_work_id", ("container_work_id", "component_name")),
    # User-authored data.  UserWorkIntent.work_id is ON DELETE CASCADE, so
    # without this a merge would delete the reader's wishlist entry.
    RefPoint(UserWorkIntent, "work_id", ("user_id", "expression_id", "manifestation_id")),
    RefPoint(SocialFeedback, "work_id"),
    RefPoint(SocialNote, "work_id"),
    RefPoint(RoadmapItem, "work_id"),
    RefPoint(EscalationRequest, "work_id"),
    # Polymorphic: keyed by (entity_type, entity_id) rather than a real FK.
    RefPoint(SemanticLink, "entity_id", (), polymorphic=True),
)

_EXPRESSION_REFPOINTS: tuple[RefPoint, ...] = (
    RefPoint(Manifestation, "expression_id"),
    RefPoint(ExpressionContribution, "expression_id", ("contributor_id", "role")),
    # SET NULL today, but a user's deliberate target of one realization should
    # follow the survivor rather than be orphaned.
    RefPoint(UserWorkIntent, "expression_id"),
    RefPoint(SocialFeedback, "expression_id"),
    RefPoint(SocialNote, "expression_id"),
    RefPoint(RoadmapItem, "expression_id"),
    RefPoint(EscalationRequest, "expression_id"),
    # Polymorphic: keyed by (entity_type, entity_id) rather than a real FK.
    RefPoint(SemanticLink, "entity_id", (), polymorphic=True),
)

_MANIFESTATION_REFPOINTS: tuple[RefPoint, ...] = (
    RefPoint(Item, "manifestation_id"),
    RefPoint(ManifestationContribution, "manifestation_id", ("contributor_id", "role")),
    RefPoint(ImageScan, "manifestation_id"),
    RefPoint(UserWorkIntent, "manifestation_id", ("user_id", "work_id", "expression_id")),
    RefPoint(SocialFeedback, "manifestation_id"),
    RefPoint(SocialNote, "manifestation_id"),
    RefPoint(RoadmapItem, "manifestation_id"),
    RefPoint(ScanTelemetry, "manifestation_id"),
    RefPoint(EscalationRequest, "manifestation_id"),
    # Polymorphic: keyed by (entity_type, entity_id) rather than a real FK.
    RefPoint(SemanticLink, "entity_id", (), polymorphic=True),
)

#: Every referencing column per tier, keyed by FRBR level.
REFPOINTS_BY_TIER: dict[str, tuple[RefPoint, ...]] = {
    TIER_WORK: _WORK_REFPOINTS,
    TIER_EXPRESSION: _EXPRESSION_REFPOINTS,
    TIER_MANIFESTATION: _MANIFESTATION_REFPOINTS,
}

#: Referencing columns deliberately excluded from re-pointing, per tier, each
#: with the reason it must not move.  Anything absent from a tier's map must be
#: justified here, which is what makes the maps auditable.
ALLOWED_OMISSIONS: dict[str, frozenset[tuple[str, str]]] = {
    TIER_WORK: frozenset(),
    TIER_EXPRESSION: frozenset(),
    TIER_MANIFESTATION: frozenset(),
}


def repoint_simple(
    model: type,
    fk_attribute: str,
    source_id: int,
    target_id: int,
    *,
    where_extra: Any | None = None,
) -> int:
    """Re-point every non-unique child FK from one parent to another.

    Used for the plain ``manifestation_id``-style columns where re-pointing
    cannot create duplicates.

    Args:
        model: Model class holding the FK column.
        fk_attribute: Name of the FK column on ``model``.
        source_id: Parent id being consolidated away.
        target_id: Parent id being consolidated onto.
        where_extra: Optional additional SQL filter.

    Returns:
        Number of rows updated.
    """
    conditions = [getattr(model, fk_attribute) == source_id]
    if where_extra is not None:
        conditions.append(where_extra)
    result = db.session.execute(
        db.update(model).where(*conditions).values({fk_attribute: target_id}).execution_options(synchronize_session=False)
    )
    return int(getattr(result, "rowcount", 0) or 0)


def repoint_unique_child(
    model: type[Any],
    fk_attribute: str,
    unique_attributes: tuple[str, ...],
    source_id: int,
    target_id: int,
) -> int:
    """Re-point a uniquely-constrained child FK, collapsing collisions.

    Rows whose natural key already exists on the target are deleted, since the
    surviving target row is authoritative.

    This must not assume a surrogate ``id`` column: :class:`WorkPart` declares
    a composite primary key of ``(container_work_id, part_work_id)`` and has no
    ``id`` at all, so selecting the primary key would raise ``AttributeError``
    and fail the whole merge for any Work involved in a box set.

    Args:
        model: Model class holding the FK column.
        fk_attribute: Name of the FK column on ``model``.
        unique_attributes: Additional columns forming the natural key.
        source_id: Parent id being consolidated away.
        target_id: Parent id being consolidated onto.

    Returns:
        Number of rows re-pointed (collisions are not counted).
    """
    moved = 0
    rows: Sequence[Any] = db.session.execute(select(model).where(getattr(model, fk_attribute) == source_id)).scalars().all()
    for row in rows:
        collision_filters = [getattr(model, unique_attribute) == getattr(row, unique_attribute) for unique_attribute in unique_attributes]
        existing = db.session.execute(
            select(literal(1)).where(getattr(model, fk_attribute) == target_id, *collision_filters).limit(1)
        ).first()
        if existing is not None:
            db.session.delete(row)
        else:
            setattr(row, fk_attribute, target_id)
            moved += 1
    return moved


def repoint_semantic_links(entity_type: str, source_id: int, target_id: int) -> int:
    """Re-point polymorphic :class:`SemanticLink` rows onto the surviving entity.

    Args:
        entity_type: ``"work"``, ``"expression"``, or ``"manifestation"``.
        source_id: Entity id being consolidated away.
        target_id: Entity id being consolidated onto.

    Returns:
        Number of links re-pointed.
    """
    result = db.session.execute(
        db.update(SemanticLink)
        .where(SemanticLink.entity_type == entity_type, SemanticLink.entity_id == source_id)
        .values(entity_id=target_id)
        .execution_options(synchronize_session=False)
    )
    return int(getattr(result, "rowcount", 0) or 0)


def repoint_references(tier: str, source_id: int, target_id: int) -> dict[str, int]:
    """Move every table that references ``tier`` from the source onto the target.

    Iterates the tier's :data:`REFPOINTS_BY_TIER` entry, so the set of moved
    tables is declared in exactly one place and is verified against the schema
    by ``tests/test_frbr_merge_coverage.py``.

    Args:
        tier: ``"work"``, ``"expression"``, or ``"manifestation"``.
        source_id: Entity id being consolidated away.
        target_id: Entity id being consolidated onto.

    Returns:
        Mapping of ``"Model.column"`` to the number of rows re-pointed.

    Raises:
        KeyError: If ``tier`` is not an abstract FRBR level.
    """
    refpoints = REFPOINTS_BY_TIER[tier]
    moved: dict[str, int] = {}
    for refpoint in refpoints:
        label = f"{refpoint.model.__name__}.{refpoint.fk_attribute}"
        if refpoint.polymorphic:
            moved[label] = repoint_semantic_links(tier, source_id, target_id)
        elif refpoint.unique_attributes:
            moved[label] = repoint_unique_child(refpoint.model, refpoint.fk_attribute, refpoint.unique_attributes, source_id, target_id)
        else:
            moved[label] = repoint_simple(refpoint.model, refpoint.fk_attribute, source_id, target_id)
    return moved


def delete_source_row(source: Any) -> None:
    """Remove the discarded entity's row with a Core-level DELETE.

    ``db.session.delete()`` must never be used to drop a merged entity.  Several
    relationships are declared ``cascade="all, delete-orphan"`` with
    ``lazy="selectin"`` -- ``Work.contributions`` is the sharpest case -- and the
    in-session collection on ``source`` still holds children that were just
    re-pointed by assigning their foreign-key column.  Assigning a column does
    not update the parent's loaded collection, so the ORM still sees the child as
    an orphan of the source and cascades a delete to it, destroying exactly the
    row the merge exists to preserve.  Verified on PostgreSQL: a source-only
    contributor was deleted rather than migrated, leaving the survivor with two
    contributions where three were correct.

    A Core DELETE bypasses ORM cascade processing entirely, which is the intent:
    every child has already been re-pointed, so only the now-empty parent row is
    removed.

    The primary key is captured before the statement runs; touching ``source``
    afterwards would trigger an autoflush and defeat the ordering guarantees
    the merge relies on.

    Args:
        source: The discarded Work, Expression, or Manifestation.
    """
    model = type(source)
    source_id = source.id
    db.session.execute(delete(model).where(model.id == source_id))
    db.session.expire_all()


#: Edition-defining Manifestation attributes copied from the source when the
#: primary lacks them.  All of them belong to F3 and nowhere else.
_ADOPTABLE_IDENTIFIERS = (
    "ean",
    "upc",
    "barcode",
    "catalog_number",
    "publisher",
    "publication_date",
    "format",
    "format_type",
    "label",
    "cover_url",
)


def consolidate_manifestation_identifiers(target: Manifestation, source: Manifestation) -> None:
    """Reconcile edition identifiers from ``source`` onto the surviving Manifestation.

    FRBRoo F3: identifiers belong to the Manifestation and nowhere else.  The
    surviving primary is authoritative; a value the primary lacks is adopted, and
    one it already carries is preserved as an alternate on the Manifestation
    rather than being dropped or promoted to a Work or Expression.

    ``target.meta`` is expected to have been consolidated by the caller first.

    Args:
        target: The surviving Manifestation.
        source: The discarded Manifestation.
    """
    alternate_isbns = target.meta.get("alternate_isbn13")
    if not isinstance(alternate_isbns, list):
        alternate_isbns = []

    for attribute in _ADOPTABLE_IDENTIFIERS:
        source_value = getattr(source, attribute, None)
        if source_value in (None, ""):
            continue
        if getattr(target, attribute, None) in (None, ""):
            setattr(target, attribute, source_value)
            continue
        if attribute == "barcode":
            # Barcodes legitimately identify different printings, so keep the
            # source's alongside the primary's.
            alternates = target.meta.get("alternate_barcodes")
            if not isinstance(alternates, list):
                alternates = []
            if source_value not in alternates:
                alternates.append(source_value)
            target.meta["alternate_barcodes"] = alternates

    source_isbn13 = source.isbn13
    if source_isbn13:
        if not target.isbn13:
            # Release the unique isbn13 index on the source row *before*
            # adopting it.  Both rows would otherwise carry the same value at
            # flush time, and the UPDATE order within a single flush is not
            # guaranteed, so the constraint would reject the merge.  Flushing
            # here makes the release explicit and deterministic.
            source.isbn13 = None
            db.session.flush()
            target.isbn13 = source_isbn13
        elif source_isbn13 != target.isbn13 and source_isbn13 not in alternate_isbns:
            alternate_isbns.append(source_isbn13)
    if alternate_isbns:
        target.meta["alternate_isbn13"] = alternate_isbns


def lock_pair(model: type, source_id: int, target_id: int) -> list[Any]:
    """Lock both entities in ascending id order for the rest of the transaction.

    Ordering by id prevents two concurrent merges of the same pair from
    deadlocking against each other.

    Args:
        model: ORM class of the tier being merged.
        source_id: Id of the entity being consolidated away.
        target_id: Id of the surviving entity.

    Returns:
        The two locked rows in ascending id order, or fewer if one is gone.
    """
    return list(
        db.session.execute(select(model).where(model.id.in_([source_id, target_id])).order_by(model.id).with_for_update()).scalars().all()
    )
