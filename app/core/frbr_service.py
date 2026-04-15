"""This module provides services for creating FRBR-compliant objects."""

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
from typing import Any

from app.db.audio import Contributor, ExpressionContribution, WorkContribution, WorkPart
from app.db.core import Expression, Item, Manifestation, Work
from app.db.models import db


def create_work(title: str, meta: dict[str, Any] | None = None) -> Work:
    """
    Creates a new Work.

    Args:
        title: The title of the work
        meta: Additional metadata for the work

    Returns:
        The created Work object
    """
    if meta is None:
        meta = {}
    work = Work(title=title, meta=meta)
    db.session.add(work)
    db.session.commit()
    return work


def create_expression(work_id: int, content_type: str = "text", language: str = "en", meta: dict[str, Any] | None = None) -> Expression:
    """
    Creates a new Expression for a Work.

    Args:
        work_id: The ID of the parent work
        content_type: Type of content (e.g., 'text', 'sound', 'notated_music')
        language: Language code (e.g., 'en', 'pl')
        meta: Additional metadata for the expression

    Returns:
        The created Expression object
    """
    if meta is None:
        meta = {}
    expression = Expression(work_id=work_id, content_type=content_type, language=language, meta=meta)
    db.session.add(expression)
    db.session.commit()
    return expression


def create_manifestation(
    expression_id: int,
    isbn13: str | None = None,
    upc: str | None = None,
    ean: str | None = None,
    publisher: str | None = None,
    publication_date: Any | None = None,
    meta: dict[str, Any] | None = None,
) -> Manifestation:
    """
    Creates a new Manifestation for an Expression.

    Args:
        expression_id: The ID of the parent expression
        isbn13: ISBN-13 identifier
        upc: UPC identifier
        ean: EAN identifier
        publisher: Publisher name
        publication_date: Date of publication
        meta: Additional metadata (e.g., Title, Authors, cover images)

    Returns:
        The created Manifestation object
    """
    if meta is None:
        meta = {}
    manifestation = Manifestation(
        expression_id=expression_id,
        isbn13=isbn13,
        upc=upc,
        ean=ean,
        publisher=publisher,
        publication_date=publication_date,
        meta=meta,
    )
    db.session.add(manifestation)
    db.session.commit()
    return manifestation


def create_item(
    manifestation_id: int,
    owner_id: str,
    status: str = "available",
    condition: str | None = None,
    meta: dict[str, Any] | None = None,
) -> Item:
    """
    Creates a new Item for a Manifestation.

    Args:
        manifestation_id: The ID of the parent manifestation
        owner_id: The ID of the owner
        status: Status of the item (e.g., 'available', 'lent', 'lost', 'wish_list')
        condition: Condition of the item
        meta: Additional metadata (e.g., tags, notes, location)

    Returns:
        The created Item object
    """
    if meta is None:
        meta = {}
    item = Item(manifestation_id=manifestation_id, owner_id=owner_id, status=status, condition=condition, meta=meta)
    db.session.add(item)
    db.session.commit()
    return item


def get_or_create_book_manifestation(
    isbn: str, title: str, authors: list | None = None, publisher: str | None = None
) -> Manifestation | None:
    """
    Get or create a complete FRBR hierarchy for a book.

    This is a convenience function that creates Work -> Expression -> Manifestation
    if they don't exist, or returns the existing Manifestation.

    Args:
        isbn: ISBN-13 or ISBN-10
        title: Book title
        authors: List of author names
        publisher: Publisher name

    Returns:
        The Manifestation object
    """
    # Check if manifestation already exists
    manifestation: Manifestation | None = Manifestation.query.filter_by(isbn13=isbn).first()  # type: ignore[assignment]

    if manifestation:
        # Update metadata if provided
        if title or authors:
            if not manifestation.meta:
                manifestation.meta = {}
            if title:
                manifestation.meta["Title"] = title
            if authors:
                manifestation.meta["Authors"] = authors
            db.session.commit()
        return manifestation

    # Create the full FRBR hierarchy
    work = create_work(title=title, meta={"original_language": "en"})
    expression = create_expression(work_id=work.id, content_type="text", language="en")

    metadata: dict[str, Any] = {"Title": title}
    if authors:
        metadata["Authors"] = authors if isinstance(authors, list) else [authors]

    manifestation = create_manifestation(expression_id=expression.id, isbn13=isbn, publisher=publisher, meta=metadata)

    return manifestation


