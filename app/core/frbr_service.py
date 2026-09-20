"""This module provides services for creating FRBR-compliant objects."""

# pylint: disable=too-many-lines

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
import itertools
import re
from collections.abc import Generator, Iterable
from typing import TYPE_CHECKING, Any, cast

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.core.ontology_validation import (
    validate_container_not_linked_as_expansion,
    validate_work_not_expansion_aggregated,
)
from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY, FORMAT_TO_CATEGORY
from app.db.audio import Contributor, ExpressionContribution, WorkContribution, WorkPart
from app.db.core import (
    EXPRESSION_KIND_LIVE_PERFORMANCE,
    EXPRESSION_KINDS,
    WORK_LINK_TYPE_IS_EXPANSION_OF,
    WORK_LINK_TYPES,
    Expression,
    ImageScan,
    Item,
    Manifestation,
    UserCollectionItem,
    Work,
    WorkExpansionLink,
)
from app.db.models import db
from app.db.video import ManifestationContribution

if TYPE_CHECKING:
    from app.db.games import ContainerAggregation

_LEADING_ARTICLES_RE = re.compile(r"^(?:the|a|an|ten|ta|to)\s+", re.IGNORECASE)


def derive_sort_title(title: str) -> str:
    """Derive alphabetical sort title by stripping leading articles (The, A, An, Ten, Ta, To)."""
    if not title:
        return ""
    return _LEADING_ARTICLES_RE.sub("", title).strip()


