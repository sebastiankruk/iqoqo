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
                    "meta": work.meta,
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
                    "meta": expr.meta,
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
                    "publisher": manif.publisher,
                    "publication_date": (manif.publication_date.isoformat() if manif.publication_date else None),
                    "cover_url": manif.cover_url,
                    "meta": manif.meta,
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
        from sqlalchemy import func, select

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
        intent_count = (
            db.session.execute(select(func.count(UserWorkIntent.id)).where(*intent_filter)).scalar() or 0  # pylint: disable=not-callable
        )
        status_counts["wish_list"] += intent_count

        if owner_id:
            from sqlalchemy import distinct

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
    def get_faceted_stats(
        owner_id: uuid.UUID | None = None,
        category: str | None = None,
        fmt: str | None = None,
        tags: list[str] | None = None,
        collections: list[str] | None = None,
        genres: list[str] | None = None,
        publishers: list[str] | None = None,
        statuses: list[str] | None = None,
        borrowed_only: bool = False,
        missing_cover: bool = False,
        missing_id: bool = False,
    ) -> dict[str, Any]:
        """Return cross-filtered per-facet counts for sidebar faceted navigation.

        When no filters are passed, returns global/unfiltered counts.
        When filters are active, all facet counts are narrowed to the
        matching item subset.

        Returns a dict with keys:
          category_counts, format_counts, status_counts,
          collection_counts, tag_counts, genre_counts, publisher_counts
        """
        from sqlalchemy import func, or_, select

        base_query = (
            select(Item.id)
            .select_from(Item)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .join(Work, Expression.work_id == Work.id)
        )

        if owner_id:
            base_query = base_query.where(Item.owner_id == owner_id)

        if borrowed_only and owner_id:
            base_query = base_query.where(Item.lent_to_user_id == owner_id)

        if category:
            base_query = base_query.where(Expression.content_type == category)
        if fmt:
            base_query = base_query.where(Manifestation.meta["format"].as_string() == fmt)
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

        if tags:
            base_query = base_query.join(ItemTag, Item.id == ItemTag.item_id).join(Tag, ItemTag.tag_id == Tag.id)
            tag_conds = [Tag.name.ilike(t.strip()) for t in tags]
            base_query = base_query.where(or_(*tag_conds))

        if collections:
            base_query = base_query.join(UserCollectionItem, Item.id == UserCollectionItem.item_id).join(
                UserCollection, UserCollectionItem.collection_id == UserCollection.id
            )
            coll_conds = [UserCollection.name.ilike(c.strip()) for c in collections]
            base_query = base_query.where(or_(*coll_conds))
            if owner_id:
                base_query = base_query.where(UserCollection.owner_id == owner_id)

        if genres:
            from app.api.filters import apply_genre_filter as _apply_genre_filter

            genre_query = (
                select(Item.id)
                .select_from(Item)
                .join(Manifestation, Item.manifestation_id == Manifestation.id)
                .join(Expression, Manifestation.expression_id == Expression.id)
                .join(Work, Expression.work_id == Work.id)
            )
            genre_query = _apply_genre_filter(genre_query, genres)
            genre_item_ids = genre_query.subquery()
            base_query = base_query.where(Item.id.in_(select(genre_item_ids.c.id)))

        if publishers:
            pub_conds = [Manifestation.publisher.ilike(f"%{p.strip()}%") for p in publishers]
            base_query = base_query.where(or_(*pub_conds))

        if statuses:
            status_conds = [Item.status.in_(statuses), Item.collection_status.in_(statuses)]
            base_query = base_query.where(or_(*status_conds))

        item_ids_subq = base_query.subquery()
        item_id_col = item_ids_subq.c.id

        # Category counts (grouped by Expression.content_type)
        cat_rows = db.session.execute(
            select(Expression.content_type, func.count(Item.id).label("cnt"))
            .select_from(Item)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .where(Item.id.in_(select(item_id_col)))
            .group_by(Expression.content_type)
        ).all()
        category_counts: dict[str, int] = {}
        for ct, cnt in cat_rows:
            if ct:
                category_counts[ct] = cnt

        # Format counts (grouped by Manifestation.meta->'format')
        fmt_rows = db.session.execute(
            select(Manifestation.meta["format"].as_string(), func.count(Item.id).label("cnt"))
            .select_from(Item)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .where(Item.id.in_(select(item_id_col)))
            .group_by(Manifestation.meta["format"].as_string())
        ).all()
        format_counts: dict[str, int] = {}
        for f_val, cnt in fmt_rows:
            if f_val:
                format_counts[f_val] = cnt

        # Status counts (grouped by Item.collection_status + Item.status)
        db_statuses = dict.fromkeys(ITEM_STATUSES, 0)
        status_rows = db.session.execute(
            select(Item.status, func.count(Item.id).label("cnt")).where(Item.id.in_(select(item_id_col))).group_by(Item.status)
        ).all()
        for s, cnt in status_rows:
            if s in db_statuses:
                db_statuses[s] += cnt
        coll_status_rows = db.session.execute(
            select(Item.collection_status, func.count(Item.id).label("cnt"))
            .where(Item.id.in_(select(item_id_col)))
            .group_by(Item.collection_status)
        ).all()
        for cs, cnt in coll_status_rows:
            if cs in db_statuses:
                db_statuses[cs] += cnt

        # Collection counts
        coll_rows = db.session.execute(
            select(UserCollection.name, func.count(UserCollectionItem.item_id).label("cnt"))
            .select_from(UserCollectionItem)
            .join(UserCollection, UserCollectionItem.collection_id == UserCollection.id)
            .where(UserCollectionItem.item_id.in_(select(item_id_col)))
            .group_by(UserCollection.name)
        ).all()
        collection_counts: dict[str, int] = {c: cnt for c, cnt in coll_rows if c}

        # Tag counts
        tag_rows = db.session.execute(
            select(Tag.name, func.count(ItemTag.item_id).label("cnt"))
            .select_from(ItemTag)
            .join(Tag, ItemTag.tag_id == Tag.id)
            .where(ItemTag.item_id.in_(select(item_id_col)))
            .group_by(Tag.name)
        ).all()
        tag_counts: dict[str, int] = {t: cnt for t, cnt in tag_rows if t}

        # Genre counts
        genre_counts: dict[str, int] = {}
        w_ids_query = db.session.execute(
            select(Work.id)
            .join(Expression, Expression.work_id == Work.id)
            .join(Manifestation, Manifestation.expression_id == Expression.id)
            .join(Item, Item.manifestation_id == Manifestation.id)
            .where(Item.id.in_(select(item_id_col)))
            .distinct()
        ).all()
        w_ids = [r[0] for r in w_ids_query]
        if w_ids:
            works_meta = db.session.query(Work.meta).filter(Work.id.in_(w_ids)).all()
            from collections import Counter

            genre_counter: Counter[str] = Counter()
            for row in works_meta:
                meta = row[0]
                if meta:
                    raw = meta.get("genres") or meta.get("genre")
                    if isinstance(raw, list):
                        for g_val in raw:
                            if isinstance(g_val, str) and g_val.strip():
                                genre_counter[g_val.strip()] += 1
                    elif isinstance(raw, str) and raw.strip():
                        genre_counter[raw.strip()] += 1
            genre_counts = dict(genre_counter.most_common())

        # Publisher counts
        pub_rows = db.session.execute(
            select(Manifestation.publisher, func.count(Item.id).label("cnt"))
            .select_from(Item)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .where(
                Item.id.in_(select(item_id_col)),
                Manifestation.publisher.isnot(None),
                Manifestation.publisher != "",
            )
            .group_by(Manifestation.publisher)
        ).all()
        publisher_counts: dict[str, int] = {p.strip(): cnt for p, cnt in pub_rows if p and p.strip()}

        return {
            "category_counts": category_counts,
            "format_counts": format_counts,
            "status_counts": db_statuses,
            "collection_counts": collection_counts,
            "tag_counts": tag_counts,
            "genre_counts": genre_counts,
            "publisher_counts": publisher_counts,
        }