def get_or_create_contributor(name: str, contributor_type: str = "person") -> Contributor | None:
    """
    Get an existing contributor by name, or create a new one.

    Args:
        name: Display name of the contributor.
        contributor_type: ``'person'`` or ``'organization'``.

    Returns:
        The existing or newly created :class:`~app.db.audio.Contributor`.
    """
    from sqlalchemy.exc import IntegrityError

    contributor: Contributor | None = Contributor.query.filter_by(name=name, type=contributor_type).first()  # type: ignore[assignment]
    if contributor:
        return contributor

    try:
        contributor = Contributor(name=name, type=contributor_type)
        db.session.add(contributor)
        db.session.commit()
        return contributor
    except IntegrityError:
        db.session.rollback()
        return Contributor.query.filter_by(name=name, type=contributor_type).first()  # type: ignore[no-any-return]


def add_work_contribution(
    work_id: int,
    contributor_id: int,
    role: str,
    sequence: int = 0,
) -> WorkContribution:
    """
    Link a contributor to a Work with a creative role (Composition Event).

    Args:
        work_id: ID of the parent :class:`~app.db.core.Work`.
        contributor_id: ID of the :class:`~app.db.audio.Contributor`.
        role: Creative role (see :data:`~app.db.audio.WORK_CONTRIBUTION_ROLES`).
        sequence: Display order when multiple contributors share the same role.

    Returns:
        The created :class:`~app.db.audio.WorkContribution`.
    """
    contribution = WorkContribution(
        work_id=work_id,
        contributor_id=contributor_id,
        role=role,
        sequence=sequence,
    )
    db.session.add(contribution)
    db.session.commit()
    return contribution


def add_expression_contribution(
    expression_id: int,
    contributor_id: int,
    role: str,
    sequence: int = 0,
) -> ExpressionContribution:
    """
    Link a contributor to an Expression with a performance role (Performance Event).

    Args:
        expression_id: ID of the parent :class:`~app.db.core.Expression`.
        contributor_id: ID of the :class:`~app.db.audio.Contributor`.
        role: Performance role (see :data:`~app.db.audio.EXPRESSION_CONTRIBUTION_ROLES`).
        sequence: Display order when multiple contributors share the same role.

    Returns:
        The created :class:`~app.db.audio.ExpressionContribution`.
    """
    contribution = ExpressionContribution(
        expression_id=expression_id,
        contributor_id=contributor_id,
        role=role,
        sequence=sequence,
    )
    db.session.add(contribution)
    db.session.commit()
    return contribution


def create_work_part(container_work_id: int, part_work_id: int, sequence: int = 0) -> WorkPart:
    """
    Declare that a Work is a part of a container Work (F15 Complex Work).

    Args:
        container_work_id: ID of the box-set or anthology :class:`~app.db.core.Work`.
        part_work_id: ID of the member :class:`~app.db.core.Work`.
        sequence: Display order of the part within the container.

    Returns:
        The created :class:`~app.db.audio.WorkPart`.
    """
    work_part = WorkPart(
        container_work_id=container_work_id,
        part_work_id=part_work_id,
        sequence=sequence,
    )
    db.session.add(work_part)
    db.session.commit()
    return work_part


# --- UPDATE METHODS ---