def create_work(
    title: str,
    meta: dict[str, Any] | None = None,
    sort_title: str | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> Work:
    """
    Creates a new Work.

    Args:
        title: The title of the work
        meta: Additional metadata for the work
        sort_title: Alphabetical sort key (auto-derived from title if None)
        raw_payload: Verbatim provider payload JSON

    Returns:
        The created Work object
    """
    if meta is None:
        meta = {}
    if sort_title is None and title:
        sort_title = derive_sort_title(title)
    work = Work(title=title, sort_title=sort_title, meta=meta, raw_payload=raw_payload)
    db.session.add(work)
    db.session.commit()
    return work


def create_expression(
    work_id: int,
    content_type: str = "text",
    language: str = "en",
    meta: dict[str, Any] | None = None,
    kind: str | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> Expression:
    """
    Creates a new Expression for a Work.

    Args:
        work_id: The ID of the parent work
        content_type: Type of content (e.g., 'text', 'sound', 'notated_music')
        language: Language code (e.g., 'en', 'pl')
        meta: Additional metadata for the expression
        kind: FRBRoo expression kind (see :data:`app.db.core.EXPRESSION_KINDS`).
              ``None`` (default) means a studio/ordinary realization.  Use
              ``"live_performance"`` for concert recordings.
        raw_payload: Verbatim provider payload JSON

    Returns:
        The created Expression object

    Raises:
        ValueError: If *kind* is not in the controlled vocabulary.
    """
    if meta is None:
        meta = {}
    if kind is not None and kind not in EXPRESSION_KINDS:
        raise ValueError(f"Invalid expression kind {kind!r}; must be one of {EXPRESSION_KINDS}")
    expression = Expression(
        work_id=work_id,
        content_type=content_type,
        language=language,
        meta=meta,
        kind=kind,
        raw_payload=raw_payload,
    )
    db.session.add(expression)
    db.session.commit()
    return expression


def create_manifestation(  # pylint: disable=too-many-arguments,too-many-positional-arguments,redefined-builtin
    expression_id: int,
    isbn13: str | None = None,
    upc: str | None = None,
    ean: str | None = None,
    publisher: str | None = None,
    publication_date: Any | None = None,
    meta: dict[str, Any] | None = None,
    format: str | None = None,
    label: str | None = None,
    barcode: str | None = None,
    catalog_number: str | None = None,
    raw_payload: dict[str, Any] | None = None,
    format_type: str | None = None,
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
        format: Canonical format marker (e.g. 'dvd', 'bluray_audio')
        label: Publisher / record label name
        barcode: Generic barcode
        catalog_number: Catalog number
        raw_payload: Verbatim provider payload JSON
        format_type: Physical format type (e.g., 'hardcover', 'paperback', 'vinyl')

    Returns:
        The created Manifestation object
    """
    if meta is None:
        meta = {}
    else:
        meta = dict(meta)

    # Import shared validation utilities
    from app.core.f3_validation import (
        ISBNValidationError,
        extract_promoted_key_case_insensitive,
        normalize_isbn,
        validate_format_type,
        validate_publisher,
    )

    # Normalize ISBN using shared validation
    if isbn13 is None:
        cand_isbn = extract_promoted_key_case_insensitive(meta, "isbn13")
        if not cand_isbn:
            cand_isbn = extract_promoted_key_case_insensitive(meta, "isbn")
        if cand_isbn and isinstance(cand_isbn, str):
            try:
                isbn13 = normalize_isbn(cand_isbn)
            except ISBNValidationError:
                # Skip invalid ISBNs - they won't be stored
                isbn13 = None
    elif isbn13 and isinstance(isbn13, str):
        try:
            isbn13 = normalize_isbn(isbn13)
        except ISBNValidationError:
            isbn13 = None

    # Normalize publisher using shared validation
    if publisher is None:
        cand_pub = extract_promoted_key_case_insensitive(meta, "publisher")
        if cand_pub and isinstance(cand_pub, str):
            publisher = validate_publisher(cand_pub, strict=False)
    elif publisher and isinstance(publisher, str):
        publisher = validate_publisher(publisher, strict=False)

    # Normalize format_type using shared validation
    if format_type is None:
        cand_fmt = (
            extract_promoted_key_case_insensitive(meta, "format_type")
            or format
            or extract_promoted_key_case_insensitive(meta, "format")
            or extract_promoted_key_case_insensitive(meta, "video_format")
            or extract_promoted_key_case_insensitive(meta, "format_name")
        )
        if cand_fmt and isinstance(cand_fmt, str):
            format_type = validate_format_type(cand_fmt, strict=False)
    elif format_type and isinstance(format_type, str):
        format_type = validate_format_type(format_type, strict=False)

    if format is None:
        format = format_type or meta.get("format") or meta.get("video_format") or meta.get("format_name")
    if label is None:
        label = meta.get("label") or meta.get("studio") or meta.get("imprint") or publisher
    if barcode is None:
        barcode = meta.get("barcode") or meta.get("identifier") or ean or upc or isbn13
    if catalog_number is None:
        catalog_number = meta.get("catalog_number") or meta.get("catno") or meta.get("sku")

    # Prune promoted keys from metadata (case-insensitive)
    promoted_keys = ["isbn13", "isbn", "publisher", "format_type"]
    for key in promoted_keys:
        keys_to_remove = [k for k in meta.keys() if isinstance(k, str) and k.lower() == key.lower()]
        for k in keys_to_remove:
            del meta[k]

    manifestation = Manifestation(
        expression_id=expression_id,
        isbn13=isbn13,
        upc=upc,
        ean=ean,
        publisher=publisher,
        publication_date=publication_date,
        format_type=format_type,
        format=format,
        label=label,
        barcode=barcode,
        catalog_number=catalog_number,
        meta=meta,
        raw_payload=raw_payload,
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
    raw_payload: dict[str, Any] | None = None,
) -> Item:
    """
    Creates a new Item for a Manifestation.

    Args:
        manifestation_id: The ID of the parent manifestation
        owner_id: The ID of the owner
        status: Status of the item (e.g., 'available', 'lent', 'lost', 'wish_list')
        condition: Condition of the item
        meta: Additional metadata
        raw_payload: Verbatim provider payload JSON
    """
    if meta is None:
        meta = {}
    item = Item(
        manifestation_id=manifestation_id,
        owner_id=owner_id,
        status=status,
        condition=condition,
        meta=meta,
        raw_payload=raw_payload,
    )
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
    clean_isbn = isbn.replace("-", "").replace(" ", "").strip() if isbn else ""

    # Check if manifestation already exists
    manifestation: Manifestation | None = None
    if clean_isbn:
        manifestation = Manifestation.query.filter_by(isbn13=clean_isbn).first()  # type: ignore[assignment]
    if not manifestation and isbn:
        manifestation = Manifestation.query.filter_by(isbn13=isbn).first()  # type: ignore[assignment]

    if manifestation:
        # Update metadata if provided
        if publisher and not manifestation.publisher:
            manifestation.publisher = publisher.strip()[:255]
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

    manifestation = create_manifestation(
        expression_id=expression.id,
        isbn13=clean_isbn or isbn,
        publisher=publisher,
        format_type="book",
        meta=metadata,
    )

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


def add_manifestation_contribution(
    manifestation_id: int,
    contributor_id: int,
    role: str,
    sequence: int = 0,
) -> ManifestationContribution:
    """
    Link a contributor to a Manifestation with a publication role (Publication Event).

    Args:
        manifestation_id: ID of the parent :class:`~app.db.core.Manifestation`.
        contributor_id: ID of the :class:`~app.db.audio.Contributor`.
        role: Publication role (see :data:`~app.db.video.MANIFESTATION_VIDEO_ROLES`).
        sequence: Display order when multiple contributors share the same role.

    Returns:
        The created :class:`~app.db.video.ManifestationContribution`.
    """
    contribution = ManifestationContribution(
        manifestation_id=manifestation_id,
        contributor_id=contributor_id,
        role=role,
        sequence=sequence,
    )
    db.session.add(contribution)
    db.session.commit()
    return contribution


# ---------------------------------------------------------------------------
# FRBRoo F16 Container Work (board games)
# ---------------------------------------------------------------------------


def add_container_component(
    container_work_id: int,
    component_name: str,
    *,
    aggregated_work_id: int | None = None,
    aggregated_item_id: int | None = None,
    quantity: int = 1,
) -> "ContainerAggregation":
    """
    Add a component to an F16 Container Work (e.g., a board game box).

    Exactly one of ``aggregated_work_id`` (for abstract Works like a rulebook)
    or ``aggregated_item_id`` (for physical components like board/pieces) must
    be provided — enforced by the ``ck_container_aggregation_type_match``
    check constraint on the model.

    Args:
        container_work_id: ID of the container :class:`~app.db.core.Work` (the box).
        component_name: Human-readable label (e.g., ``"Rulebook"``, ``"Main Board"``).
        aggregated_work_id: Optional Work ID for an aggregated Work (rulebook).
        aggregated_item_id: Optional Item ID for an aggregated physical component.
        quantity: Number of these components in the box (default 1).

    Returns:
        The created :class:`~app.db.games.ContainerAggregation`.

    Raises:
        ValueError: If both or neither of the aggregated IDs are provided.
    """
    from app.db.games import ContainerAggregation

    if (aggregated_work_id is None) == (aggregated_item_id is None):
        raise ValueError(
            "Exactly one of aggregated_work_id (rulebook Work) or aggregated_item_id (physical component Item) must be provided."
        )

    if aggregated_work_id is not None:
        validate_work_not_expansion_aggregated(aggregated_work_id)

    aggregated_type = "work" if aggregated_work_id is not None else "item"
    agg = ContainerAggregation(
        container_work_id=container_work_id,
        aggregated_type=aggregated_type,
        aggregated_work_id=aggregated_work_id,
        aggregated_item_id=aggregated_item_id,
        component_name=component_name,
        quantity=quantity,
    )
    db.session.add(agg)
    db.session.commit()
    return agg


def link_expansion_to_base(
    base_work_id: int,
    expansion_work_id: int,
    link_type: str = WORK_LINK_TYPE_IS_EXPANSION_OF,
) -> WorkExpansionLink:
    """
    Reify an expansion relationship between two F1 Works.

    Creates a :class:`~app.db.core.WorkExpansionLink` row and enforces the
    SHACL constraint that an expansion Work must not be aggregated into an F16
    Container Work.

    Args:
        base_work_id: ID of the base game Work.
        expansion_work_id: ID of the expansion Work.
        link_type: Controlled link type (default ``is_expansion_of``).

    Returns:
        The created or existing :class:`~app.db.core.WorkExpansionLink`.

    Raises:
        ValueError: If *link_type* is unknown or the ontology guard fires.
    """
    if link_type not in WORK_LINK_TYPES:
        raise ValueError(f"Invalid work link type {link_type!r}; must be one of {WORK_LINK_TYPES}")

    validate_container_not_linked_as_expansion(expansion_work_id)
    validate_work_not_expansion_aggregated(expansion_work_id)

    existing: WorkExpansionLink | None = (
        WorkExpansionLink.query.filter_by(
            base_work_id=base_work_id,
            expansion_work_id=expansion_work_id,
            link_type=link_type,
        )
        .order_by(WorkExpansionLink.id.asc())
        .first()
    )
    if existing is not None:
        return existing

    link = WorkExpansionLink(
        base_work_id=base_work_id,
        expansion_work_id=expansion_work_id,
        link_type=link_type,
    )
    db.session.add(link)
    db.session.commit()
    return link


def get_or_create_rulebook_work(container_work: Work, title: str | None = None) -> Work:
    """
    Get or create the aggregated Rulebook Work inside an F16 Container.

    The rulebook is a sibling Work whose title is derived from the container
    (``"<container title> — Rulebook"``) unless explicitly overridden.  If a
    rulebook Work is already aggregated into the container, it is returned
    as-is (idempotent).

    Args:
        container_work: The container (box) :class:`~app.db.core.Work`.
        title: Optional explicit title for the rulebook Work.

    Returns:
        The rulebook :class:`~app.db.core.Work` (already linked via
        :class:`~app.db.games.ContainerAggregation` with
        ``aggregated_type='work'`` and ``component_name='Rulebook'``).
    """
    from app.db.games import ContainerAggregation

    # Look for an existing aggregated Work component named 'Rulebook'
    existing = (
        ContainerAggregation.query.filter_by(
            container_work_id=container_work.id,
            aggregated_type="work",
            component_name="Rulebook",
        )
        .order_by(ContainerAggregation.id.asc())
        .first()
    )
    if existing and existing.aggregated_work_id:
        return db.session.get(Work, existing.aggregated_work_id)  # type: ignore[return-value]

    rulebook_title = title or f"{container_work.title} — Rulebook"
    rulebook = create_work(title=rulebook_title, meta={"aggregated_into_work_id": container_work.id})
    add_container_component(
        container_work_id=container_work.id,
        component_name="Rulebook",
        aggregated_work_id=rulebook.id,
        quantity=1,
    )
    return rulebook


def serialize_container_aggregation(container_work: Work | None) -> dict[str, Any]:
    """
    Serialize an F16 Container Work's contents for API payloads.

    Returns a dict with two keys:

    - ``works``  — aggregated Works (e.g. Rulebook) with ``work_id``, ``title``, ``quantity``.
    - ``items``  — aggregated Items (physical components) with ``item_id``,
      ``component_name``, ``quantity``.

    Safe to call with ``None`` — returns empty buckets.
    """
    result: dict[str, Any] = {"works": [], "items": []}
    if container_work is None:
        return result

    for agg in getattr(container_work, "aggregates", None) or []:
        if agg.aggregated_type == "work" and agg.aggregated_work_id:
            work = db.session.get(Work, agg.aggregated_work_id)
            result["works"].append(
                {
                    "aggregation_id": agg.id,
                    "work_id": agg.aggregated_work_id,
                    "title": getattr(work, "title", None),
                    "component_name": agg.component_name,
                    "quantity": agg.quantity or 1,
                }
            )
        elif agg.aggregated_type == "item" and agg.aggregated_item_id:
            result["items"].append(
                {
                    "aggregation_id": agg.id,
                    "item_id": agg.aggregated_item_id,
                    "component_name": agg.component_name,
                    "quantity": agg.quantity or 1,
                }
            )
    return result


# --- UPDATE METHODS ---


def update_work(
    work_id: int,
    title: str | None = None,
    sort_title: str | None = None,
    meta: dict[str, Any] | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> Work:
    """
    Update an existing Work.

    Args:
        work_id: The ID of the work to update
        title: New title for the work
        sort_title: New alphabetical sort title
        meta: Metadata to merge with existing
        raw_payload: Verbatim provider payload JSON

    Returns:
        The updated Work object
    """
    work = db.session.get(Work, work_id)
    if work is None:
        raise ValueError(f"Work with id {work_id} not found")

    if title is not None:
        work.title = title
        if sort_title is None:
            work.sort_title = derive_sort_title(title)
    if sort_title is not None:
        work.sort_title = sort_title
    if raw_payload is not None:
        work.raw_payload = raw_payload
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
    kind: str | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> Expression:
    """
    Update an existing Expression.

    Args:
        expression_id: The ID of the expression to update
        work_id: New parent work ID
        content_type: New content type
        language: New language code
        meta: Metadata to merge with existing
        kind: New expression kind (``live_performance`` or ``None`` to clear
              via :func:`clear_expression_kind`).
        raw_payload: Verbatim provider payload JSON

    Returns:
        The updated Expression object

    Raises:
        ValueError: If the Expression/Work does not exist, or *kind* is not in
                    the controlled vocabulary.
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
        child_manifs = db.session.execute(select(Manifestation).where(Manifestation.expression_id == expr.id)).scalars().all()
        for m in child_manifs:
            m_meta = dict(m.meta or {})
            carrier = _sync_type_meta(m_meta, m.format, content_type)
            m.meta = m_meta
            if hasattr(m, "format"):
                m.format = carrier
    if language is not None:
        expr.language = language
    if kind is not None:
        if kind not in EXPRESSION_KINDS:
            raise ValueError(f"Invalid expression kind {kind!r}; must be one of {EXPRESSION_KINDS}")
        expr.kind = kind
    if raw_payload is not None:
        expr.raw_payload = raw_payload
    if meta is not None:
        current_meta = dict(expr.meta or {})
        current_meta.update(meta)
        expr.meta = current_meta
    db.session.commit()
    return expr


def clear_expression_kind(expression_id: int) -> Expression:
    """
    Reset an Expression's ``kind`` to ``None`` (studio/ordinary realization).

    Args:
        expression_id: The ID of the expression to reset.

    Returns:
        The updated Expression object.
    """
    expr = db.session.get(Expression, expression_id)
    if expr is None:
        raise ValueError(f"Expression with id {expression_id} not found")
    expr.kind = None
    db.session.commit()
    return expr


def is_live_performance(expression: Expression | None) -> bool:
    """Return ``True`` iff *expression* is typed as a live-performance Event."""
    return bool(expression is not None and expression.kind == EXPRESSION_KIND_LIVE_PERFORMANCE)


def serialize_contributions(
    work: Work | None = None,
    expression: Expression | None = None,
    manifestation: Manifestation | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Serialize FRBRoo event contributions for API payloads.

    Returns a dict with three keys, each an ordered list of contributor dicts
    (``name``, ``role``, ``sequence``, ``contributor_id``):

    - ``creators``   — Work-level Composition Event rows (``WorkContribution``).
    - ``performers`` — Expression-level Performance Event rows (``ExpressionContribution``).
    - ``publishers`` — Manifestation-level Publication Event rows (``ManifestationContribution``).

    Any entity left as ``None`` contributes an empty list to its bucket.  The
    serializer tolerates lazy-loaded relationships and missing backrefs so it
    is safe to call from any API surface.
    """
    creators: list[dict[str, Any]] = []
    performers: list[dict[str, Any]] = []
    publishers: list[dict[str, Any]] = []

    if work is not None:
        for wc in getattr(work, "contributions", None) or []:
            contributor = getattr(wc, "contributor", None)
            creators.append(
                {
                    "contributor_id": wc.contributor_id,
                    "name": getattr(contributor, "name", None),
                    "role": wc.role,
                    "sequence": wc.sequence or 0,
                }
            )
        creators.sort(key=lambda c: (c["role"], c["sequence"], c["name"] or ""))

    if expression is not None:
        for ec in getattr(expression, "contributions", None) or []:
            contributor = getattr(ec, "contributor", None)
            performers.append(
                {
                    "contributor_id": ec.contributor_id,
                    "name": getattr(contributor, "name", None),
                    "role": ec.role,
                    "sequence": ec.sequence or 0,
                }
            )
        performers.sort(key=lambda c: (c["role"], c["sequence"], c["name"] or ""))

    if manifestation is not None:
        for mc in getattr(manifestation, "contributions", None) or []:
            contributor = getattr(mc, "contributor", None)
            publishers.append(
                {
                    "contributor_id": mc.contributor_id,
                    "name": getattr(contributor, "name", None),
                    "role": mc.role,
                    "sequence": mc.sequence or 0,
                }
            )
        publishers.sort(key=lambda c: (c["role"], c["sequence"], c["name"] or ""))

    return {"creators": creators, "performers": performers, "publishers": publishers}


def get_or_create_live_performance_expression(
    work_id: int,
    content_type: str = "music",
    language: str = "en",
    venue: str | None = None,
    performance_date: Any | None = None,
    performers: list[tuple[str, str]] | None = None,
    meta: dict[str, Any] | None = None,
) -> Expression:
    """
    Get or create a Performance Event Expression for a live recording.

    Concerts are modeled as an Expression of the parent Work with
    ``kind='live_performance'``.  Performers, venue, and date are captured via
    :class:`ExpressionContribution` rows (Performance Event); venue/date land
    in the expression ``meta`` JSON when provided.

    Args:
        work_id: ID of the parent Work (e.g., the tour/album being performed).
        content_type: Typically ``"music"`` or ``"movie"`` (concert video).
        language: BCP-47 language tag.
        venue: Optional venue name, stored in ``meta['venue']``.
        performance_date: Optional date of the performance, stored ISO in
                          ``meta['performance_date']``.
        performers: Optional list of ``(name, role)`` tuples added as
                    :class:`ExpressionContribution` rows (e.g.,
                    ``[("Miles Davis Quintet", "band")]``).
        meta: Extra ``meta`` keys to merge.

    Returns:
        The existing or newly created Expression with
        ``kind='live_performance'``.
    """
    # Prefer reusing an existing live_performance Expression for the same Work
    # with the same venue/date when one already exists (idempotent).
    existing = (
        Expression.query.filter_by(work_id=work_id, kind=EXPRESSION_KIND_LIVE_PERFORMANCE, content_type=content_type)
        .order_by(Expression.id.asc())
        .first()
    )

    merged_meta: dict[str, Any] = dict(meta or {})
    if venue:
        merged_meta["venue"] = venue
    if performance_date:
        merged_meta["performance_date"] = performance_date.isoformat() if hasattr(performance_date, "isoformat") else str(performance_date)

    if existing is not None:
        # Merge any newly provided venue/date/meta into the existing row.
        if merged_meta:
            current = dict(existing.meta or {})
            current.update({k: v for k, v in merged_meta.items() if v is not None})
            existing.meta = current
            db.session.commit()
        expr = existing
    else:
        expr = create_expression(
            work_id=work_id,
            content_type=content_type,
            language=language,
            meta=merged_meta,
            kind=EXPRESSION_KIND_LIVE_PERFORMANCE,
        )

    for name, role in performers or []:
        contributor = get_or_create_contributor(name, contributor_type="person")
        if contributor is not None:
            already = ExpressionContribution.query.filter_by(expression_id=expr.id, contributor_id=contributor.id, role=role).first()
            if already is None:
                add_expression_contribution(expression_id=expr.id, contributor_id=contributor.id, role=role)

    return cast(Expression, expr)


def update_manifestation(  # pylint: disable=too-many-arguments,too-many-positional-arguments,redefined-builtin
    manifestation_id: int,
    expression_id: int | None = None,
    isbn13: str | None = None,
    upc: str | None = None,
    ean: str | None = None,
    publisher: str | None = None,
    publication_date: Any | None = None,
    meta: dict[str, Any] | None = None,
    format: str | None = None,
    label: str | None = None,
    barcode: str | None = None,
    catalog_number: str | None = None,
    raw_payload: dict[str, Any] | None = None,
    format_type: str | None = None,
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
        format: New canonical format
        label: New label
        barcode: New barcode
        catalog_number: New catalog number
        raw_payload: Verbatim provider payload JSON
        format_type: New physical format type (e.g., 'hardcover', 'paperback', 'vinyl')

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
        manif.isbn13 = isbn13.replace("-", "").replace(" ", "").strip() if isbn13 else None
    if upc is not None:
        manif.upc = upc
    if ean is not None:
        manif.ean = ean
    if publisher is not None:
        manif.publisher = publisher.strip()[:255] if publisher else None
    if publication_date is not None:
        manif.publication_date = publication_date
    if format_type is not None:
        manif.format_type = format_type.strip().lower()[:50] if format_type else None
    if format is not None:
        manif.format = format
        if manif.format_type is None and format:
            manif.format_type = format.strip().lower()[:50]
        current_meta = dict(manif.meta or {})
        current_meta["format"] = format
        current_meta["Format"] = format
        current_meta["type"] = format
        manif.meta = current_meta
        if manif.expression:
            category = FORMAT_TO_CATEGORY.get(format) or FORMAT_ALIAS_TO_CATEGORY.get(format) or format
            manif.expression.content_type = category
            if manif.expression.work:
                w_meta = dict(manif.expression.work.meta or {})
                w_meta["type"] = category
                w_meta["format"] = category
                w_meta["Format"] = category
                manif.expression.work.meta = w_meta
    if label is not None:
        manif.label = label
    if barcode is not None:
        manif.barcode = barcode
    if catalog_number is not None:
        manif.catalog_number = catalog_number
    if raw_payload is not None:
        manif.raw_payload = raw_payload
    if meta is not None:
        current_meta = dict(manif.meta or {})
        current_meta.update(meta)
        new_type = meta.get("type") or meta.get("format") or meta.get("Format")
        if new_type:
            current_meta["type"] = new_type
            current_meta["format"] = new_type
            current_meta["Format"] = new_type
            manif.format = new_type
            if manif.format_type is None:
                manif.format_type = new_type.strip().lower()[:50]
            if manif.expression:
                category = FORMAT_TO_CATEGORY.get(new_type) or FORMAT_ALIAS_TO_CATEGORY.get(new_type) or new_type
                manif.expression.content_type = category
                if manif.expression.work:
                    w_meta = dict(manif.expression.work.meta or {})
                    w_meta["type"] = category
                    w_meta["format"] = category
                    w_meta["Format"] = category
                    manif.expression.work.meta = w_meta

        if "format_type" in meta and format_type is None and meta["format_type"]:
            manif.format_type = str(meta["format_type"]).strip().lower()[:50]
        if ("publisher" in meta or "Publisher" in meta) and publisher is None:
            cand_pub = meta.get("publisher") or meta.get("Publisher")
            if cand_pub:
                manif.publisher = str(cand_pub).strip()[:255]
        if ("isbn13" in meta or "isbn" in meta) and isbn13 is None:
            cand_isbn = meta.get("isbn13") or meta.get("isbn")
            if cand_isbn:
                manif.isbn13 = str(cand_isbn).replace("-", "").replace(" ", "").strip()

        for k in ("isbn13", "isbn", "publisher", "Publisher", "format_type"):
            current_meta.pop(k, None)

        manif.meta = current_meta
    else:
        if manif.meta:
            current_meta = dict(manif.meta)
            has_promoted = any(k in current_meta for k in ("isbn13", "isbn", "publisher", "Publisher", "format_type"))
            if has_promoted:
                for k in ("isbn13", "isbn", "publisher", "Publisher", "format_type"):
                    current_meta.pop(k, None)
                manif.meta = current_meta

    db.session.commit()
    return manif


def update_item(
    item_id: int,
    manifestation_id: int | None = None,
    status: str | None = None,
    condition: str | None = None,
    meta: dict[str, Any] | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> Item:
    """
    Update an existing Item.

    Args:
        item_id: The ID of the item to update
        manifestation_id: New parent manifestation ID
        status: New status
        condition: New condition
        meta: Metadata to merge with existing
        raw_payload: Verbatim provider payload JSON

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
    if raw_payload is not None:
        item.raw_payload = raw_payload
    if meta is not None:
        current_meta = dict(item.meta or {})
        current_meta.update(meta)
        item.meta = current_meta
    db.session.commit()
    return item


#: Media category → its canonical ``unknown_*`` placeholder format,
#: derived from the taxonomy so it stays in sync automatically.
_CATEGORY_TO_UNKNOWN_FORMAT = {category: fmt for fmt, category in FORMAT_TO_CATEGORY.items() if fmt.startswith("unknown_")}


def _resolve_carrier_format(current_format: Any, new_type: str) -> str:
    """
    Resolve the carrier format to store after a content-type change.

    A real carrier (e.g. ``bluray``, ``vinyl``) whose category matches the new
    type is preserved. A carrier from another category (the type genuinely
    changed category) or a type-like/empty value degrades to the category's
    ``unknown_*`` placeholder instead of clobbering the carrier with the
    content type itself.

    Args:
        current_format: The format currently stored (column or meta value).
        new_type: The new content type being applied (e.g. ``movie``, ``music``).

    Returns:
        The carrier format to persist.
    """
    new_category = FORMAT_ALIAS_TO_CATEGORY.get(new_type.strip().lower())
    current = str(current_format or "").strip().lower()
    if current in FORMAT_TO_CATEGORY and (new_category is None or FORMAT_TO_CATEGORY[current] == new_category):
        return current
    if new_category:
        unknown = _CATEGORY_TO_UNKNOWN_FORMAT.get(new_category)
        if unknown:
            return unknown
    return current or new_type


def _sync_type_meta(meta: dict[str, Any], current_format: Any, new_type: str) -> str:
    """
    Sync a type change into an entity meta dict, preserving the carrier format.

    Sets ``type`` to the resolved carrier and resolves ``format``/``Format``
    via :func:`_resolve_carrier_format`.

    Args:
        meta: The entity meta dict to mutate.
        current_format: The authoritative current carrier (e.g. the format column).
        new_type: The new content type.

    Returns:
        The resolved carrier format.
    """
    carrier = _resolve_carrier_format(current_format or meta.get("format") or meta.get("Format"), new_type)
    meta["type"] = new_type
    meta["format"] = carrier
    meta["Format"] = carrier
    return carrier


def update_frbr_entity_type(
    entity_class: Any,
    entity_id: int,
    new_type: str,
) -> Any:
    """
    Update the type of a FRBR entity and adapt parent/child entities to maintain consistency.

    Carrier formats (``bluray``, ``vinyl`` …) on Manifestations are preserved
    when they stay valid for the new type; only invalid or type-like format
    values degrade to the category's ``unknown_*`` placeholder.
    """
    entity = db.session.get(entity_class, entity_id)
    if not entity:
        raise ValueError(f"{entity_class.__name__} with id {entity_id} not found")

    if hasattr(entity, "meta"):
        current_meta = dict(entity.meta or {})
        carrier = _sync_type_meta(
            current_meta,
            entity.format if hasattr(entity, "format") else None,
            new_type,
        )
        entity.meta = current_meta
        if hasattr(entity, "format"):
            entity.format = carrier

    if entity_class == Manifestation:
        if entity.expression:
            entity.expression.content_type = new_type
            if entity.expression.work:
                w_meta = dict(entity.expression.work.meta or {})
                w_meta["type"] = new_type
                w_meta["format"] = new_type
                w_meta["Format"] = new_type
                entity.expression.work.meta = w_meta
    elif entity_class == Expression:
        entity.content_type = new_type
        if entity.work:
            w_meta = dict(entity.work.meta or {})
            w_meta["type"] = new_type
            w_meta["format"] = new_type
            w_meta["Format"] = new_type
            entity.work.meta = w_meta
        child_manifs = db.session.execute(select(Manifestation).where(Manifestation.expression_id == entity.id)).scalars().all()
        for m in child_manifs:
            m_meta = dict(m.meta or {})
            carrier = _sync_type_meta(m_meta, m.format, new_type)
            m.meta = m_meta
            if hasattr(m, "format"):
                m.format = carrier
    elif entity_class == Work:
        w_meta = dict(entity.meta or {})
        w_meta["type"] = new_type
        w_meta["format"] = new_type
        w_meta["Format"] = new_type
        entity.meta = w_meta
        child_exprs = db.session.execute(select(Expression).where(Expression.work_id == entity.id)).scalars().all()
        for sub_expr in child_exprs:
            sub_expr.content_type = new_type
            sub_manifs = db.session.execute(select(Manifestation).where(Manifestation.expression_id == sub_expr.id)).scalars().all()
            for m in sub_manifs:
                m_meta = dict(m.meta or {})
                carrier = _sync_type_meta(m_meta, m.format, new_type)
                m.meta = m_meta
                if hasattr(m, "format"):
                    m.format = carrier

    db.session.commit()
    return entity


# Define Namespaces
FRBR = Namespace("http://iflastandards.info/ns/frbr/frbrer/")
SIOC = Namespace("http://rdfs.org/sioc/ns#")
SCHEMA = Namespace("https://schema.org/")
PROV = Namespace("http://www.w3.org/ns/prov#")

# Schema.org type mapping for content types
SCHEMA_TYPE_MAP = {
    "text": SCHEMA.Book,
    "audiobook": SCHEMA.Audiobook,
    "music": SCHEMA.MusicAlbum,
    "movie": SCHEMA.Movie,
    "board_game": SCHEMA.Game,
    "puzzle": SCHEMA.Product,
    "concert": SCHEMA.MusicEvent,
}


def _add_provenance_triples(
    g: Graph,
    m_uri: URIRef,
    meta: dict[str, Any],
    raw_payload: dict[str, Any] | None = None,
    isbn: str | None = None,
) -> None:
    """Extract external provenance and attach prov:wasDerivedFrom."""
    prov_url = meta.get("source_url") or meta.get("provenance_url") or meta.get("was_derived_from") or meta.get("provenance")
    if prov_url and str(prov_url).startswith(("http://", "https://")):
        g.add((m_uri, PROV.wasDerivedFrom, URIRef(str(prov_url))))
        return

    source = meta.get("data_source") or meta.get("source") or meta.get("provider")
    if not source and raw_payload:
        source = raw_payload.get("source") or raw_payload.get("data_source")

    if not source:
        return

    source_str = str(source).lower()
    if source_str.startswith(("http://", "https://")):
        g.add((m_uri, PROV.wasDerivedFrom, URIRef(str(source))))
    elif "openlibrary" in source_str or "open_library" in source_str:
        olid = meta.get("openlibrary_id") or meta.get("olid")
        if olid:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef(f"https://openlibrary.org/books/{olid}")))
        elif isbn:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef(f"https://openlibrary.org/isbn/{isbn}")))
        else:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef("https://openlibrary.org")))
    elif "musicbrainz" in source_str:
        mbid = meta.get("musicbrainz_id") or meta.get("mbid")
        if mbid:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef(f"https://musicbrainz.org/release/{mbid}")))
        else:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef("https://musicbrainz.org")))
    elif "bgg" in source_str or "boardgamegeek" in source_str:
        bgg_id = meta.get("bgg_id") or meta.get("boardgamegeek_id")
        if bgg_id:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef(f"https://boardgamegeek.com/boardgame/{bgg_id}")))
        else:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef("https://boardgamegeek.com")))
    elif "allegro" in source_str:
        allegro_url = meta.get("allegro_url")
        if allegro_url:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef(str(allegro_url))))
        else:
            g.add((m_uri, PROV.wasDerivedFrom, URIRef("https://allegro.pl")))


