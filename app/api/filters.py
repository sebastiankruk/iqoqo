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
"""Dialect-aware genre filter helper for faceted navigation."""

from sqlalchemy.dialects.postgresql import JSONB

from app.db import db
from app.db.models import (
    Expression,
    Item,
    ItemTag,
    Manifestation,
    SemanticLink,
    Tag,
    UserCollection,
    UserCollectionItem,
    Work,
)


def parse_csv_param(value: str | None) -> list[str] | None:
    """Parse comma-separated string parameter into a list of non-empty stripped strings.

    Parameters
    ----------
    value:
        Optional comma-separated string parameter.

    Returns
    -------
    list[str] | None
        List of non-empty stripped string tokens, or None if input is empty/None/whitespace only.
    """
    if not value:
        return None
    tokens = [t.strip() for t in value.split(",") if t.strip()]
    return tokens if tokens else None


def escape_ilike_term(term: str) -> str:
    """Canonicalize apostrophe variants (’ ‘ ʼ -> ') and escape ILIKE metacharacters (% _ \\)."""
    if not term:
        return ""
    cleaned = term.translate(str.maketrans("’‘ʼ", "'''")).strip()
    return cleaned.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def apply_genre_filter(query, genres_list):
    """Apply genre filter on Work.meta, handling scalar ``genre`` and array ``genres`` case-insensitively.

    The ``Work.meta`` column is typed as PostgreSQL ``json`` (not ``jsonb``).
    We explicitly cast to ``jsonb`` so that SQLAlchemy's ``.contains()``
    emits the ``@>`` containment operator instead of a broken ``LIKE`` on
    raw JSON.  This also allows the GIN index
    ``idx_work_meta_genres_gin`` (on ``meta::jsonb->'genres'``) to be
    used for ``@>`` queries.
    """
    is_postgres = db.engine.dialect.name == "postgresql"

    conditions = []
    for gen in genres_list:
        g_clean = gen.strip().translate(str.maketrans("’‘ʼ", "'''"))
        if is_postgres:
            # Cast meta to jsonb so .contains() emits the @> containment operator
            meta_jsonb = Work.meta.cast(JSONB)
            conditions.append(meta_jsonb.contains({"genre": g_clean}))
            conditions.append(meta_jsonb["genres"].contains([g_clean]))
        else:
            # SQLite fallback path with explicit ESCAPE '\\'
            g_escaped = escape_ilike_term(gen)
            conditions.append(Work.meta["genre"].as_string().ilike(f"%{g_escaped}%", escape="\\"))
            conditions.append(Work.meta["genres"].as_string().ilike(f"%{g_escaped}%", escape="\\"))
    query = query.filter(db.or_(*conditions))
    return query


def apply_statuses_filter(query, statuses_list, user_id=None, borrowed_only=False):
    """
    Apply statuses filter handling both Process (Item.status) and Collection (Item.collection_status) filters.
    When both types are provided, applies them conjunctively (AND).
    """
    if not statuses_list:
        return query

    from app.core.taxonomy import COLLECTION_STATUSES, PROGRESS_STATUSES
    from app.db.models import Item

    process_statuses = [s for s in statuses_list if s in PROGRESS_STATUSES]
    collection_statuses = [s for s in statuses_list if s in COLLECTION_STATUSES]
    unknown_statuses = [s for s in statuses_list if s not in PROGRESS_STATUSES and s not in COLLECTION_STATUSES]

    if unknown_statuses:
        process_statuses.extend(unknown_statuses)

    conditions = []
    if process_statuses:
        conditions.append(Item.status.in_(process_statuses))

    if collection_statuses:
        if "lent" in collection_statuses and not borrowed_only and user_id is not None:
            other_statuses = [s for s in collection_statuses if s != "lent"]
            if other_statuses:
                conditions.append(
                    db.or_(
                        db.and_(Item.collection_status == "lent", Item.owner_id == user_id),
                        Item.collection_status.in_(other_statuses),
                    )
                )
            else:
                conditions.append(db.and_(Item.collection_status == "lent", Item.owner_id == user_id))
        else:
            conditions.append(Item.collection_status.in_(collection_statuses))

    if conditions:
        return query.filter(db.and_(*conditions))
    return query


