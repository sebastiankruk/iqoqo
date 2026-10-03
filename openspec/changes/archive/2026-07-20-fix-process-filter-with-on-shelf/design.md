---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

When viewing Works or Expressions in the library, users can filter by item-level attributes such as "On Shelf" (a storage location or collection status concept) and "Process" (e.g., Unread, Read, Want to Read). Currently, when a user selects both "On Shelf" and a "Process" filter simultaneously, the Process filter is ignored and all items matching "On Shelf" are returned.

## Goals / Non-Goals

**Goals:**

- Ensure that multiple cross-FRBR filters (like "On Shelf" and "Process") are combined using a logical AND operation.
- Users should be able to filter for Works/Expressions that have associated Items which are BOTH "On Shelf" AND "Unread".

**Non-Goals:**

- Altering the general query structure for basic manifestation listing.

## Decisions

- **Filter Composition**: The backend query building logic for Works and Expressions needs to be updated. When generating the EXISTS clause or JOIN condition that checks for associated Items matching the user's criteria, all selected item-level filters (Process, Status, Location) must be composed with `AND` within the subquery or JOIN condition. Currently, they might be joined using an `OR` or one filter might be accidentally overriding the other.

## Risks / Trade-offs

- [Risk] Composing multiple Item conditions might lead to complex subqueries impacting performance. → [Mitigation] Ensure appropriate indexes exist on the `Item` table for `process`, `status`, and `location` columns.