def _enrich_dict_item(g: Graph, item: dict[str, Any], base_url: str) -> None:
    """Enrich graph with relational and provenance metadata from a plain dictionary item."""
    item_id = item.get("id")
    m_id = item.get("manifestation_id", item_id)
    w_id = item.get("work_id", m_id)
    m_uri = URIRef(f"{base_url}/api/public/manifestations/{m_id}")
    w_uri = URIRef(f"{base_url}/api/public/works/{w_id}")

    if item.get("publisher"):
        g.add((m_uri, SCHEMA.publisher, Literal(str(item["publisher"]))))
    if item.get("language"):
        g.add((m_uri, SCHEMA.inLanguage, Literal(str(item["language"]))))
    pub_date = item.get("publication_date") or item.get("date_published") or item.get("year")
    if pub_date:
        g.add((m_uri, SCHEMA.datePublished, Literal(str(pub_date))))

    cover = item.get("cover_url") or item.get("image")
    if cover:
        img_uri = URIRef(str(cover) if str(cover).startswith(("http://", "https://")) else f"{base_url}/{str(cover).lstrip('/')}")
        g.add((m_uri, SCHEMA.image, img_uri))

    for c in item.get("contributors", []):
        if isinstance(c, dict):
            c_name = c.get("name")
            c_type = c.get("type", "person")
            c_id = c.get("id", c_name)
            c_uri = URIRef(f"{base_url}/api/public/contributors/{c_id}")
            g.add((c_uri, RDF.type, SCHEMA.Person if c_type == "person" else SCHEMA.Organization))
            if c_name:
                g.add((c_uri, SCHEMA.name, Literal(c_name)))
            g.add((m_uri, SCHEMA.contributor, c_uri))
        elif isinstance(c, str):
            c_uri = URIRef(f"{base_url}/api/public/contributors/{c}")
            g.add((c_uri, RDF.type, SCHEMA.Person))
            g.add((c_uri, SCHEMA.name, Literal(c)))
            g.add((m_uri, SCHEMA.contributor, c_uri))

    _add_provenance_triples(g, m_uri, item, isbn=item.get("isbn"))

    is_part_of = item.get("is_part_of") or item.get("container_work_id")
    if is_part_of:
        p_uri = URIRef(str(is_part_of) if str(is_part_of).startswith("http") else f"{base_url}/api/public/works/{is_part_of}")
        g.add((w_uri, SCHEMA.isPartOf, p_uri))
        g.add((p_uri, SCHEMA.hasPart, w_uri))

    has_part = item.get("has_part")
    if has_part:
        p_list = has_part if isinstance(has_part, list) else [has_part]
        for p in p_list:
            p_uri = URIRef(str(p) if str(p).startswith("http") else f"{base_url}/api/public/works/{p}")
            g.add((w_uri, SCHEMA.hasPart, p_uri))
            g.add((p_uri, SCHEMA.isPartOf, w_uri))


