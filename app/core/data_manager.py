# pylint: disable=too-many-lines
"""
Data Import/Export Manager for iqoqo.

Handles exporting and importing database content in a standardized JSON format.
Supports both full database dumps and selective exports.
"""

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

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import distinct, func, or_, select

from app.db import db
from app.db.models import (
    ITEM_STATUSES,
    Expression,
    Item,
    ItemTag,
    Manifestation,
    Tag,
    User,
    UserCollection,
    UserCollectionItem,
    UserWorkIntent,
    Work,
)


class DataManager:
    """Manages import and export of iqoqo database content."""

    @staticmethod
    def export_all() -> dict[str, Any]:
        """
        Export all data from the database in JSON format.

        Returns:
            Dict containing all works, expressions, manifestations, and items.
        """
        data: dict[str, Any] = {
            "version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "works": [],
            "expressions": [],
            "manifestations": [],
            "items": [],
        }

        # Export works
        for work in Work.query.all():
            data["works"].append(
                {
                    "id": work.id,
                    "title": work.title,
                    "sort_title": work.sort_title or (work.meta.get("sort_title") if work.meta else None),
                    "meta": work.meta,
                    "raw_payload": work.raw_payload,
                }
            )

        # Export expressions
        for expr in Expression.query.all():
            data["expressions"].append(
                {
                    "id": expr.id,
                    "work_id": expr.work_id,
                    "content_type": expr.content_type,
                    "language": expr.language,
                    "kind": expr.kind or (expr.meta.get("kind") if expr.meta else None),
                    "meta": expr.meta,
                    "raw_payload": expr.raw_payload,
                }
            )

        # Export manifestations
        for manif in Manifestation.query.all():
            data["manifestations"].append(
                {
                    "id": manif.id,
                    "expression_id": manif.expression_id,
                    "isbn13": manif.isbn13,
                    "upc": manif.upc,
                    "ean": manif.ean,
                    "publisher": manif.publisher or (manif.meta.get("publisher") if manif.meta else None),
                    "publication_date": (manif.publication_date.isoformat() if manif.publication_date else None),
                    "cover_url": manif.cover_url,
                    "format": manif.format or (manif.meta.get("format") if manif.meta else None),
                    "label": manif.label or (manif.meta.get("label") if manif.meta else None),
                    "barcode": manif.barcode or (manif.meta.get("barcode") if manif.meta else None),
                    "catalog_number": manif.catalog_number or (manif.meta.get("catalog_number") if manif.meta else None),
                    "meta": manif.meta,
                    "raw_payload": manif.raw_payload,
                }
            )

        # Export items
        for item in Item.query.all():
            data["items"].append(
                {
                    "id": item.id,
                    "manifestation_id": item.manifestation_id,
                    "owner_id": str(item.owner_id) if item.owner_id else None,
                    "status": item.status,
                    "collection_status": item.collection_status,
                    "condition": item.condition,
                    "added_at": item.added_at.isoformat() if item.added_at else None,
                    "meta": item.meta,
                    "raw_payload": item.raw_payload,
                }
            )

        return data

    @staticmethod
    def export_to_file(filepath: str) -> None:
        """
        Export all data to a JSON file.

        Args:
            filepath: Path to the output JSON file.
        """
        data = DataManager.export_all()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def import_data(data: dict[str, Any], clear_existing: bool = False) -> dict[str, int]:
        """
        Import data from a JSON structure.

        Args:
            data: Dictionary containing works, expressions, manifestations, and items.
            clear_existing: If True, clears all existing data before importing.

        Returns:
            Dictionary with counts of imported records.
        """
        if clear_existing:
            DataManager.clear_all_data()

        # Track ID mappings (old_id -> new_id)
        work_id_map: dict[int, int] = {}
        expr_id_map: dict[int, int] = {}
        manif_id_map: dict[int, int] = {}

        counts = {
            "works": 0,
            "expressions": 0,
            "manifestations": 0,
            "items": 0,
        }

        # Ensure a fallback user exists for imported items lacking valid UUID owners
        default_owner = User.query.first()
        if not default_owner:
            default_owner = User(email="data_importer@iqoqo.local", display_name="Data Importer")
            db.session.add(default_owner)
            db.session.flush()

        # Import works
        for work_data in data.get("works", []):
            old_id = work_data.get("id")
            work = Work(
                title=work_data["title"],
                meta=work_data.get("meta", {}),
            )
            db.session.add(work)
            db.session.flush()  # Get the new ID
            if old_id:
                work_id_map[old_id] = work.id
            counts["works"] += 1

        # Import expressions
        for expr_data in data.get("expressions", []):
            old_id = expr_data.get("id")
            old_work_id = expr_data.get("work_id")
            new_work_id = work_id_map.get(old_work_id, old_work_id)

            expr = Expression(
                work_id=new_work_id,
                content_type=expr_data.get("content_type"),
                language=expr_data.get("language"),
                meta=expr_data.get("meta", {}),
            )
            db.session.add(expr)
            db.session.flush()
            if old_id:
                expr_id_map[old_id] = expr.id
            counts["expressions"] += 1

        # Import manifestations
        for manif_data in data.get("manifestations", []):
            old_id = manif_data.get("id")
            old_expr_id = manif_data.get("expression_id")
            new_expr_id = expr_id_map.get(old_expr_id, old_expr_id)

            pub_date = None
            if manif_data.get("publication_date"):
                pub_date = datetime.fromisoformat(manif_data["publication_date"]).date()

            manif = Manifestation(
                expression_id=new_expr_id,
                isbn13=manif_data.get("isbn13"),
                upc=manif_data.get("upc"),
                ean=manif_data.get("ean"),
                publisher=manif_data.get("publisher"),
                publication_date=pub_date,
                meta=manif_data.get("meta", {}),
            )
            db.session.add(manif)
            db.session.flush()
            if old_id:
                manif_id_map[old_id] = manif.id
            counts["manifestations"] += 1

        # Import items
        for item_data in data.get("items", []):
            old_manif_id = item_data.get("manifestation_id")
            new_manif_id = manif_id_map.get(old_manif_id, old_manif_id)

            added_at = None
            if item_data.get("added_at"):
                added_at = datetime.fromisoformat(item_data["added_at"])

            # Resolve Owner ID (fallback to default if invalid/missing)
            raw_owner_id = item_data.get("owner_id")
            owner_id = default_owner.id
            if raw_owner_id:
                try:
                    owner_id = uuid.UUID(str(raw_owner_id))
                except ValueError:
                    pass

            item = Item(
                manifestation_id=new_manif_id,
                owner_id=owner_id,
                status=item_data.get("status", "want_to_read"),
                collection_status=item_data.get("collection_status", "available"),
                condition=item_data.get("condition"),
                added_at=added_at,
                meta=item_data.get("meta", {}),
            )
            db.session.add(item)
            counts["items"] += 1

        db.session.commit()
        return counts

    @staticmethod
    def import_from_file(filepath: str, clear_existing: bool = False) -> dict[str, int]:
        """
        Import data from a JSON file.

        Args:
            filepath: Path to the input JSON file.
            clear_existing: If True, clears all existing data before importing.

        Returns:
            Dictionary with counts of imported records.
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return DataManager.import_data(data, clear_existing=clear_existing)

    @staticmethod
    def clear_all_data() -> None:
        """Clear all data from the database. Use with caution!"""
        Item.query.delete()
        Manifestation.query.delete()
        Expression.query.delete()
        Work.query.delete()
        db.session.commit()

    @staticmethod
    def verify_column_meta_drift() -> dict[str, Any]:
        """
        Post-migration verification query health check.

        Compares relational column values against historical ``meta`` JSON keys.
        Returns a dict summarizing any non-zero drift counts.

        All drift computation is performed at the database level using
        ``func.count()`` with JSONB operators to prevent OOM exhaustion
        on large catalogs.
        """
        is_pg = db.engine.dialect.name == "postgresql"

        if is_pg:
            format_cond = [
                Manifestation.meta.has_key("format"),  # noqa: W601
                Manifestation.format != Manifestation.meta["format"].as_string(),
            ]
            label_cond = [
                Manifestation.meta.has_key("label"),  # noqa: W601
                Manifestation.label != Manifestation.meta["label"].as_string(),
            ]
            barcode_cond = [
                Manifestation.meta.has_key("barcode"),  # noqa: W601
                Manifestation.barcode != Manifestation.meta["barcode"].as_string(),
            ]
        else:
            fmt_ext = func.json_extract(Manifestation.meta, "$.format")
            format_cond = [fmt_ext.is_not(None), Manifestation.format != fmt_ext]
            lbl_ext = func.json_extract(Manifestation.meta, "$.label")
            label_cond = [lbl_ext.is_not(None), Manifestation.label != lbl_ext]
            bar_ext = func.json_extract(Manifestation.meta, "$.barcode")
            barcode_cond = [bar_ext.is_not(None), Manifestation.barcode != bar_ext]

        # Format Drift
        format_drift = (
            db.session.query(func.count(Manifestation.id))  # pylint: disable=not-callable
            .filter(
                Manifestation.meta.is_not(None),
                *format_cond,
            )
            .scalar()
            or 0
        )

        # Label Drift
        label_drift = (
            db.session.query(func.count(Manifestation.id))  # pylint: disable=not-callable
            .filter(
                Manifestation.meta.is_not(None),
                *label_cond,
            )
            .scalar()
            or 0
        )

        # Barcode Drift
        barcode_drift = (
            db.session.query(func.count(Manifestation.id))  # pylint: disable=not-callable
            .filter(
                Manifestation.meta.is_not(None),
                *barcode_cond,
            )
            .scalar()
            or 0
        )

        # Sort Title Drift
        sort_title_drift = (
            db.session.query(func.count(Work.id))  # pylint: disable=not-callable
            .filter(
                Work.title.is_not(None),
                Work.sort_title.is_(None),
            )
            .scalar()
            or 0
        )

        total_drift = format_drift + label_drift + barcode_drift + sort_title_drift

        return {
            "format_drift": format_drift,
            "label_drift": label_drift,
            "barcode_drift": barcode_drift,
            "sort_title_drift": sort_title_drift,
            "total_drift": total_drift,
        }

    @staticmethod
    def get_stats(owner_id: uuid.UUID | None = None) -> dict[str, int]:
        """
        Get database statistics.

        When ``owner_id`` is provided all counts — including the FRBR entity
        counts for works, expressions, and manifestations — are scoped to that
        user's collection by walking the join chain
        ``Item → Manifestation → Expression → Work`` with ``distinct()``.
        This ensures the response is fully user-scoped rather than mixing
        user-scoped item counts with global FRBR counts.

        When ``owner_id`` is ``None`` all counts reflect the full database.

        Args:
            owner_id: Optional ID of the owner to filter their specific collection.

        Returns:
            Dictionary with counts for each FRBR entity type plus UI-friendly
            derived fields (``total_items``, ``lent_items``, ``to_read``) used
            by the React dashboard, and per-status counts keyed as
            ``items_<status>`` for every value in ``ITEM_STATUSES``.
        """
        # Group by Item.status (progress) and Item.collection_status
        owner_filter = [Item.owner_id == owner_id] if owner_id else []
        status_rows = db.session.execute(
            select(Item.status, func.count(Item.id).label("cnt")).where(*owner_filter).group_by(Item.status)  # pylint: disable=not-callable
        ).all()
        collection_status_rows = db.session.execute(
            select(Item.collection_status, func.count(Item.id).label("cnt"))  # pylint: disable=not-callable
            .where(*owner_filter)
            .group_by(Item.collection_status)
        ).all()

        format_rows = db.session.execute(
            select(Expression.content_type, func.count(Item.id).label("cnt"))  # pylint: disable=not-callable
            .select_from(Item)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .where(*owner_filter)
            .group_by(Expression.content_type)
        ).all()

        borrowed_count = 0
        if owner_id:
            borrowed_count = (
                db.session.execute(
                    select(func.count(Item.id)).where(Item.lent_to_user_id == owner_id)  # pylint: disable=not-callable
                ).scalar()
                or 0
            )

        status_counts: dict[str, int] = dict.fromkeys(ITEM_STATUSES, 0)
        total = 0

        for status, cnt in status_rows:
            if status in status_counts:
                status_counts[status] += cnt
            total += cnt

        for c_status, cnt in collection_status_rows:
            if c_status in status_counts:
                status_counts[c_status] += cnt

        intent_filter = [UserWorkIntent.user_id == owner_id] if owner_id else []
        intent_filter.append(UserWorkIntent.status != "fulfilled")
        intent_count = (
            db.session.execute(select(func.count(UserWorkIntent.id)).where(*intent_filter)).scalar() or 0  # pylint: disable=not-callable
        )
        status_counts["wish_list"] += intent_count

        if owner_id:
            works_count = (
                db.session.execute(
                    select(func.count(distinct(Work.id)))  # pylint: disable=not-callable
                    .select_from(Work)
                    .outerjoin(Expression, Expression.work_id == Work.id)
                    .outerjoin(Manifestation, Manifestation.expression_id == Expression.id)
                    .outerjoin(Item, db.and_(Item.manifestation_id == Manifestation.id, Item.owner_id == owner_id))
                    .outerjoin(UserWorkIntent, db.and_(UserWorkIntent.work_id == Work.id, UserWorkIntent.user_id == owner_id))
                    .where(db.or_(Item.id.isnot(None), UserWorkIntent.id.isnot(None)))
                ).scalar()
                or 0
            )

            expressions_count = (
                db.session.execute(
                    select(func.count(distinct(Expression.id)))  # pylint: disable=not-callable
                    .select_from(Expression)
                    .join(Work, Expression.work_id == Work.id)
                    .outerjoin(Manifestation, Manifestation.expression_id == Expression.id)
                    .outerjoin(Item, db.and_(Item.manifestation_id == Manifestation.id, Item.owner_id == owner_id))
                    .outerjoin(UserWorkIntent, db.and_(UserWorkIntent.work_id == Work.id, UserWorkIntent.user_id == owner_id))
                    .where(db.or_(Item.id.isnot(None), UserWorkIntent.id.isnot(None)))
                ).scalar()
                or 0
            )

            manifestations_count = (
                db.session.execute(
                    select(func.count(distinct(Manifestation.id)))  # pylint: disable=not-callable
                    .select_from(Manifestation)
                    .join(Expression, Manifestation.expression_id == Expression.id)
                    .join(Work, Expression.work_id == Work.id)
                    .outerjoin(Item, db.and_(Item.manifestation_id == Manifestation.id, Item.owner_id == owner_id))
                    .outerjoin(UserWorkIntent, db.and_(UserWorkIntent.work_id == Work.id, UserWorkIntent.user_id == owner_id))
                    .where(db.or_(Item.id.isnot(None), UserWorkIntent.id.isnot(None)))
                ).scalar()
                or 0
            )
        else:
            works_count = Work.query.count()
            expressions_count = Expression.query.count()
            manifestations_count = Manifestation.query.count()

        return {
            # FRBR entity counts (user-scoped when owner_id is set)
            "works": works_count,
            "expressions": expressions_count,
            "manifestations": manifestations_count,
            "items": total,
            # UI-friendly aliases expected by the React dashboard
            "total_items": total,
            "lent_items": status_counts["lent"],
            "borrowed_items": borrowed_count,
            "items_borrowed": borrowed_count,
            "to_read": status_counts["wish_list"],
            # Per-status counts (items_available, items_lent, …)
            **{f"items_{s}": count for s, count in status_counts.items()},
            # Per-format counts
            **{f"format_{f}": count for f, count in format_rows},
        }

    @staticmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    def _build_item_ids_subq(
        owner_id: uuid.UUID | None = None,
        category: list[str] | None = None,
        fmt: list[str] | None = None,
        tags: list[str] | None = None,
        collections: list[str] | None = None,
        genres: list[str] | None = None,
        publishers: list[str] | None = None,
        statuses: list[str] | None = None,
        borrowed_only: bool = False,
        missing_cover: bool = False,
        missing_id: bool = False,
        target_entity: str = "items",
    ):
        """Build a subquery of entity IDs matching the given filters.

        The ``target_entity`` parameter controls which FRBR-level entity IDs
        are returned in the subquery: ``"items"``, ``"manifestations"``,
        ``"expressions"``, or ``"works"``.  For non-Item targets the query
        starts from the target entity and joins down through the FRBR
        hierarchy to apply lower-level filters (statuses, tags, etc.).

        Each filter group can be independently enabled or disabled via its
        parameter, allowing callers to exclude a particular facet group's
        own filters when computing that group's counts for multi-select
        faceted navigation.

        User-specific filters (tags, collections, statuses) are only applied
        when an owner_id is provided (authenticated user).
        """
        # Map target entity to class and ID column
        _target_map = {
            "items": (Item, Item.id),
            "manifestations": (Manifestation, Manifestation.id),
            "expressions": (Expression, Expression.id),
            "works": (Work, Work.id),
        }
        target_cls, target_id_col = _target_map.get(target_entity, (Item, Item.id))

        _has_user_filters = owner_id is not None and (tags is not None or collections is not None or statuses is not None or borrowed_only)

        _needs_item_join = _has_user_filters or (missing_cover is True) or (missing_id is True)

        # Build base query starting from the target entity and joining down
        if target_entity == "works":
            base_query = (
                select(distinct(target_id_col).label("id"))
                .select_from(target_cls)
                .join(Expression, Expression.work_id == Work.id)
                .join(Manifestation, Manifestation.expression_id == Expression.id)
            )
            # Item join: LEFT if no item-level filters, otherwise INNER
            if _needs_item_join:
                base_query = base_query.join(Item, Item.manifestation_id == Manifestation.id)
            else:
                base_query = base_query.outerjoin(Item, Item.manifestation_id == Manifestation.id)
        elif target_entity == "expressions":
            base_query = (
                select(distinct(target_id_col).label("id"))
                .select_from(target_cls)
                .join(Work, Expression.work_id == Work.id)
                .join(Manifestation, Manifestation.expression_id == Expression.id)
            )
            if _needs_item_join:
                base_query = base_query.join(Item, Item.manifestation_id == Manifestation.id)
            else:
                base_query = base_query.outerjoin(Item, Item.manifestation_id == Manifestation.id)
        elif target_entity == "manifestations":
            base_query = (
                select(distinct(target_id_col).label("id"))
                .select_from(target_cls)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
            )
            if _needs_item_join:
                base_query = base_query.join(Item, Item.manifestation_id == Manifestation.id)
            else:
                base_query = base_query.outerjoin(Item, Item.manifestation_id == Manifestation.id)
        else:  # "items"
            base_query = (
                select(distinct(target_id_col).label("id"))
                .select_from(target_cls)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
            )

        _apply_owner_filter = owner_id is not None and (target_entity == "items" or _has_user_filters)

        if _apply_owner_filter:
            base_query = base_query.where(Item.owner_id == owner_id)

        if borrowed_only and owner_id:
            base_query = base_query.where(Item.lent_to_user_id == owner_id)

        if category:
            base_query = base_query.where(Expression.content_type.in_(category))
        if fmt:
            base_query = base_query.where(Manifestation.meta["format"].as_string().in_(fmt))
        if missing_cover:
            base_query = base_query.where(
                or_(
                    Manifestation.cover_url.is_(None),
                    Manifestation.cover_url == "",
                )
            )
        if missing_id:
            base_query = base_query.where(
                or_(
                    Manifestation.isbn13.is_(None),
                    Manifestation.isbn13 == "",
                )
            )

        # User-specific filters: only applied when owner_id is present
        if tags and owner_id:
            base_query = base_query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
            tag_conds = [Tag.name.ilike(t.strip()) for t in tags]
            base_query = base_query.where(or_(*tag_conds))

        if collections and owner_id:
            base_query = base_query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
                UserCollection, UserCollectionItem.collection_id == UserCollection.id
            )
            coll_conds = [UserCollection.name.ilike(c.strip()) for c in collections]
            base_query = base_query.where(or_(*coll_conds))
            base_query = base_query.where(UserCollection.owner_id == owner_id)

        if genres:
            from app.api.filters import apply_genre_filter as _apply_genre_filter

            # Apply genre filter directly on the base query using its Work join
            base_query = _apply_genre_filter(base_query, genres)

        if publishers:
            pub_conds = []
            for p in publishers:
                p_term = f"%{p.strip()}%"
                pub_conds.append(
                    or_(
                        Manifestation.publisher.ilike(p_term),
                        Manifestation.meta["Publisher"].as_string().ilike(p_term),
                        Manifestation.meta["publisher"].as_string().ilike(p_term),
                        db.and_(Expression.content_type == "music", Manifestation.meta["label"].as_string().ilike(p_term)),
                    )
                )
            base_query = base_query.where(or_(*pub_conds))

        if statuses and owner_id:
            status_conds = [Item.status.in_(statuses), Item.collection_status.in_(statuses)]
            base_query = base_query.where(or_(*status_conds))

        return base_query.subquery()

    @staticmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    def get_faceted_stats(
        owner_id: uuid.UUID | None = None,
        category: list[str] | None = None,
        fmt: list[str] | None = None,
        tags: list[str] | None = None,
        collections: list[str] | None = None,
        genres: list[str] | None = None,
        publishers: list[str] | None = None,
        statuses: list[str] | None = None,
        borrowed_only: bool = False,
        missing_cover: bool = False,
        missing_id: bool = False,
        view: str = "items",
    ) -> dict[str, Any]:
        """Return cross-filtered per-facet counts for sidebar faceted navigation.

        The ``view`` parameter controls which FRBR-level entity is counted:
        ``"items"``, ``"manifestations"``, ``"expressions"``, or ``"works"``.
        When no filters are passed, returns global/unfiltered counts at the
        requested level.

        Each facet group's counts are computed excluding that group's own
        filters so that selecting a value within a group (e.g. a genre) does
        not zero out counts for other values in the same group.  All other
        groups' filters are still applied to provide cross-facet narrowing.

        Returns a dict with keys:
          category_counts, format_counts, status_counts,
          collection_counts, tag_counts, genre_counts, publisher_counts
        """
        sa_distinct = distinct
        from sqlalchemy import text

        # Map view to target entity class, ID column, and canonical join path
        _view_config = {
            "works": {
                "cls": Work,
                "from_clause": Work,
                "joins": [
                    (Expression, Expression.work_id == Work.id),
                    (Manifestation, Manifestation.expression_id == Expression.id),
                    (Item, Item.manifestation_id == Manifestation.id),
                ],
                "target_col": Work.id,
                "target_clause": Work.id,
                "subq_col": Work.id,
            },
            "expressions": {
                "cls": Expression,
                "from_clause": Expression,
                "joins": [
                    (Work, Expression.work_id == Work.id),
                    (Manifestation, Manifestation.expression_id == Expression.id),
                    (Item, Item.manifestation_id == Manifestation.id),
                ],
                "target_col": Expression.id,
                "target_clause": Expression.id,
                "subq_col": Expression.id,
            },
            "manifestations": {
                "cls": Manifestation,
                "from_clause": Manifestation,
                "joins": [
                    (Expression, Manifestation.expression_id == Expression.id),
                    (Work, Expression.work_id == Work.id),
                    (Item, Item.manifestation_id == Manifestation.id),
                ],
                "target_col": Manifestation.id,
                "target_clause": Manifestation.id,
                "subq_col": Manifestation.id,
            },
            "items": {
                "cls": Item,
                "from_clause": Item,
                "joins": [
                    (Manifestation, Item.manifestation_id == Manifestation.id),
                    (Expression, Manifestation.expression_id == Expression.id),
                    (Work, Expression.work_id == Work.id),
                ],
                "target_col": Item.id,
                "target_clause": Item.id,
                "subq_col": Item.id,
            },
        }
        cfg = _view_config.get(view, _view_config["items"])
        target_entity = view if view in ("items", "manifestations", "works", "expressions") else "items"

        def _subq(
            exclude_category: bool = False,
            exclude_fmt: bool = False,
            exclude_tags: bool = False,
            exclude_collections: bool = False,
            exclude_genres: bool = False,
            exclude_publishers: bool = False,
            exclude_statuses: bool = False,
        ):
            """Build entity-id subquery with the specified facet groups excluded."""
            # For user-specific facets when unauthenticated, no subquery filtering is possible
            _tags = None if (exclude_tags or not owner_id) else tags
            _collections = None if (exclude_collections or not owner_id) else collections
            _statuses = None if (exclude_statuses or not owner_id) else statuses
            return DataManager._build_item_ids_subq(
                owner_id=owner_id,
                category=None if exclude_category else category,
                fmt=None if exclude_fmt else fmt,
                tags=_tags,
                collections=_collections,
                genres=None if exclude_genres else genres,
                publishers=None if exclude_publishers else publishers,
                statuses=_statuses,
                borrowed_only=borrowed_only,
                missing_cover=missing_cover,
                missing_id=missing_id,
                target_entity=target_entity,
            )

        cat_subq = _subq(exclude_category=True)
        fmt_subq = _subq(exclude_fmt=True)
        tag_subq = _subq(exclude_tags=True)
        coll_subq = _subq(exclude_collections=True)
        genre_subq = _subq(exclude_genres=True)
        pub_subq = _subq(exclude_publishers=True)
        status_subq = _subq(exclude_statuses=True)

        # ── Helpers: per-facet join paths ──────────────────────────────
        def _apply_joins(q, *join_pairs):
            for join_cls, condition in join_pairs:
                q = q.join(join_cls, condition)
            return q

        def _outerjoin_items(q):
            """Outer-join Item so entities without Items are still counted."""
            if target_entity == "works":
                return q.outerjoin(Item, Item.manifestation_id == Manifestation.id)
            if target_entity == "expressions":
                return q.outerjoin(Item, Item.manifestation_id == Manifestation.id)
            if target_entity == "manifestations":
                return q.outerjoin(Item, Item.manifestation_id == Manifestation.id)
            return q  # items: already Item-native

        # ── Join to Expression (needed for category counts) ───────────
        def _join_to_expression(q):
            if target_entity == "works":
                return q.join(Expression, Expression.work_id == Work.id)
            if target_entity == "expressions":
                return q  # Expression is already the from_clause
            if target_entity == "manifestations":
                return q.join(Expression, Manifestation.expression_id == Expression.id)
            return q.join(Manifestation, Item.manifestation_id == Manifestation.id).join(
                Expression, Manifestation.expression_id == Expression.id
            )

        # ── Join to Manifestation (needed for format/publisher counts) ─
        def _join_to_manifestation(q):
            if target_entity == "works":
                return q.join(Expression, Expression.work_id == Work.id).join(Manifestation, Manifestation.expression_id == Expression.id)
            if target_entity == "expressions":
                return q.join(Manifestation, Manifestation.expression_id == Expression.id)
            if target_entity == "manifestations":
                return q  # Manifestation already the from_clause
            return q.join(Manifestation, Item.manifestation_id == Manifestation.id)

        # ── Join to Work (needed for genre counts) ────────────────────
        def _join_to_work(q):
            if target_entity == "works":
                return q  # Work is already the from_clause
            if target_entity == "expressions":
                return q.join(Work, Expression.work_id == Work.id)
            if target_entity == "manifestations":
                return q.join(Expression, Manifestation.expression_id == Expression.id).join(Work, Expression.work_id == Work.id)
            return (
                q.join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
            )

        # ── Full join chain (target → Item, for status/collection/tag) ─
        def _join_full_chain(q):
            if target_entity == "works":
                res = (
                    q.join(Expression, Expression.work_id == Work.id)
                    .join(Manifestation, Manifestation.expression_id == Expression.id)
                    .join(Item, Item.manifestation_id == Manifestation.id)
                )
            elif target_entity == "expressions":
                res = q.join(Manifestation, Manifestation.expression_id == Expression.id).join(
                    Item, Item.manifestation_id == Manifestation.id
                )
            elif target_entity == "manifestations":
                res = q.join(Item, Item.manifestation_id == Manifestation.id)
            else:
                res = q.join(Manifestation, Item.manifestation_id == Manifestation.id)
            if owner_id:
                res = res.where(Item.owner_id == owner_id)
            return res

        subq_filter_col = cfg["subq_col"]

        # ── Category counts (grouped by Expression.content_type) ──────────
        cat_query = (
            select(Expression.content_type, func.count(sa_distinct(cfg["target_clause"])).label("cnt"))  # pylint: disable=not-callable
            .select_from(cfg["from_clause"])
            .where(subq_filter_col.in_(select(cat_subq.c.id)))
            .group_by(Expression.content_type)
        )
        cat_query = _join_to_expression(cat_query)
        cat_rows = db.session.execute(cat_query).all()
        category_counts: dict[str, int] = {}
        for ct, cnt in cat_rows:
            if ct:
                category_counts[ct] = cnt

        # ── Format counts (grouped by Manifestation.meta->'format') ───────
        fmt_query = (
            select(
                Manifestation.meta["format"].as_string(),
                func.count(sa_distinct(cfg["target_clause"])).label("cnt"),  # pylint: disable=not-callable
            )
            .select_from(cfg["from_clause"])
            .where(subq_filter_col.in_(select(fmt_subq.c.id)))
            .group_by(Manifestation.meta["format"].as_string())
        )
        fmt_query = _join_to_manifestation(fmt_query)
        fmt_rows = db.session.execute(fmt_query).all()
        format_counts: dict[str, int] = {}
        for f_val, cnt in fmt_rows:
            if f_val:
                format_counts[f_val] = cnt

        # Normalize format counts: non-canonical raw values are resolved to
        # canonical MediaFormat identifiers and their counts are merged.
        from app.core.format_normalizer import normalize_format_counts

        format_counts = normalize_format_counts(format_counts)

        # ── Status counts (grouped by Item.status + collection_status) ────
        db_statuses = dict.fromkeys(ITEM_STATUSES, 0)
        if owner_id:
            status_query = (
                select(Item.status, func.count(sa_distinct(cfg["target_clause"])).label("cnt"))  # pylint: disable=not-callable
                .select_from(cfg["from_clause"])
                .where(subq_filter_col.in_(select(status_subq.c.id)))
                .group_by(Item.status)
            )
            status_query = _join_full_chain(status_query)
            status_rows = db.session.execute(status_query).all()
            for s, cnt in status_rows:
                if s in db_statuses:
                    db_statuses[s] += cnt

            coll_status_query = (
                select(
                    func.coalesce(Item.collection_status, "available").label("c_status"),
                    func.count(sa_distinct(cfg["target_clause"])).label("cnt"),  # pylint: disable=not-callable
                )
                .select_from(cfg["from_clause"])
                .where(subq_filter_col.in_(select(status_subq.c.id)))
                .group_by(func.coalesce(Item.collection_status, "available"))
            )
            coll_status_query = _join_full_chain(coll_status_query)
            coll_status_rows = db.session.execute(coll_status_query).all()
            for cs, cnt in coll_status_rows:
                if cs in db_statuses:
                    db_statuses[cs] += cnt

        borrowed_count = 0
        if owner_id:
            borrowed_query = (
                select(func.count(sa_distinct(cfg["target_clause"])))  # pylint: disable=not-callable
                .select_from(cfg["from_clause"])
                .where(Item.lent_to_user_id == owner_id)
                .where(subq_filter_col.in_(select(status_subq.c.id)))
            )
            borrowed_query = _join_full_chain(borrowed_query)
            borrowed_count = db.session.execute(borrowed_query).scalar() or 0

        # ── Collection counts ─────────────────────────────────────────────
        collection_counts: dict[str, int] = {}
        if owner_id:
            coll_query = (
                select(UserCollection.name, func.count(sa_distinct(cfg["target_clause"])).label("cnt"))  # pylint: disable=not-callable
                .select_from(cfg["from_clause"])
                .where(subq_filter_col.in_(select(coll_subq.c.id)))
                .group_by(UserCollection.name)
            )
            coll_query = _join_full_chain(coll_query)
            coll_query = coll_query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
                UserCollection, UserCollectionItem.collection_id == UserCollection.id
            )
            coll_rows = db.session.execute(coll_query).all()
            collection_counts = {c: cnt for c, cnt in coll_rows if c}

        # ── Tag counts ────────────────────────────────────────────────────
        tag_counts: dict[str, int] = {}
        if owner_id:
            tag_query = (
                select(Tag.name, func.count(sa_distinct(cfg["target_clause"])).label("cnt"))  # pylint: disable=not-callable
                .select_from(cfg["from_clause"])
                .where(subq_filter_col.in_(select(tag_subq.c.id)))
                .group_by(Tag.name)
            )
            tag_query = _join_full_chain(tag_query)
            tag_query = tag_query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
            tag_rows = db.session.execute(tag_query).all()
            tag_counts = {t: cnt for t, cnt in tag_rows if t}

        # ── Genre counts ──────────────────────────────────────────────────
        genre_counts: dict[str, int] = {}
        _is_pg = db.engine.dialect.name == "postgresql"

        if _is_pg:
            genre_query = (
                select(
                    func.jsonb_array_elements_text(text("works.meta::jsonb->'genres'")).label("genre"),
                    func.count(sa_distinct(cfg["target_clause"])).label("cnt"),  # pylint: disable=not-callable
                )
                .select_from(cfg["from_clause"])
                .where(
                    subq_filter_col.in_(select(genre_subq.c.id)),
                    Work.meta.isnot(None),
                    text("jsonb_typeof(works.meta::jsonb->'genres') = 'array'"),
                )
                .group_by(text("genre"))
                .order_by(func.count(sa_distinct(cfg["target_clause"])).desc())  # pylint: disable=not-callable
            )
            genre_query = _join_to_work(genre_query)
            genre_rows = db.session.execute(genre_query).all()
            genre_counts = {g.strip(): cnt for g, cnt in genre_rows if g and g.strip()}
        else:
            # SQLite fallback: in-memory Counter aggregation.
            from collections import Counter

            # Get target entity IDs from the subquery
            target_ids_result = db.session.execute(select(genre_subq.c.id)).all()
            target_ids = [r[0] for r in target_ids_result]

            if target_ids:
                if target_entity == "works":
                    w_ids = target_ids
                else:
                    w_ids_query = db.session.execute(
                        select(Work.id)
                        .join(Expression, Expression.work_id == Work.id)
                        .join(Manifestation, Manifestation.expression_id == Expression.id)
                        .join(Item, Item.manifestation_id == Manifestation.id)
                        .where(subq_filter_col.in_(target_ids))
                        .distinct()
                    ).all()
                    w_ids = [r[0] for r in w_ids_query]
                if w_ids:
                    works_meta = db.session.execute(select(Work.meta).where(Work.id.in_(w_ids))).all()
                    genre_counter: Counter[str] = Counter()
                    for (meta,) in works_meta:
                        if meta:
                            raw = meta.get("genres") or meta.get("genre")
                            if isinstance(raw, list):
                                for g_val in raw:
                                    if isinstance(g_val, str) and g_val.strip():
                                        genre_counter[g_val.strip()] += 1
                            elif isinstance(raw, str) and raw.strip():
                                genre_counter[raw.strip()] += 1
                    genre_counts = dict(genre_counter.most_common())

        # ── Publisher counts ──────────────────────────────────────────────
        coalesced_pub = func.coalesce(  # pylint: disable=assignment-from-no-return
            Manifestation.publisher,
            Manifestation.meta["Publisher"].as_string(),
            Manifestation.meta["publisher"].as_string(),
            db.case((Expression.content_type == "music", Manifestation.meta["label"].as_string()), else_=None),
        )
        pub_query = (
            select(
                coalesced_pub.label("publisher"), func.count(sa_distinct(cfg["target_clause"])).label("cnt")  # pylint: disable=not-callable
            )
            .select_from(cfg["from_clause"])
            .where(
                subq_filter_col.in_(select(pub_subq.c.id)),
                coalesced_pub.isnot(None),
                coalesced_pub != "",
            )
            .group_by(coalesced_pub)
        )

        def _join_to_expr_and_man(q):
            if target_entity == "works":
                return q.join(Expression, Expression.work_id == Work.id).join(Manifestation, Manifestation.expression_id == Expression.id)
            if target_entity == "expressions":
                return q.join(Manifestation, Manifestation.expression_id == Expression.id)
            if target_entity == "manifestations":
                return q.join(Expression, Manifestation.expression_id == Expression.id)
            return q.join(Manifestation, Item.manifestation_id == Manifestation.id).join(
                Expression, Manifestation.expression_id == Expression.id
            )

        pub_query = _join_to_expr_and_man(pub_query)
        pub_rows = db.session.execute(pub_query).all()
        publisher_counts: dict[str, int] = {p.strip(): cnt for p, cnt in pub_rows if p and p.strip()}

        # ── Append Virtual Intents to counts (when view == 'items' and owner_id) ──
        if owner_id and view == "items":
            intents = (
                db.session.query(UserWorkIntent).filter(UserWorkIntent.user_id == owner_id, UserWorkIntent.status != "fulfilled").all()
            )

            def match_filter(f_list, item_vals):
                if not f_list:
                    return True
                if not item_vals:
                    return False
                f_list_lower = [f.strip().lower() for f in f_list]
                return any(any(f in v.lower() for f in f_list_lower) for v in item_vals if v)

            _INTENT_STATUSES = {"want_to_read", "want_to_listen", "want_to_watch", "want_to_play"}

            for intent in intents:
                work = intent.work
                intent_cats = set()
                intent_formats = set()
                intent_pubs = set()
                for expr in work.expressions:
                    if expr.content_type:
                        intent_cats.add(expr.content_type)
                    for man in expr.manifestations:
                        if man.publisher:
                            intent_pubs.add(man.publisher)
                        if man.meta:
                            for key in ["Publisher", "publisher", "label"]:
                                if key == "label" and expr.content_type != "music":
                                    continue
                                val = man.meta.get(key)
                                if isinstance(val, list):
                                    intent_pubs.update(v for v in val if isinstance(v, str))
                                elif isinstance(val, str):
                                    intent_pubs.add(val)
                        if man.meta and man.meta.get("format"):
                            intent_formats.add(man.meta["format"])

                intent_genres: set[str] = set()
                if work.meta:
                    raw_g = work.meta.get("genres") or work.meta.get("genre")
                    if isinstance(raw_g, list):
                        intent_genres.update(g.strip() for g in raw_g if isinstance(g, str) and g.strip())
                    elif isinstance(raw_g, str) and raw_g.strip():
                        intent_genres.add(raw_g.strip())

                intent_status_match = False
                if not statuses:
                    intent_status_match = True
                else:
                    req_intents = [s for s in statuses if s in _INTENT_STATUSES]
                    if req_intents:
                        intent_status_match = intent.status in req_intents
                    elif "wish_list" in statuses:
                        intent_status_match = True

                # Cross-filter conditions
                cat_match = match_filter(category, intent_cats)
                fmt_match = match_filter(fmt, intent_formats)
                pub_match = match_filter(publishers, intent_pubs)
                genre_match = match_filter(genres, intent_genres)

                # category counts
                if fmt_match and pub_match and genre_match and intent_status_match:
                    for c in intent_cats:
                        category_counts[c] = category_counts.get(c, 0) + 1

                # status counts
                if cat_match and fmt_match and pub_match and genre_match:
                    if intent.status in db_statuses:
                        db_statuses[intent.status] += 1
                    if "wish_list" in db_statuses:
                        db_statuses["wish_list"] += 1

                # genre counts
                if cat_match and fmt_match and pub_match and intent_status_match:
                    for g in intent_genres:
                        genre_counts[g] = genre_counts.get(g, 0) + 1

                # format counts
                if cat_match and pub_match and genre_match and intent_status_match:
                    for f in intent_formats:
                        format_counts[f] = format_counts.get(f, 0) + 1

                # publisher counts
                if cat_match and fmt_match and genre_match and intent_status_match:
                    for p in intent_pubs:
                        publisher_counts[p] = publisher_counts.get(p, 0) + 1

        return {
            "category_counts": category_counts,
            "format_counts": format_counts,
            "status_counts": db_statuses,
            "collection_counts": collection_counts,
            "tag_counts": tag_counts,
            "genre_counts": genre_counts,
            "publisher_counts": publisher_counts,
            "borrowed_count": borrowed_count,
        }


def get_velocity_stats(owner_id: Any) -> list[dict[str, Any]]:
    """Returns monthly item acquisition count for the last 12 months for a given user."""
    owner_val: Any
    if isinstance(owner_id, str):
        try:
            owner_val = uuid.UUID(owner_id)
        except ValueError:
            owner_val = owner_id
    else:
        owner_val = owner_id

    now = datetime.now(UTC)
    months = []
    for i in range(11, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year:04d}-{month:02d}")

    cutoff_date = datetime(int(months[0].split("-")[0]), int(months[0].split("-")[1]), 1, tzinfo=UTC)

    bind = db.session.get_bind()
    dialect_name = bind.dialect.name if bind else "sqlite"
    if dialect_name == "sqlite":
        month_expr = func.strftime("%Y-%m", Item.added_at)
    else:
        month_expr = func.to_char(func.date_trunc("month", Item.added_at), "YYYY-MM")

    stmt = (
        select(month_expr.label("month"), func.count(Item.id).label("count"))  # pylint: disable=not-callable
        .where(Item.owner_id == owner_val, Item.added_at >= cutoff_date)
        .group_by(month_expr)
    )

    results = db.session.execute(stmt).all()
    count_map = {r.month: r.count for r in results if r.month}

    return [{"month": m, "count": count_map.get(m, 0)} for m in months]


def get_distribution_stats(owner_id: Any) -> dict[str, list[dict[str, Any]]]:
    """Returns collection items breakdown by content_type and physical format for a given user."""
    owner_val: Any
    if isinstance(owner_id, str):
        try:
            owner_val = uuid.UUID(owner_id)
        except ValueError:
            owner_val = owner_id
    else:
        owner_val = owner_id

    # 1. By type (Expression.content_type)
    stmt_type = (
        select(Expression.content_type.label("type"), func.count(Item.id).label("count"))  # pylint: disable=not-callable
        .select_from(Item)
        .join(Manifestation, Item.manifestation_id == Manifestation.id)
        .join(Expression, Manifestation.expression_id == Expression.id)
        .where(Item.owner_id == owner_val)
        .group_by(Expression.content_type)
    )
    type_results = db.session.execute(stmt_type).all()
    by_type = [{"type": r.type or "unknown", "count": r.count} for r in type_results]

    # 2. By format (Manifestation.meta['format'])
    format_expr = Manifestation.meta["format"].as_string()
    stmt_format = (
        select(format_expr.label("format"), func.count(Item.id).label("count"))  # pylint: disable=not-callable
        .select_from(Item)
        .join(Manifestation, Item.manifestation_id == Manifestation.id)
        .where(Item.owner_id == owner_val)
        .group_by(format_expr)
    )
    format_results = db.session.execute(stmt_format).all()
    by_format = [{"format": r.format or "book", "count": r.count} for r in format_results]

    return {
        "by_type": by_type,
        "by_format": by_format,
    }
