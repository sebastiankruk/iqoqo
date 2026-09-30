---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

We need to centralize our virtual boundaries and harden API validation while strictly adhering to the FRBR ontology at the Item level. The current system relies on brittle inline validation (e.g., `if item_id <= 0:`) which increases cyclomatic complexity and reduces maintainability. This change will establish a robust foundation for system stability, technical debt reduction, and future ActivityPub federation by introducing CIDOC CRM-compliant item custody event logging.

## What Changes

- Implement an `ItemCustodyEvent` immutable event log table for CIDOC CRM-compliant item custody and history tracking.
- Implement an `EntityAuditLog` table for tracking curation edits and record merges across the Work, Expression, and Manifestation tiers.
- Design and construct a declarative `@require_physical_item` endpoint interceptor decorator (`app/api/decorators.py`) to screen incoming payloads.
- Refactor collection item route handlers (`app/api/items.py`) to strip out inline validation and use the centralized interceptor.
- Introduce validation test scripts ensuring the interceptor correctly rejects illegal states.
- Prepare ActivityPub federation via proper custody tracking exclusively at the Item tier (preserving Work, Expression, and Manifestation layers).

## Capabilities

### New Capabilities

- `item-custody`: CIDOC CRM-compliant immutable event log for item custody and history tracking at the FRBR Item level.
- `entity-audit`: Curation and edit history logging for Work, Expression, and Manifestation tiers.

### Modified Capabilities

- `hardening`: System hardening with centralized API validation using interceptor decorators.

## Impact

- **API Handlers:** `app/api/items.py` route handlers will be refactored to use decorators.
- **Database Schema:** New `ItemCustodyEvent` and `EntityAuditLog` tables will be added.
- **Decorators:** New `app/api/decorators.py` file or module created/modified.
- **Tests:** `tests/test_api_items_validation.py` will be created or updated for robust interceptor rejection tests.
- **E2E:** Playwright tests to validate UI response when the interceptor rejects an invalid state modification.