def _enrich_graph_from_db(
    g: Graph,
    items: list[Any],
    base_url: str,
    collection_uri: str | URIRef | None = None,
    enrichment_profile: str = "public",
) -> None:
    """Add contributor, WorkPart, ImageScan, provenance, and UserCollection triples from DB.

    Args:
        g: The RDF graph to enrich.
        items: List of items to enrich.
        base_url: Base URL for generating URIs.
        collection_uri: Optional collection URI for hasPart/isPartOf relationships.
        enrichment_profile: "public" for public-safe enrichment (excludes private data),
                           "full" for authenticated export (includes all data).
    """
    if collection_uri:
        coll_uri_ref = URIRef(str(collection_uri))
        g.add((coll_uri_ref, RDF.type, SCHEMA.Collection))
        for item in items:
            if isinstance(item, dict):
                m_id = item.get("manifestation_id") or item.get("id")
                i_id = item.get("id")
            else:
                if hasattr(item, "manifestation_id"):
                    m_id = item.manifestation_id
                    i_id = getattr(item, "id", None)
                elif hasattr(item, "expression_id"):
                    m_id = getattr(item, "id", None)
                    i_id = None
                else:
                    m_id = None
                    i_id = None

            if m_id:
                m_uri = URIRef(f"{base_url}/api/public/manifestations/{m_id}")
                g.add((coll_uri_ref, SCHEMA.hasPart, m_uri))
                g.add((m_uri, SCHEMA.isPartOf, coll_uri_ref))
            if i_id and i_id != m_id:
                i_uri = URIRef(f"{base_url}/api/public/items/{i_id}")
                g.add((coll_uri_ref, SCHEMA.hasPart, i_uri))
                g.add((i_uri, SCHEMA.isPartOf, coll_uri_ref))

    for item in items:
        if isinstance(item, dict):
            _enrich_dict_item(g, item, base_url)

    seen_works: set[int] = set()
    seen_expressions: set[int] = set()
    seen_manifestations: set[int] = set()
    seen_items: set[int] = set()

    for item in items:
        if isinstance(item, dict):
            continue  # Handled above via _enrich_dict_item

        # Resolve IDs from ORM objects
        if hasattr(item, "manifestation_id") and hasattr(item, "manifestation"):
            # Item object
            db_item = item
            seen_items.add(db_item.id)
            m = db_item.manifestation
            if not m:
                continue
            seen_manifestations.add(m.id)
            if m.expression:
                seen_expressions.add(m.expression.id)
                if m.expression.work:
                    seen_works.add(m.expression.work.id)
        elif hasattr(item, "expression_id"):
            # Manifestation object
            m = item
            seen_manifestations.add(m.id)
            if hasattr(m, "expression") and m.expression:
                seen_expressions.add(m.expression.id)
                if m.expression.work:
                    seen_works.add(m.expression.work.id)
        elif hasattr(item, "work_id"):
            # Expression object
            seen_expressions.add(item.id)
            if item.work_id:
                seen_works.add(item.work_id)
        elif hasattr(item, "expressions") or isinstance(item, Work):
            # Work object
            seen_works.add(item.id)

    try:
        # WorkContributions
        if seen_works:
            contribs = db.session.execute(select(WorkContribution).where(WorkContribution.work_id.in_(seen_works))).scalars().all()
            for wc in contribs:
                w_uri = URIRef(f"{base_url}/api/public/works/{wc.work_id}")
                c_uri = URIRef(f"{base_url}/api/public/contributors/{wc.contributor_id}")
                g.add((c_uri, RDF.type, SCHEMA.Person if wc.contributor and wc.contributor.type == "person" else SCHEMA.Organization))
                if wc.contributor:
                    g.add((c_uri, SCHEMA.name, Literal(wc.contributor.name)))
                g.add((w_uri, SCHEMA.contributor, c_uri))
                g.add((w_uri, FRBR.creator, c_uri))

        # ExpressionContributions
        if seen_expressions:
            expr_contribs = (
                db.session.execute(select(ExpressionContribution).where(ExpressionContribution.expression_id.in_(seen_expressions)))
                .scalars()
                .all()
            )
            for ec in expr_contribs:
                e_uri = URIRef(f"{base_url}/api/public/expressions/{ec.expression_id}")
                c_uri = URIRef(f"{base_url}/api/public/contributors/{ec.contributor_id}")
                g.add((c_uri, RDF.type, SCHEMA.Person if ec.contributor and ec.contributor.type == "person" else SCHEMA.Organization))
                if ec.contributor:
                    g.add((c_uri, SCHEMA.name, Literal(ec.contributor.name)))
                g.add((e_uri, SCHEMA.contributor, c_uri))

        # ManifestationContributions
        if seen_manifestations:
            m_contribs = (
                db.session.execute(
                    select(ManifestationContribution).where(ManifestationContribution.manifestation_id.in_(seen_manifestations))
                )
                .scalars()
                .all()
            )
            for mc in m_contribs:
                m_uri = URIRef(f"{base_url}/api/public/manifestations/{mc.manifestation_id}")
                c_uri = URIRef(f"{base_url}/api/public/contributors/{mc.contributor_id}")
                g.add((c_uri, RDF.type, SCHEMA.Person if mc.contributor and mc.contributor.type == "person" else SCHEMA.Organization))
                if mc.contributor:
                    g.add((c_uri, SCHEMA.name, Literal(mc.contributor.name)))
                g.add((m_uri, SCHEMA.contributor, c_uri))

        # WorkParts (container aggregation)
        if seen_works:
            parts = db.session.execute(select(WorkPart).where(WorkPart.container_work_id.in_(seen_works))).scalars().all()
            for wp in parts:
                container_uri = URIRef(f"{base_url}/api/public/works/{wp.container_work_id}")
                part_uri = URIRef(f"{base_url}/api/public/works/{wp.part_work_id}")
                g.add((part_uri, SCHEMA.isPartOf, container_uri))
                g.add((container_uri, SCHEMA.hasPart, part_uri))

        # ImageScans - only include in full profile (authenticated exports)
        if enrichment_profile == "full" and seen_manifestations:
            scans = db.session.execute(select(ImageScan).where(ImageScan.manifestation_id.in_(seen_manifestations))).scalars().all()
            for scan in scans:
                m_uri = URIRef(f"{base_url}/api/public/manifestations/{scan.manifestation_id}")
                img_uri = URIRef(f"{base_url}/{scan.file_path}")
                g.add((m_uri, SCHEMA.image, img_uri))

        # UserCollections - only include in full profile (authenticated exports)
        # Private collection names should not be exposed in public RDF
        if enrichment_profile == "full" and seen_items:
            links = db.session.execute(select(UserCollectionItem).where(UserCollectionItem.item_id.in_(seen_items))).scalars().all()
            for link in links:
                coll = link.collection
                if coll:
                    coll_uri = URIRef(f"{base_url}/api/public/collections/{coll.id}")
                    i_uri = URIRef(f"{base_url}/api/public/items/{link.item_id}")
                    g.add((coll_uri, RDF.type, SCHEMA.Collection))
                    g.add((coll_uri, SCHEMA.name, Literal(coll.name)))
                    g.add((coll_uri, SCHEMA.hasPart, i_uri))
                    g.add((i_uri, SCHEMA.isPartOf, coll_uri))

        # Manifestations enrichment: publisher, datePublished, image, prov:wasDerivedFrom
        if seen_manifestations:
            manifests = db.session.execute(select(Manifestation).where(Manifestation.id.in_(seen_manifestations))).scalars().all()
            for m in manifests:
                m_uri = URIRef(f"{base_url}/api/public/manifestations/{m.id}")
                if m.publisher:
                    g.add((m_uri, SCHEMA.publisher, Literal(m.publisher)))
                pub_date = (
                    getattr(m, "publication_date", None)
                    or (m.meta.get("publication_date") if m.meta else None)
                    or (m.meta.get("year") if m.meta else None)
                )
                if pub_date:
                    g.add((m_uri, SCHEMA.datePublished, Literal(str(pub_date))))
                cover = getattr(m, "cover_url", None) or (m.meta.get("cover_url") if m.meta else None)
                if cover:
                    img_uri = URIRef(cover if str(cover).startswith(("http://", "https://")) else f"{base_url}/{str(cover).lstrip('/')}")
                    g.add((m_uri, SCHEMA.image, img_uri))

                _add_provenance_triples(g, m_uri, m.meta or {}, getattr(m, "raw_payload", None), getattr(m, "isbn13", None))

        # Expressions enrichment: inLanguage
        if seen_expressions:
            exprs = db.session.execute(select(Expression).where(Expression.id.in_(seen_expressions))).scalars().all()
            for expr in exprs:
                if getattr(expr, "language", None):
                    for m in getattr(expr, "manifestations", []):
                        m_uri = URIRef(f"{base_url}/api/public/manifestations/{m.id}")
                        g.add((m_uri, SCHEMA.inLanguage, Literal(expr.language)))
    except (SQLAlchemyError, AttributeError, KeyError):
        pass


