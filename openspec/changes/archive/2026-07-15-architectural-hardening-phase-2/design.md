---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

The current backend API validation heavily relies on inline logic (e.g., `if item_id <= 0:`) within route handlers (`app/api/items.py`). This increases cyclomatic complexity, makes handlers brittle, and violates DRY principles. Furthermore, to prepare for ActivityPub federation, we need a CIDOC CRM-compliant audit trail for physical/digital items. The FRBR ontology strictly dictates that this event log applies at the Item tier only, preserving the integrity of Work, Expression, and Manifestation layers.

## Goals / Non-Goals

**Goals:**

- Replace inline API validation for items with a centralized, declarative decorator pattern (`@require_physical_item`).
- Reduce cyclomatic complexity in `app/api/items.py`.
- Implement `ItemCustodyEvent` database table for immutable tracking of item custody and history.
- Add robust validation testing via Pytest and E2E testing via Playwright to ensure the interceptor properly rejects invalid states.

**Non-Goals:**

- Applying the `ItemCustodyEvent` log to Work, Expression, or Manifestation tiers (custody applies to physical/digital possession only. Curation is handled by the new `EntityAuditLog`).
- Altering the existing UI functionality (we are only hardening the backend and ensuring UI handles failures gracefully).
- Implementing full ActivityPub federation in this phase (we are only laying the groundwork).

## Decisions

**1. Declarative Interceptor Decorator (`@require_physical_item`)**

- **Decision:** Extract item-level boundary checks into a Python decorator that wraps Flask route handlers.
- **Rationale:** Separates business logic from request validation, adhering to DRY and making handlers purely focused on execution.
- **Alternative Considered:** A centralized middleware approach. Rejected because we need precise control over which specific routes require this validation, and a decorator offers fine-grained, explicit application.

**2. `ItemCustodyEvent` Immutable Event Log**

- **Decision:** Create an append-only SQL table for custody events mapped specifically to the `Item` entity.
- **Rationale:** Meets CIDOC CRM compliance for provenance and custody tracking. Immutability ensures audit trails are not tampered with, which is crucial for future ActivityPub trust federation.
- **Alternative Considered:** Adding JSON/JSONB logging columns directly to the `Item` table. Rejected because it would bloat the `Item` row and make temporal queries inefficient.

**3. `EntityAuditLog` for Curation History**

- **Decision:** Create a separate `EntityAuditLog` table for tracking metadata edits and record merges at the Work, Expression, and Manifestation tiers.
- **Rationale:** In the FRBR ontology, abstract works and publication blueprints cannot be "possessed", but they are heavily curated. A dedicated audit log preserves this curation history independently from item custody, satisfying the need to track merges and updates securely.
- **Alternative Considered:** Combining both logs into one generic `HistoryEvent` table. Rejected because Custody and Curation have fundamentally different metadata shapes (e.g., Custody involves condition and location; Curation involves field diffs and conflict resolution).

## Risks / Trade-offs

- **[Risk] Interceptor silently swallowing exceptions** → Mitigation: Ensure the decorator propagates specific, formatted JSON error payloads (e.g., `{"error": "description", "code": 400}`) and write dedicated Pytest cases asserting proper 4xx/5xx status codes.
- **[Risk] Database bloat with immutable event log** → Mitigation: Use optimal indices on the `ItemCustodyEvent` table (e.g., indexing `item_id` and `timestamp`).
