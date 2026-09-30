---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Backend Filter Query Composition

- [x] 1.1 Locate the query building logic for filtering Works and Expressions (likely in `backend/app/api/works.py`, `backend/app/api/expressions.py`, or a shared query builder for faceted search).
- [x] 1.2 Identify where the "On Shelf" (status/location) filter and the "Process" filter are appended to the query.
- [x] 1.3 Ensure that when both filters are present, they are applied conjunctively (AND) to the same underlying Item subquery/join, rather than disjunctively or having one overwrite the other.

## 2. Validation

- [x] 2.1 Verify that viewing Works with "On Shelf" selected returns only items on the shelf.
- [x] 2.2 Verify that viewing Works with "Unread" selected returns only unread items.
- [x] 2.3 Verify that viewing Works with BOTH "On Shelf" and "Unread" selected returns ONLY items that are both on the shelf and unread.
- [x] 2.4 Add or update backend tests to cover the intersection of multiple cross-FRBR filters (e.g., status + process).