def build_collection_rdf_graph(
    items: list[Any],
    base_url: str,
    collection_uri: str | URIRef | None = None,
    enrichment_profile: str = "public",
) -> Graph:
    """
    Build an in-memory RDF Graph for a list of collection items/manifestations
    supporting FRBRer, SIOC (for tags), and Schema.org profiles.

    Args:
        items: List of items to serialize.
        base_url: Base URL for generating URIs.
        collection_uri: Optional collection URI for hasPart/isPartOf relationships.
        enrichment_profile: "public" for public-safe enrichment (excludes private data),
                           "full" for authenticated export (includes all data).
    """
    g = Graph()
    g.bind("frbr", FRBR)
    g.bind("sioc", SIOC)
    g.bind("schema", SCHEMA)
    g.bind("prov", PROV)

    for item in items:
        # Resolve whether dict or db object
        if isinstance(item, dict):
            item_id = item.get("id")
            manifestation_id = item.get("manifestation_id", item_id)
            expression_id = item.get("expression_id", manifestation_id)
            title = item.get("title", "Untitled")
            isbn = item.get("isbn")
            authors = item.get("authors", [])
            tags = item.get("tags", [])
            status = item.get("status")
            work_id = item.get("work_id", manifestation_id)
            content_type = item.get("content_type")
            publisher = item.get("publisher")
            language = item.get("language")
            publication_date = item.get("publication_date") or item.get("date_published") or item.get("year")
            cover_url = item.get("cover_url") or item.get("image")
        else:
            item_id = getattr(item, "id", None)
            if hasattr(item, "manifestation_id"):
                # Database Item object
                manifestation_id = item.manifestation_id
                expression_id = None
                work_id = None
                title = "Untitled"
                isbn = None
                authors = []
                tags = []
                status = getattr(item, "status", None)
                content_type = None
                publisher = None
                language = None
                publication_date = None
                cover_url = None

                m = item.manifestation
                if m:
                    manifestation_id = m.id
                    expression_id = m.expression_id
                    title = getattr(m, "title", "Untitled") or "Untitled"
                    isbn = m.isbn13
                    publisher = getattr(m, "publisher", None)
                    publication_date = (
                        getattr(m, "publication_date", None)
                        or (m.meta.get("publication_date") if m.meta else None)
                        or (m.meta.get("year") if m.meta else None)
                    )
                    cover_url = getattr(m, "cover_url", None) or (m.meta.get("cover_url") if m.meta else None)
                    if m.expression:
                        expression_id = m.expression.id
                        work_id = m.expression.work_id
                        content_type = m.expression.content_type
                        language = getattr(m.expression, "language", None)
                        if m.expression.work:
                            work_id = m.expression.work.id
                            title = m.expression.work.title or title
                            if m.expression.work.meta:
                                authors = m.expression.work.meta.get("authors", []) or m.expression.work.meta.get("Authors", [])
                        if not authors and m.meta:
                            authors = m.meta.get("authors", []) or m.meta.get("Authors", [])
                        if m.expression.meta:
                            tags = m.expression.meta.get("tags", []) or m.expression.meta.get("Tags", [])
                    elif m.meta:
                        authors = m.meta.get("authors", []) or m.meta.get("Authors", [])

                if expression_id is None:
                    expression_id = item_id
                if work_id is None:
                    work_id = expression_id
            elif hasattr(item, "work_id"):
                # Database Expression object
                expression_id = item.id
                work_id = item.work_id
                content_type = getattr(item, "content_type", None)
                w_title = getattr(item.work, "title", "Untitled") if getattr(item, "work", None) else "Untitled"
                authors = []
                if getattr(item, "work", None) and item.work.meta:
                    authors = item.work.meta.get("authors", []) or item.work.meta.get("Authors", [])

                w_uri = URIRef(f"{base_url}/api/public/works/{work_id}")
                e_uri = URIRef(f"{base_url}/api/public/expressions/{expression_id}")
                g.add((w_uri, RDF.type, FRBR.Work))
                g.add((w_uri, RDF.type, SCHEMA.CreativeWork))
                g.add((w_uri, SCHEMA.name, Literal(w_title)))
                for author in authors:
                    g.add((w_uri, FRBR.creator, Literal(author)))
                    g.add((w_uri, SCHEMA.author, Literal(author)))
                g.add((e_uri, RDF.type, FRBR.Expression))
                g.add((e_uri, FRBR.expressionOf, w_uri))

                for m_elem in getattr(item, "manifestations", []):
                    m_uri = URIRef(f"{base_url}/api/public/manifestations/{m_elem.id}")
                    g.add((m_uri, RDF.type, FRBR.Manifestation))
                    g.add((m_uri, RDF.type, SCHEMA.CreativeWork))
                    g.add((m_uri, FRBR.embodimentOf, e_uri))
                    if m_elem.title:
                        g.add((m_uri, SCHEMA.name, Literal(m_elem.title)))
                    if m_elem.isbn13:
                        g.add((m_uri, SCHEMA.isbn, Literal(m_elem.isbn13)))
                    if m_elem.cover_url:
                        img_uri = URIRef(
                            str(m_elem.cover_url)
                            if str(m_elem.cover_url).startswith(("http://", "https://"))
                            else f"{base_url}/{str(m_elem.cover_url).lstrip('/')}"
                        )
                        g.add((m_uri, SCHEMA.image, img_uri))
                continue
            elif hasattr(item, "expressions") or isinstance(item, Work):
                # Database Work object
                work_id = item.id
                title = getattr(item, "title", "Untitled") or "Untitled"
                authors = []
                if getattr(item, "meta", None):
                    authors = item.meta.get("authors", []) or item.meta.get("Authors", [])

                w_uri = URIRef(f"{base_url}/api/public/works/{work_id}")
                g.add((w_uri, RDF.type, FRBR.Work))
                g.add((w_uri, RDF.type, SCHEMA.CreativeWork))
                g.add((w_uri, SCHEMA.name, Literal(title)))
                for author in authors:
                    g.add((w_uri, FRBR.creator, Literal(author)))
                    g.add((w_uri, SCHEMA.author, Literal(author)))

                for expr_elem in getattr(item, "expressions", []):
                    e_uri = URIRef(f"{base_url}/api/public/expressions/{expr_elem.id}")
                    g.add((e_uri, RDF.type, FRBR.Expression))
                    g.add((e_uri, FRBR.expressionOf, w_uri))
                    for m_elem in getattr(expr_elem, "manifestations", []):
                        m_uri = URIRef(f"{base_url}/api/public/manifestations/{m_elem.id}")
                        g.add((m_uri, RDF.type, FRBR.Manifestation))
                        g.add((m_uri, RDF.type, SCHEMA.CreativeWork))
                        g.add((m_uri, FRBR.embodimentOf, e_uri))
                        if m_elem.title:
                            g.add((m_uri, SCHEMA.name, Literal(m_elem.title)))
                        if m_elem.isbn13:
                            g.add((m_uri, SCHEMA.isbn, Literal(m_elem.isbn13)))
                        if m_elem.cover_url:
                            img_uri = URIRef(
                                str(m_elem.cover_url)
                                if str(m_elem.cover_url).startswith(("http://", "https://"))
                                else f"{base_url}/{str(m_elem.cover_url).lstrip('/')}"
                            )
                            g.add((m_uri, SCHEMA.image, img_uri))
                continue
            else:
                # Database Manifestation object
                manifestation_id = item_id
                expression_id = getattr(item, "expression_id", None)
                work_id = None
                title = getattr(item, "title", "Untitled") or "Untitled"
                isbn = getattr(item, "isbn13", None)
                authors = []
                tags = []
                status = getattr(item, "status", None)
                content_type = None
                publisher = getattr(item, "publisher", None)
                language = None
                publication_date = (
                    getattr(item, "publication_date", None)
                    or (item.meta.get("publication_date") if getattr(item, "meta", None) else None)
                    or (item.meta.get("year") if getattr(item, "meta", None) else None)
                )
                cover_url = getattr(item, "cover_url", None) or (item.meta.get("cover_url") if getattr(item, "meta", None) else None)

                if hasattr(item, "expression") and item.expression:
                    expr = item.expression
                    expression_id = expr.id
                    work_id = expr.work_id
                    content_type = expr.content_type
                    language = getattr(expr, "language", None)
                    if expr.work:
                        work_id = expr.work.id
                        title = expr.work.title or title
                        if expr.work.meta:
                            authors = expr.work.meta.get("authors", []) or expr.work.meta.get("Authors", [])
                    if not authors and getattr(item, "meta", None):
                        authors = item.meta.get("authors", []) or item.meta.get("Authors", [])
                    if expr.meta:
                        tags = expr.meta.get("tags", []) or expr.meta.get("Tags", [])
                elif getattr(item, "meta", None):
                    authors = item.meta.get("authors", []) or item.meta.get("Authors", [])

                if expression_id is None:
                    expression_id = item_id
                if work_id is None:
                    work_id = expression_id

        m_uri = URIRef(f"{base_url}/api/public/manifestations/{manifestation_id}")
        e_uri = URIRef(f"{base_url}/api/public/expressions/{expression_id}")
        w_uri = URIRef(f"{base_url}/api/public/works/{work_id}")

        # FRBR Core Declarations
        g.add((m_uri, RDF.type, FRBR.Manifestation))
        g.add((e_uri, RDF.type, FRBR.Expression))
        g.add((w_uri, RDF.type, FRBR.Work))

        # Manifestation embodies Expression, Expression is expression of Work
        g.add((m_uri, FRBR.embodimentOf, e_uri))
        g.add((e_uri, FRBR.expressionOf, w_uri))

        # High-level Schema.org Mapping for AI Agent Interoperability
        g.add((m_uri, RDF.type, SCHEMA.CreativeWork))
        g.add((m_uri, SCHEMA.name, Literal(title)))

        g.add((w_uri, RDF.type, SCHEMA.CreativeWork))
        g.add((w_uri, SCHEMA.name, Literal(title)))

        # Add specific Schema.org type based on content_type
        specific_type = SCHEMA_TYPE_MAP.get(content_type) if content_type else None
        if specific_type:
            g.add((m_uri, RDF.type, specific_type))

        if isbn:
            g.add((m_uri, SCHEMA.isbn, Literal(isbn)))

        if publisher:
            g.add((m_uri, SCHEMA.publisher, Literal(publisher)))

        if language:
            g.add((m_uri, SCHEMA.inLanguage, Literal(language)))

        if publication_date:
            g.add((m_uri, SCHEMA.datePublished, Literal(str(publication_date))))

        if cover_url:
            img_uri = URIRef(
                str(cover_url) if str(cover_url).startswith(("http://", "https://")) else f"{base_url}/{str(cover_url).lstrip('/')}"
            )
            g.add((m_uri, SCHEMA.image, img_uri))

        for author in authors:
            g.add((m_uri, SCHEMA.author, Literal(author)))
            g.add((w_uri, FRBR.creator, Literal(author)))
            g.add((w_uri, SCHEMA.author, Literal(author)))

        # SIOC Semantics for Tagging / Folksonomy categorization
        for tag in tags:
            g.add((m_uri, SIOC.topic, Literal(tag)))

        # Handle specific item tracking if item instances exist
        if item_id:
            i_uri = URIRef(f"{base_url}/api/public/items/{item_id}")
            g.add((i_uri, RDF.type, FRBR.Item))
            g.add((i_uri, FRBR.exemplarOf, m_uri))
            if status:
                g.add((i_uri, SCHEMA.itemCondition, Literal(status)))

        # Specialized domain mapping for Concerts
        is_concert = (content_type in ("concert", "live_performance")) or (isinstance(item, dict) and item.get("is_concert"))
        if not is_concert and not isinstance(item, dict):
            expr = getattr(item, "expression", None) or (
                item.manifestation.expression if hasattr(item, "manifestation") and item.manifestation else None
            )
            if expr and getattr(expr, "kind", None) == EXPRESSION_KIND_LIVE_PERFORMANCE:
                is_concert = True
            m_obj = item if hasattr(item, "expression_id") else getattr(item, "manifestation", None)
            if m_obj and getattr(m_obj, "format", None) == "concert":
                is_concert = True

        if is_concert:
            g.add((m_uri, RDF.type, SCHEMA.MusicEvent))
            p_list = None
            if isinstance(item, dict):
                p_list = item.get("performers") or item.get("performer") or authors
                c_date = item.get("start_date") or item.get("date") or publication_date
                c_loc = item.get("location") or item.get("venue")
            else:
                m_obj = item if hasattr(item, "expression_id") else getattr(item, "manifestation", None)
                meta_dict = (m_obj.meta or {}) if m_obj else {}
                p_list = meta_dict.get("performers") or meta_dict.get("performer") or authors
                c_date = meta_dict.get("start_date") or meta_dict.get("event_date") or publication_date
                c_loc = meta_dict.get("location") or meta_dict.get("venue")

            if p_list:
                if isinstance(p_list, str):
                    p_list = [p_list]
                for p in p_list:
                    g.add((m_uri, SCHEMA.performer, Literal(str(p))))
            if c_date:
                g.add((m_uri, SCHEMA.startDate, Literal(str(c_date))))
            if c_loc:
                g.add((m_uri, SCHEMA.location, Literal(str(c_loc))))

        # Specialized domain mapping for Board Games
        is_board_game = (content_type == "board_game") or (isinstance(item, dict) and item.get("content_type") == "board_game")
        if not is_board_game and not isinstance(item, dict):
            m_obj = item if hasattr(item, "expression_id") else getattr(item, "manifestation", None)
            if m_obj and getattr(m_obj, "format_type", None) == "game":
                is_board_game = True

        if is_board_game:
            g.add((m_uri, RDF.type, SCHEMA.Game))
            min_p = None
            max_p = None
            num_p = None
            if isinstance(item, dict):
                min_p = item.get("min_players")
                max_p = item.get("max_players")
                num_p = item.get("number_of_players")
            else:
                m_obj = item if hasattr(item, "expression_id") else getattr(item, "manifestation", None)
                meta_dict = (m_obj.meta or {}) if m_obj else {}
                min_p = meta_dict.get("min_players")
                max_p = meta_dict.get("max_players")
                num_p = meta_dict.get("number_of_players")

            if min_p is not None and max_p is not None:
                player_str = str(min_p) if min_p == max_p else f"{min_p}-{max_p}"
                g.add((m_uri, SCHEMA.numberOfPlayers, Literal(player_str)))
            elif min_p is not None:
                g.add((m_uri, SCHEMA.numberOfPlayers, Literal(f"{min_p}+")))
            elif num_p:
                g.add((m_uri, SCHEMA.numberOfPlayers, Literal(str(num_p))))

    # --- Enrichment pass: Contributors, WorkParts, ImageScans, UserCollections ---
    _enrich_graph_from_db(g, items, base_url, collection_uri=collection_uri, enrichment_profile=enrichment_profile)
    return g


