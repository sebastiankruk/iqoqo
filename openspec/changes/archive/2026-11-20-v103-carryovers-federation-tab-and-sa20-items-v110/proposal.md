## Why

Two low-severity items remain open from `v1.0.3` and development notes:
1. `frontend/components/item/item-tabs.tsx` still renders a dead `"Federation Coming Soon"` tab (`FederationTab`) when `FEDERATION_ENABLED=true`, even though federation is fully operational and surfaced in sidebar/admin views.
2. `app/api/items.py` retains 13 legacy SQLAlchemy 1.x `.query` / `db.session.query()` calls outside `add_items_bulk`, flagged in the `v1.0.3` Principal Code Review (`principal-review-release-1.0.3.md`).

## What Changes

- Remove the `FederationTab` component and `"federation"` tab entry from `TABS` in `frontend/components/item/item-tabs.tsx`.
- Surface a concise federated loan / remote provenance badge inside `DetailsTab` in `frontend/components/item/item-tabs.tsx` when an `Item` carries federated custody or remote provenance metadata (`is_borrowed`, `lent_to_name`, or `_provenance`).
- Migrate all remaining legacy `Model.query` / `db.session.query()` calls in `app/api/items.py` to SQLAlchemy 2.0 `select()` / `db.session.execute()` while preserving identical HTTP responses and OpenAPI 3.1 contracts.

## Capabilities

### New Capabilities
- `v103-carryovers-federation-cleanup`: Remove the stale `"Federation Coming Soon"` tab from `ItemTabs` (surfacing federated loan/provenance badges in `DetailsTab`) and complete SQLAlchemy 2.0 `select()` migration in `app/api/items.py`.

### Modified Capabilities

## Impact

- **Frontend (`frontend/`)**: `frontend/components/item/item-tabs.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`, `frontend/__tests__/components/item/`.
- **Backend (`app/`)**: `app/api/items.py`.
- **Tests (`tests/`)**: `tests/test_api_items*.py`, `tests/test_item_is_owner.py`, Vitest item-tabs tests.