class CatalogFilterBuilder:
    """Unified, join-deduplicating builder for multi-entity catalog filters.

    Encapsulates format, content-type (category), tags, collections, genres,
    publishers, statuses, missing cover/id flags, LOD linkage and ownership
    filters in a single dialect-aware abstraction, so that listing, search and
    faceting endpoints compile identical join paths and identical filter
    clauses for the same set of parameters.

    The builder tracks which joins it has already emitted so that combining
    several item-scoped facets (for example ``tags`` *and* ``statuses``) never
    produces a duplicate ``JOIN items`` clause — the cause of the divergent
    query plans between listing and counting endpoints.

    Notes
    -----
    The FRBR chain (``Manifestation`` -> ``Expression`` -> ``Work``) is joined
    by the *caller* for manifestation-rooted queries, because those callers
    require INNER joins.  For item-rooted queries the caller passes
    ``ensure_frbr_joins=True`` and the builder performs the join exactly once,
    with the join style (``outer``/``inner``) chosen by the caller.

    Parameters
    ----------
    query:
        Base ``Query``/``Select`` to build upon.
    root:
        Either :data:`ROOT_MANIFESTATION` or :data:`ROOT_ITEM`.  Determines
        whether ``Item`` needs an explicit join and which column the ownership
        filter is evaluated against.
    user_id:
        Authenticated user, or ``None`` for anonymous requests.  User-scoped
        filters (statuses, collections, ownership) are only applied when set.
    borrowed_only:
        Passed through to :func:`apply_statuses_filter`.
    ensure_frbr_join:
        When ``True`` the builder joins the FRBR chain itself (item-rooted
        callers only).  Callers that need a FRBR join for unrelated reasons
        (for example sorting by work title) may set this to preserve their
        existing join plan.
    frbr_join_outer:
        Use ``OUTER JOIN`` rather than ``JOIN`` for the FRBR chain when
        ``ensure_frbr_joins`` is set.
    statuses_style:
        ``"auto"`` applies the full taxonomy semantics of
        :func:`apply_statuses_filter` (progress *and* collection statuses,
        with lent-out ownership scoping).  ``"progress_only"`` applies the
        narrower ``Item.status IN (...)`` predicate historically used by the
        ILIKE search path.
    """

    ROOT_MANIFESTATION = "manifestation"
    ROOT_ITEM = "item"

    def __init__(
        self,
        query,
        *,
        root: str = ROOT_MANIFESTATION,
        user_id=None,
        borrowed_only: bool = False,
        ensure_frbr_join: bool = False,
        frbr_join_outer: bool = True,
        statuses_style: str = "auto",
    ):
        self.query = query
        self.root = root
        self.user_id = user_id
        self.borrowed_only = borrowed_only
        self.ensure_frbr_join = ensure_frbr_join
        self.frbr_join_outer = frbr_join_outer
        self.statuses_style = statuses_style
        self._joined_frbr = False
        # For item-rooted queries Item *is* the root, so no join is required.
        self._joined_item = root == self.ROOT_ITEM
        self._joined_tags = False
        self._joined_collections = False

    # ── join helpers ────────────────────────────────────────────────────

    def _ensure_frbr_joins(self) -> None:
        """Join Manifestation -> Expression -> Work at most once."""
        if self._joined_frbr or not self.ensure_frbr_join:
            self._joined_frbr = True
            return
        join = self.query.outerjoin if self.frbr_join_outer else self.query.join
        self.query = (
            join(Manifestation, Item.manifestation_id == Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .join(Work, Expression.work_id == Work.id)
        )
        self._joined_frbr = True

    def _ensure_item_join(self, owner_scoped: bool = False) -> None:
        """Join ``Item`` at most once for manifestation-rooted queries.

        ``owner_scoped`` mirrors the historical behaviour where the owner
        predicate is baked into the join condition.  It only takes effect when
        this call is the one that introduces the join, so callers that mix
        several item-scoped facets keep the same plan as before.
        """
        if self._joined_item:
            return
        if self.root == self.ROOT_ITEM:
            self._joined_item = True
            return
        if owner_scoped and self.user_id is not None:
            self.query = self.query.join(Item, db.and_(Manifestation.id == Item.manifestation_id, Item.owner_id == self.user_id))
        else:
            self.query = self.query.join(Item, Manifestation.id == Item.manifestation_id)
        self._joined_item = True

    def _ensure_tags_join(self) -> None:
        if self._joined_tags:
            return
        self._ensure_item_join()
        self.query = self.query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
        self._joined_tags = True

    def _ensure_collections_join(self) -> None:
        if self._joined_collections:
            return
        self._ensure_item_join()
        self.query = self.query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
            UserCollection, UserCollectionItem.collection_id == UserCollection.id
        )
        self._joined_collections = True

    # ── filter groups ───────────────────────────────────────────────────

    def _apply_category(self, category: list[str] | None) -> None:
        if category:
            self.query = self.query.filter(Expression.content_type.in_(category))

    def _apply_format(self, fmt: list[str] | None) -> None:
        if fmt:
            self.query = self.query.filter(Manifestation.meta["format"].as_string().in_(fmt))

    def _apply_missing_cover(self, missing_cover: bool) -> None:
        if missing_cover:
            self.query = self.query.filter(
                db.and_(
                    db.or_(Manifestation.cover_url.is_(None), Manifestation.cover_url == ""),
                    db.or_(
                        Manifestation.meta["cover_url"].as_string().is_(None),
                        Manifestation.meta["cover_url"].as_string() == "",
                    ),
                )
            )

    def _apply_missing_id(self, missing_id: bool) -> None:
        if missing_id:
            self.query = self.query.filter(
                db.and_(
                    db.or_(Manifestation.isbn13.is_(None), Manifestation.isbn13 == ""),
                    db.or_(Manifestation.upc.is_(None), Manifestation.upc == ""),
                    db.or_(Manifestation.ean.is_(None), Manifestation.ean == ""),
                    db.or_(
                        Manifestation.meta["barcode"].as_string().is_(None),
                        Manifestation.meta["barcode"].as_string() == "",
                    ),
                    db.or_(
                        Manifestation.meta["catalog_number"].as_string().is_(None),
                        Manifestation.meta["catalog_number"].as_string() == "",
                    ),
                )
            )

    def _apply_ownership(self, ownership: list[str] | None) -> None:
        """Apply ``owned`` / ``not_owned`` filtering.

        For manifestation-rooted queries this uses an ``EXISTS`` correlated
        subquery so that no extra ``Item`` join is introduced; for item-rooted
        queries the predicate is evaluated directly against the root ``Item``.
        """
        if not ownership or self.user_id is None:
            return
        if self.root == self.ROOT_ITEM:
            owned = Item.owner_id == self.user_id
        else:
            owned = db.session.query(Item.id).filter(Item.manifestation_id == Manifestation.id, Item.owner_id == self.user_id).exists()
        conditions = []
        if "owned" in ownership:
            conditions.append(owned)
        if "not_owned" in ownership:
            conditions.append(~owned)
        if conditions:
            self.query = self.query.filter(db.or_(*conditions))

    def _apply_tags(self, tags: list[str] | None) -> None:
        if not tags:
            return
        self._ensure_tags_join()
        self.query = self.query.filter(db.or_(*[Tag.name.ilike(t.strip()) for t in tags]))

    def _apply_collections(self, collections: list[str] | None) -> None:
        if not collections:
            return
        self._ensure_collections_join()
        self.query = self.query.filter(db.or_(*[UserCollection.name.ilike(c.strip()) for c in collections]))
        if self.user_id is not None:
            self.query = self.query.filter(UserCollection.owner_id == self.user_id)

    def _apply_genres(self, genres: list[str] | None) -> None:
        if genres:
            self.query = apply_genre_filter(self.query, genres)

    def _apply_publishers(self, publishers: list[str] | None) -> None:
        if not publishers:
            return
        pubs_conditions = []
        for p in publishers:
            p_term = f"%{p.strip()}%"
            pubs_conditions.append(
                db.or_(
                    Manifestation.publisher.ilike(p_term),
                    Manifestation.meta["Publisher"].as_string().ilike(p_term),
                    Manifestation.meta["publisher"].as_string().ilike(p_term),
                    db.and_(Expression.content_type == "music", Manifestation.meta["label"].as_string().ilike(p_term)),
                )
            )
        self.query = self.query.filter(db.or_(*pubs_conditions))

    def _apply_statuses(self, statuses: list[str] | None) -> None:
        if not statuses or self.user_id is None:
            return
        if self.statuses_style == "progress_only":
            self._ensure_item_join(owner_scoped=True)
            self.query = self.query.filter(Item.status.in_(statuses))
            return
        self._ensure_item_join(owner_scoped=True)
        self.query = apply_statuses_filter(self.query, statuses, user_id=self.user_id, borrowed_only=self.borrowed_only)

    def _apply_lod(self, lod_authority: str | None, lod_status: str | None) -> None:
        """Apply LOD authority / linkage filters across Manifestation and Work."""
        if lod_authority:
            authority = lod_authority.lower()
            manif_auth_subq = db.select(SemanticLink.entity_id).where(
                SemanticLink.entity_type == "manifestation",
                db.func.lower(SemanticLink.authority) == authority,
            )
            work_auth_subq = db.select(SemanticLink.entity_id).where(
                SemanticLink.entity_type == "work",
                db.func.lower(SemanticLink.authority) == authority,
            )
            self.query = self.query.filter(
                db.or_(
                    Manifestation.id.in_(manif_auth_subq),
                    Work.id.in_(work_auth_subq),
                )
            )

        if lod_status == "linked":
            manif_subq = db.select(SemanticLink.entity_id).where(SemanticLink.entity_type == "manifestation")
            work_subq = db.select(SemanticLink.entity_id).where(SemanticLink.entity_type == "work")
            self.query = self.query.filter(
                db.or_(
                    Manifestation.id.in_(manif_subq),
                    Work.id.in_(work_subq),
                )
            )
        elif lod_status == "unlinked":
            manif_subq = db.select(SemanticLink.entity_id).where(SemanticLink.entity_type == "manifestation")
            work_subq = db.select(SemanticLink.entity_id).where(SemanticLink.entity_type == "work")
            self.query = self.query.filter(
                db.and_(
                    ~Manifestation.id.in_(manif_subq),
                    ~Work.id.in_(work_subq),
                )
            )

    # ── entry point ─────────────────────────────────────────────────────

    def ensure_frbr_joins(self):
        """Publicly force the FRBR chain join.

        Item-rooted callers whose join requirement is driven by something other
        than a filter (for example sorting by work title) use this to request
        the same single outer join the builder would otherwise add lazily.
        """
        self._ensure_frbr_joins()
        return self.query

    def apply(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        *,
        category: list[str] | None = None,
        fmt: list[str] | None = None,
        tags: list[str] | None = None,
        collections: list[str] | None = None,
        genres: list[str] | None = None,
        publishers: list[str] | None = None,
        statuses: list[str] | None = None,
        ownership: list[str] | None = None,
        missing_cover: bool = False,
        missing_id: bool = False,
        lod_authority: str | None = None,
        lod_status: str | None = None,
    ):
        """Apply every supplied filter group and return the built query."""
        needs_frbr = bool(
            category
            or fmt
            or publishers
            or genres
            or missing_cover
            or missing_id
            or lod_authority
            or lod_status
            or (self.root == self.ROOT_ITEM and (tags or collections or statuses or ownership))
        )
        if needs_frbr:
            self._ensure_frbr_joins()

        self._apply_category(category)
        self._apply_format(fmt)
        self._apply_missing_cover(missing_cover)
        self._apply_missing_id(missing_id)
        self._apply_ownership(ownership)
        self._apply_tags(tags)
        self._apply_collections(collections)
        self._apply_genres(genres)
        self._apply_publishers(publishers)
        self._apply_statuses(statuses)
        self._apply_lod(lod_authority, lod_status)
        return self.query

    def build(self, **kwargs):
        """Alias for :meth:`apply` for call sites that read better as a builder."""
        return self.apply(**kwargs)