def _eager_load_items_fallback(items: list[Any]) -> list[Any]:
    """Ensure ORM instances in items have their FRBR relations eagerly loaded.

    If un-hydrated Item or Manifestation instances are detected, re-queries them
    in a single batch using joinedload across Item -> Manifestation -> Expression -> Work.
    """
    if not items:
        return items

    orm_items: list[Any] = []
    item_ids: list[int] = []
    manifestation_ids: list[int] = []

    for it in items:
        if isinstance(it, dict):
            continue
        if hasattr(it, "manifestation_id") and hasattr(it, "id") and it.id is not None:
            item_ids.append(it.id)
            orm_items.append(it)
        elif hasattr(it, "expression_id") and hasattr(it, "id") and it.id is not None:
            manifestation_ids.append(it.id)
            orm_items.append(it)

    if not orm_items:
        return items

    needs_hydration = False
    for it in orm_items:
        try:
            insp = sa_inspect(it)
            if hasattr(it, "manifestation_id"):
                if "manifestation" in insp.unloaded:
                    needs_hydration = True
                    break
                m = it.manifestation
                if m is not None:
                    m_insp = sa_inspect(m)
                    if "expression" in m_insp.unloaded:
                        needs_hydration = True
                        break
                    e = m.expression
                    if e is not None:
                        e_insp = sa_inspect(e)
                        if "work" in e_insp.unloaded:
                            needs_hydration = True
                            break
            elif hasattr(it, "expression_id"):
                if "expression" in insp.unloaded:
                    needs_hydration = True
                    break
                e = it.expression
                if e is not None:
                    e_insp = sa_inspect(e)
                    if "work" in e_insp.unloaded:
                        needs_hydration = True
                        break
        except (SQLAlchemyError, AttributeError, KeyError):
            pass

    if not needs_hydration:
        return items

    try:
        hydrated_items_map: dict[int, Any] = {}
        if item_ids:
            stmt = (
                select(Item)
                .options(joinedload(Item.manifestation).joinedload(Manifestation.expression).joinedload(Expression.work))
                .where(Item.id.in_(item_ids))
            )
            for loaded_item in db.session.execute(stmt).scalars().unique().all():
                hydrated_items_map[loaded_item.id] = loaded_item

        hydrated_manifestations_map: dict[int, Any] = {}
        if manifestation_ids:
            m_stmt = (
                select(Manifestation)
                .options(joinedload(Manifestation.expression).joinedload(Expression.work))
                .where(Manifestation.id.in_(manifestation_ids))
            )
            for loaded_m in db.session.execute(m_stmt).scalars().unique().all():
                hydrated_manifestations_map[loaded_m.id] = loaded_m

        result: list[Any] = []
        for it in items:
            if isinstance(it, dict):
                result.append(it)
            elif hasattr(it, "manifestation_id") and it.id in hydrated_items_map:
                result.append(hydrated_items_map[it.id])
            elif hasattr(it, "expression_id") and it.id in hydrated_manifestations_map:
                result.append(hydrated_manifestations_map[it.id])
            else:
                result.append(it)
        return result
    except (SQLAlchemyError, AttributeError, KeyError):
        return items


