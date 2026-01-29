"""This module provides services for creating FRBR-compliant objects."""

from typing import Any

from app.db.models import Expression, Item, Manifestation, Work, db


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


def create_expression(
    work_id: int, content_type: str = "text", language: str = "en", meta: dict[str, Any] | None = None
) -> Expression:
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
) -> Manifestation:
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
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()

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
        return manifestation  # type: ignore[no-any-return]

    # Create the full FRBR hierarchy
    work = create_work(title=title, meta={"original_language": "en"})
    expression = create_expression(work_id=work.id, content_type="text", language="en")

    metadata: dict[str, Any] = {"Title": title}
    if authors:
        metadata["Authors"] = authors if isinstance(authors, list) else [authors]

    manifestation = create_manifestation(expression_id=expression.id, isbn13=isbn, publisher=publisher, meta=metadata)

    return manifestation
