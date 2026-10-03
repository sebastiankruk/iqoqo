---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Database Schema

- [x] 1.1 Add `ItemCustodyEvent` model to `app/models/item.py` (or the equivalent module defining models).
- [x] 1.2 Add `EntityAuditLog` model to track curation and merges across Work, Expression, and Manifestation tiers.
- [x] 1.3 Create Alembic migration script to add the `ItemCustodyEvent` and `EntityAuditLog` tables.
- [x] 1.4 Apply Alembic migration to update the database schema.

## 2. API Decorator Implementation

- [x] 2.1 Design and construct the declarative `@require_physical_item` endpoint interceptor decorator in `app/api/decorators.py`.
- [x] 2.2 Add unit tests for the `@require_physical_item` decorator to verify proper error propagation and rejection of invalid item IDs.

## 3. Refactor API Handlers

- [x] 3.1 Refactor collection item route handlers in `app/api/items.py` to strip out brittle inline `if item_id <= 0:` conditions.
- [x] 3.2 Apply the `@require_physical_item` decorator to the refactored handlers in `app/api/items.py`.

## 4. Validation and Testing

- [x] 4.1 Author complete validation test scripts in `tests/test_api_items_validation.py` to ensure API routes reject invalid states cleanly.
- [x] 4.2 Draft Playwright E2E tests validating the UI response when the `@require_physical_item` interceptor rejects an invalid state modification.