def stream_collection_to_rdf(
    items_iterable: Iterable[Any],
    base_url: str,
    output_format: str = "nt",
    chunk_size: int = 50,
    collection_uri: str | URIRef | None = None,
    enrichment_profile: str = "public",
) -> Generator[str, None, None]:
    """
    Generator that streams serialized RDF chunks for large collections.
    Supports 'nt' (N-Triples), 'turtle', and 'json-ld'.
    Processes items in chunks without loading entire collections into memory.

    Args:
        items_iterable: Iterable of items to serialize.
        base_url: Base URL for generating URIs.
        output_format: Output format ('nt', 'turtle', or 'json-ld').
        chunk_size: Number of items per chunk.
        collection_uri: Optional collection URI for hasPart/isPartOf relationships.
        enrichment_profile: "public" for public-safe enrichment, "full" for authenticated export.
    """
    iterator = iter(items_iterable)
    first_chunk = True

    while True:
        chunk = list(itertools.islice(iterator, chunk_size))
        if not chunk:
            break

        chunk = _eager_load_items_fallback(chunk)
        g = build_collection_rdf_graph(chunk, base_url, collection_uri=collection_uri, enrichment_profile=enrichment_profile)

        if output_format in ("nt", "n-triples", "ntriples"):
            chunk_nt = g.serialize(format="nt")
            if chunk_nt:
                yield chunk_nt
        elif output_format == "turtle":
            chunk_ttl = g.serialize(format="turtle")
            if first_chunk:
                yield chunk_ttl
            else:
                lines = [
                    line for line in chunk_ttl.splitlines(keepends=True) if not (line.startswith("@prefix") or line.startswith("PREFIX"))
                ]
                yield "".join(lines).lstrip()
        elif output_format == "json-ld":
            context = {
                "frbr": str(FRBR),
                "sioc": str(SIOC),
                "schema": str(SCHEMA),
                "prov": str(PROV),
                "title": "schema:name",
                "isbn": "schema:isbn",
                "author": "schema:author",
            }
            # Serialize as JSON-LD with @graph container for valid streaming
            chunk_jsonld = g.serialize(format="json-ld", context=context, indent=2)
            if chunk_jsonld:
                import json

                try:
                    chunk_data = json.loads(chunk_jsonld)
                    # Extract the graph items
                    if isinstance(chunk_data, list):
                        graph_items = chunk_data
                    elif isinstance(chunk_data, dict) and "@graph" in chunk_data:
                        graph_items = chunk_data["@graph"]
                    else:
                        graph_items = [chunk_data]

                    if first_chunk:
                        # First chunk: yield opening with context
                        yield '{\n  "@context": ' + json.dumps(context, indent=2) + ',\n  "@graph": [\n'
                        items_json = ",\n".join(json.dumps(item, indent=2) for item in graph_items)
                        yield items_json
                    else:
                        # Subsequent chunks: yield only items with leading comma
                        items_json = ",\n".join(json.dumps(item, indent=2) for item in graph_items)
                        yield ",\n" + items_json
                except json.JSONDecodeError:
                    # Fallback: yield as-is if parsing fails
                    if first_chunk:
                        yield chunk_jsonld
                    else:
                        yield "\n" + chunk_jsonld

        first_chunk = False

    # Close the JSON-LD document if we started one
    if output_format == "json-ld" and not first_chunk:
        yield "\n  ]\n}\n"


