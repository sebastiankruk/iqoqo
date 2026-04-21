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
"""Dialect-aware search service.

Routes queries to PostgreSQL FTS when available, with ILIKE fallback for SQLite.
"""

import logging
import os
from typing import Any

from sqlalchemy import bindparam, text

from app.db import db
from app.db.models import Expression, Item, Manifestation, Work

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema prefixes — mirrors the logic in app/db/core.py.
# Raw SQL must qualify table names when PostgreSQL named schemas are in use.
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")
_CATALOG = "catalog." if _USE_PG else ""
_INVENTORY = "inventory." if _USE_PG else ""


class SearchService:
    @staticmethod
    def search_manifestations(q: str, limit: int, offset: int) -> tuple[int, list[int]]:
        """Returns (total_count, list_of_manifestation_ids) ordered by relevance."""
        if not q:
            return 0, []

        if db.engine.dialect.name == "postgresql":
            try:
                return SearchService._pg_manifestation_fts(q, limit, offset)
            except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as exc:
                logger.exception("PostgreSQL FTS failed, falling back to ILIKE", exc_info=exc)
                db.session.rollback()

        return SearchService._ilike_manifestation_search(q, limit, offset)

    @staticmethod
    def search_items(
        q: str,
        user_id: Any,
        limit: int,
        offset: int,
        statuses: list[str] | None = None,
        category: str | None = None,
        format_filter: str | None = None,
    ) -> tuple[int, list[dict]]:
        """Returns (total_count, list_of_item_data_mappings) ordered by relevance."""
        if not q:
            return 0, []

        if db.engine.dialect.name == "postgresql":
            try:
                return SearchService._pg_item_fts(q, user_id, limit, offset, statuses, category, format_filter)
            except (db.exc.SQLAlchemyError, db.exc.DBAPIError) as exc:
                logger.exception("PostgreSQL FTS failed for items, falling back to ILIKE", exc_info=exc)
                db.session.rollback()

        return SearchService._ilike_item_search(q, user_id, limit, offset, statuses, category, format_filter)

    @staticmethod
    def _pg_manifestation_fts(q: str, limit: int, offset: int) -> tuple[int, list[int]]:
        w_tsvector_expr = "w.fts_simple"
        m_tsvector_expr = "m.fts_simple"
        w_search_vector_expr = "w.search_vector"
        tsquery_expr = "websearch_to_tsquery('simple', :q)"
        params = {"q": q, "limit": limit, "offset": offset}

        count_sql = f"""
        SELECT count(*) FROM {_CATALOG}manifestations m
        JOIN {_CATALOG}expressions e ON e.id = m.expression_id
        JOIN {_CATALOG}works w ON w.id = e.work_id
        WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr} OR {w_search_vector_expr} @@ {tsquery_expr})
        """
        rows_sql = f"""
        SELECT m.id, ts_rank({w_tsvector_expr} || {m_tsvector_expr} || coalesce({w_search_vector_expr}, ''::tsvector), {tsquery_expr}) as rank
        FROM {_CATALOG}manifestations m
        JOIN {_CATALOG}expressions e ON e.id = m.expression_id
        JOIN {_CATALOG}works w ON w.id = e.work_id
        WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr} OR {w_search_vector_expr} @@ {tsquery_expr})
        ORDER BY rank DESC
        LIMIT :limit OFFSET :offset
        """
        total = int(db.session.execute(text(count_sql), params).scalar() or 0)
        result_ids = [row[0] for row in db.session.execute(text(rows_sql), params).all()]
        return total, result_ids

    @staticmethod
    def _ilike_manifestation_search(q: str, limit: int, offset: int) -> tuple[int, list[int]]:
        pattern = f"%{q}%"
        base_query = (
            db.session.query(Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .join(Work, Expression.work_id == Work.id)
            .filter(db.or_(Work.title.ilike(pattern), Manifestation.isbn13.ilike(pattern)))
        )
        total = base_query.count()
        result_ids = [row[0] for row in base_query.limit(limit).offset(offset).all()]
        return total, result_ids

    @staticmethod
    def _pg_item_fts(
        q: str,
        user_id: Any,
        limit: int,
        offset: int,
        statuses: list[str] | None = None,
        category: str | None = None,
        format_filter: str | None = None,
    ) -> tuple[int, list[dict]]:
        w_tsvector_expr = "w.fts_simple"
        m_tsvector_expr = "m.fts_simple"
        w_search_vector_expr = "w.search_vector"
        tsquery_expr = "websearch_to_tsquery('simple', :q)"

        params = {"q": q, "limit": limit, "offset": offset, "user_id": user_id}
        extra_filters_sql = " AND i.owner_id = :user_id"

        if statuses:
            params["statuses"] = tuple(statuses)
            extra_filters_sql += " AND (i.status IN :statuses OR i.collection_status IN :statuses)"

        if category:
            params["category"] = category
            extra_filters_sql += " AND e.content_type = :category"

        if format_filter:
            params["format_filter"] = format_filter
            # exact match using JSONB ->> operator in raw SQL
            extra_filters_sql += " AND m.meta ->> 'format' = :format_filter"

        count_sql = f"""
        SELECT count(i.id) FROM {_CATALOG}manifestations m
        JOIN {_CATALOG}expressions e ON e.id = m.expression_id
        JOIN {_CATALOG}works w ON w.id = e.work_id
        JOIN {_INVENTORY}items i ON i.manifestation_id = m.id
        WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr} OR {w_search_vector_expr} @@ {tsquery_expr})
        {extra_filters_sql}
        """
        rows_sql = f"""
        SELECT i.id as item_id, i.owner_id, i.status, i.collection_status, m.id as manifestation_id,
               m.isbn13, w.title, m.cover_url, m.meta as manifestation_meta,
               w.meta as work_meta, i.added_at, i.updated_at,
                ts_rank({w_tsvector_expr} || {m_tsvector_expr} || coalesce({w_search_vector_expr}, ''::tsvector), {tsquery_expr}) as rank
        FROM {_CATALOG}manifestations m
        JOIN {_CATALOG}expressions e ON e.id = m.expression_id
        JOIN {_CATALOG}works w ON w.id = e.work_id
        JOIN {_INVENTORY}items i ON i.manifestation_id = m.id
        WHERE ({w_tsvector_expr} @@ {tsquery_expr} OR {m_tsvector_expr} @@ {tsquery_expr} OR {w_search_vector_expr} @@ {tsquery_expr})
        {extra_filters_sql}
        ORDER BY rank DESC
        LIMIT :limit OFFSET :offset
        """

        count_stmt = text(count_sql)
        rows_stmt = text(rows_sql)

        if statuses:
            count_stmt = count_stmt.bindparams(bindparam("statuses", expanding=True))
            rows_stmt = rows_stmt.bindparams(bindparam("statuses", expanding=True))

        total = int(db.session.execute(count_stmt, params).scalar() or 0)
        results = db.session.execute(rows_stmt, params).mappings().all()
        return total, [dict(r) for r in results]

    @staticmethod
    def _ilike_item_search(
        q: str,
        user_id: Any,
        limit: int,
        offset: int,
        statuses: list[str] | None = None,
        category: str | None = None,
        format_filter: str | None = None,
    ) -> tuple[int, list[dict]]:
        search_term = f"%{q}%"
        # Subquery to get matching item IDs
        matching_items_sub = (
            db.session.query(Item.id)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .join(Work, Expression.work_id == Work.id)
            .filter(
                db.or_(
                    Work.title.ilike(search_term),
                    db.cast(Work.meta["authors"], db.String).ilike(search_term),
                    Manifestation.isbn13.ilike(search_term),
                )
            )
        )

        query = (
            db.session.query(Item, Manifestation, Work)
            .join(Manifestation, Item.manifestation_id == Manifestation.id)
            .join(Expression, Manifestation.expression_id == Expression.id)
            .join(Work, Expression.work_id == Work.id)
            .filter(Item.owner_id == user_id)
            .filter(Item.id.in_(matching_items_sub))
        )

        if statuses:
            query = query.filter(db.or_(Item.status.in_(statuses), Item.collection_status.in_(statuses)))

        if category:
            query = query.filter(Expression.content_type == category)

        if format_filter:
            query = query.filter(Manifestation.meta["format"].as_string() == format_filter)

        total = query.count()
        results = query.limit(limit).offset(offset).all()

        mapped_results = []
        for item, manifestation, work in results:
            mapped_results.append(
                {
                    "item_id": item.id,
                    "owner_id": item.owner_id,
                    "status": item.status,
                    "collection_status": item.collection_status,
                    "manifestation_id": manifestation.id,
                    "isbn13": manifestation.isbn13,
                    "title": work.title,
                    "cover_url": manifestation.cover_url,
                    "manifestation_meta": manifestation.meta,
                    "work_meta": work.meta,
                    "added_at": item.added_at,
                    "updated_at": item.updated_at,
                }
            )
        return total, mapped_results
