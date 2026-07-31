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
from typing import TYPE_CHECKING, Any, cast

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
from sqlalchemy import select

from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY, FORMAT_TO_CATEGORY
from app.db.audio import Contributor, ExpressionContribution, WorkContribution, WorkPart
from app.db.core import EXPRESSION_KIND_LIVE_PERFORMANCE, EXPRESSION_KINDS, Expression, Item, Manifestation, Work
from app.db.models import db
from app.db.video import ManifestationContribution

if TYPE_CHECKING:
    from app.db.games import ContainerAggregation

import re

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

    Returns:
        The created Manifestation object
    """
    if meta is None:
        meta = {}
    if format is None:
        format = meta.get("format") or meta.get("video_format") or meta.get("format_name")
    if label is None:
        label = meta.get("label") or meta.get("studio") or meta.get("imprint") or publisher
    if barcode is None:
        barcode = meta.get("barcode") or meta.get("identifier") or ean or upc or isbn13
    if catalog_number is None:
        catalog_number = meta.get("catalog_number") or meta.get("catno") or meta.get("sku")

    manifestation = Manifestation(
        expression_id=expression_id,
        isbn13=isbn13,
        upc=upc,
        ean=ean,
        publisher=publisher,
        publication_date=publication_date,
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
    if format is not None:
        manif.format = format
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
            if manif.expression:
                category = FORMAT_TO_CATEGORY.get(new_type) or FORMAT_ALIAS_TO_CATEGORY.get(new_type) or new_type
                manif.expression.content_type = category
                if manif.expression.work:
                    w_meta = dict(manif.expression.work.meta or {})
                    w_meta["type"] = category
                    w_meta["format"] = category
                    w_meta["Format"] = category
                    manif.expression.work.meta = w_meta
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
    meta["type"] = carrier
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


def serialize_collection_to_rdf(items: list[Any], base_url: str, output_format: str = "json-ld") -> str:
    """
    Serializes a list of collection items/manifestations into semantic RDF graphs
    supporting FRBRer, SIOC (for tags), and Schema.org profiles.
    """
    g = Graph()
    g.bind("frbr", FRBR)
    g.bind("sioc", SIOC)
    g.bind("schema", SCHEMA)

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

                m = item.manifestation
                if m:
                    manifestation_id = m.id
                    expression_id = m.expression_id
                    title = getattr(m, "title", "Untitled") or "Untitled"
                    isbn = m.isbn13
                    if m.expression:
                        expression_id = m.expression.id
                        work_id = m.expression.work_id
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

                if hasattr(item, "expression") and item.expression:
                    expr = item.expression
                    expression_id = expr.id
                    work_id = expr.work_id
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

        if isbn:
            g.add((m_uri, SCHEMA.isbn, Literal(isbn)))

        for author in authors:
            g.add((m_uri, SCHEMA.author, Literal(author)))
            g.add((w_uri, FRBR.creator, Literal(author)))

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

    # Serialization Context Setup for JSON-LD vs Turtle
    if output_format == "json-ld":
        context = {
            "frbr": str(FRBR),
            "sioc": str(SIOC),
            "schema": str(SCHEMA),
            "title": "schema:name",
            "isbn": "schema:isbn",
            "author": "schema:author",
        }
        return g.serialize(format="json-ld", context=context, indent=4)

    return g.serialize(format="turtle")