def update_work(work_id: int, title: str | None = None, meta: dict[str, Any] | None = None) -> Work:
    """
    Update an existing Work.

    Args:
        work_id: The ID of the work to update
        title: New title for the work
        meta: Metadata to merge with existing

    Returns:
        The updated Work object
    """
    work = db.session.get(Work, work_id)
    if work is None:
        raise ValueError(f"Work with id {work_id} not found")

    if title is not None:
        work.title = title
    if meta is not None:
        current_meta = dict(work.meta or {})
        current_meta.update(meta)
        work.meta = current_meta
    db.session.commit()
    return work


def update_expression(
    expression_id: int,
    work_id: int | None = None,
    content_type: str | None = None,
    language: str | None = None,
    meta: dict[str, Any] | None = None,
) -> Expression:
    """
    Update an existing Expression.

    Args:
        expression_id: The ID of the expression to update
        work_id: New parent work ID
        content_type: New content type
        language: New language code
        meta: Metadata to merge with existing

    Returns:
        The updated Expression object
    """
    expr = db.session.get(Expression, expression_id)
    if expr is None:
        raise ValueError(f"Expression with id {expression_id} not found")

    if work_id is not None:
        work = db.session.get(Work, work_id)
        if work is None:
            raise ValueError(f"Work with id {work_id} not found")
        expr.work_id = work_id
    if content_type is not None:
        expr.content_type = content_type
    if language is not None:
        expr.language = language
    if meta is not None:
        current_meta = dict(expr.meta or {})
        current_meta.update(meta)
        expr.meta = current_meta
    db.session.commit()
    return expr


def update_manifestation(
    manifestation_id: int,
    expression_id: int | None = None,
    isbn13: str | None = None,
    upc: str | None = None,
    ean: str | None = None,
    publisher: str | None = None,
    publication_date: Any | None = None,
    meta: dict[str, Any] | None = None,
) -> Manifestation:
    """
    Update an existing Manifestation.

    Args:
        manifestation_id: The ID of the manifestation to update
        expression_id: New parent expression ID
        isbn13: New ISBN-13
        upc: New UPC
        ean: New EAN
        publisher: New publisher name
        publication_date: New publication date
        meta: Metadata to merge with existing

    Returns:
        The updated Manifestation object
    """
    manif = db.session.get(Manifestation, manifestation_id)
    if manif is None:
        raise ValueError(f"Manifestation with id {manifestation_id} not found")

    if expression_id is not None:
        expr = db.session.get(Expression, expression_id)
        if expr is None:
            raise ValueError(f"Expression with id {expression_id} not found")
        manif.expression_id = expression_id
    if isbn13 is not None:
        manif.isbn13 = isbn13
    if upc is not None:
        manif.upc = upc
    if ean is not None:
        manif.ean = ean
    if publisher is not None:
        manif.publisher = publisher
    if publication_date is not None:
        manif.publication_date = publication_date
    if meta is not None:
        current_meta = dict(manif.meta or {})
        current_meta.update(meta)
        manif.meta = current_meta
    db.session.commit()
    return manif


def update_item(
    item_id: int,
    manifestation_id: int | None = None,
    status: str | None = None,
    condition: str | None = None,
    meta: dict[str, Any] | None = None,
) -> Item:
    """
    Update an existing Item.

    Args:
        item_id: The ID of the item to update
        manifestation_id: New parent manifestation ID
        status: New status
        condition: New condition
        meta: Metadata to merge with existing

    Returns:
        The updated Item object
    """
    item = db.session.get(Item, item_id)
    if item is None:
        raise ValueError(f"Item with id {item_id} not found")

    if manifestation_id is not None:
        manif = db.session.get(Manifestation, manifestation_id)
        if manif is None:
            raise ValueError(f"Manifestation with id {manifestation_id} not found")
        item.manifestation_id = manifestation_id
    if status is not None:
        item.status = status
    if condition is not None:
        item.condition = condition
    if meta is not None:
        current_meta = dict(item.meta or {})
        current_meta.update(meta)
        item.meta = current_meta
    db.session.commit()
    return item
