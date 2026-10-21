## Context

Delivers the In-App Notification Center idea from the roadmap.

## Goals / Non-Goals

**Goals:**
- Centralized notification inbox with interactive direct action buttons.

**Non-Goals:**
- Native push notifications (reserved for v1.0.0 mobile apps).

## Decisions

### Actionable Payloads
* **Decision**: Store `payload_json` with direct navigation links and action endpoints.
* **Rationale**: Allows one-click approve/reject directly from dropdown.

## Risks / Trade-offs

- ('[Risk] Notification spam', 'Mitigation: Coalesce duplicate events and enforce sender rate limits.')
