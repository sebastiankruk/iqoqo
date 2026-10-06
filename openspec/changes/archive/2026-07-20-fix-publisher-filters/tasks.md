---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Update API Filtering Logic

- [x] 1.1 Update `app/api/manifestations.py` to use `func.coalesce` or `db.or_` across `publisher` and `meta` fields, ensuring `meta['label']` is scoped to `Expression.content_type == 'music'`.
- [x] 1.2 Update `app/api/items.py` to use the same coalesced/conditional filtering for the `intent_query`.
- [x] 1.3 Update `app/core/search_service.py` (`_ilike_manifestation_search`) to include `meta` fields in publisher matching, with the same music scope constraint.

## 2. Update Taxonomy and Faceted Stats

- [x] 2.1 Update `app/api/taxonomies.py` `publishers_query` to extract distinct publishers using `func.coalesce` across `publisher`, `meta['Publisher']`, `meta['publisher']`, and conditionally `meta['label']` when `content_type == 'music'`.
- [x] 2.2 Update `app/core/data_manager.py` (`get_faceted_stats`) to use the coalesced publisher expression (with the `CASE` statement for music) in the `pub_query` `group_by` and `select` clauses.

## 3. Testing and Verification

- [x] 3.1 Verify taxonomy endpoint returns JSON publishers.
- [x] 3.2 Verify faceted stats endpoint accurately counts items with JSON publishers.
- [x] 3.3 Verify items and manifestations endpoints correctly filter by JSON publishers.