def serialize_collection_to_rdf(
    items: list[Any],
    base_url: str,
    output_format: str = "json-ld",
    collection_uri: str | URIRef | None = None,
    enrichment_profile: str = "public",
) -> str:
    """
    Serializes a list of collection items/manifestations into semantic RDF graphs
    supporting FRBRer, SIOC (for tags), and Schema.org profiles.

    Args:
        items: List of items to serialize.
        base_url: Base URL for generating URIs.
        output_format: Output format ('nt', 'turtle', or 'json-ld').
        collection_uri: Optional collection URI for hasPart/isPartOf relationships.
        enrichment_profile: "public" for public-safe enrichment, "full" for authenticated export.
    """
    items = _eager_load_items_fallback(items)
    g = build_collection_rdf_graph(items, base_url, collection_uri=collection_uri, enrichment_profile=enrichment_profile)

    if output_format in ("nt", "n-triples", "ntriples"):
        return g.serialize(format="nt")

    if output_format == "json-ld":
        context = {
            "frbr": str(FRBR),
            "sioc": str(SIOC),
            "schema": str(SCHEMA),
            "prov": str(PROV),
            "title": "schema:name",
            "isbn": "schema:isbn",
            "author": "schema:author",
        }
        return g.serialize(format="json-ld", context=context, indent=4)

    return g.serialize(format="turtle")
