## Why

Policy-driven scanning currently risks colliding with personal UserWorkIntent (wishlist) states. By enforcing strict isolation between policy scanning and user intent, we preserve the FRBR ontology integrity where policy scans are purely Manifestation-level operations, whereas UserWorkIntent and Item records represent user-level ownership intent. 

## What Changes

- Add strict isolation handling for `policy="catalog_only"` in `app/api/scanner.py`.
- Ensure that when scanning with `policy="catalog_only"`, a Manifestation is created or linked, but no rows are inserted into `inventory.items` or `inventory.user_work_intents`.
- Leave regular scanning behavior intact so it still creates `Items` or `UserWorkIntents` as expected.

## Capabilities

### Modified Capabilities
- `policy-scanning`: Scanning with `policy="catalog_only"` must exclusively create/link a Manifestation without generating `inventory.items` or `inventory.user_work_intents` records.

## Impact

- `app/api/scanner.py`: Updated to correctly isolate `catalog_only` policy.
- `app/core/frbr_service.py`: Prevent auto-creation of Items in the Manifestation creation path.
- Test suites covering scanner policy isolation.
