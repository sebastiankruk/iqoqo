---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Core Data Manager Adjustments

- [x] 1.1 In `app/core/data_manager.py`, update `_build_item_ids_subq` to only require an `INNER JOIN` to `Item` when item-specific filters are active, avoiding unconditional `INNER JOIN` on global views.
- [x] 1.2 In `app/core/data_manager.py`, verify `get_faceted_stats` correctly aggregates counts for non-item views (`Works`, `Expressions`, `Manifestations`) so that they represent global totals, utilizing `LEFT JOIN` as appropriate.

## 2. API Endpoint Cross-FRBR Filtering Fixes

- [x] 2.1 In `app/api/works.py`, modify the `statuses_list` condition to filter using `or_(Item.status.in_(statuses_list), Item.collection_status.in_(statuses_list))`.
- [x] 2.2 In `app/api/manifestations.py`, modify the `statuses_list` condition to filter using `or_(Item.status.in_(statuses_list), Item.collection_status.in_(statuses_list))`.
- [x] 2.3 Identify any similar logic in `app/api/expressions.py` (if it exists) and modify the `statuses_list` condition to also check `Item.collection_status`.

## 3. Testing and Validation

- [x] 3.1 Run tests for `data_manager.py` to confirm facet counts accurately count distinct entities on Global Library views without improperly restricting to user items.
- [x] 3.2 Run tests for main catalog queries to ensure cross-FRBR filtering by collection status (e.g., `wish_list`) returns appropriate parent entities.
