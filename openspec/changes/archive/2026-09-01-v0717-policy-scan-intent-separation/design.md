## Context

The current barcode scanner allows setting a policy for how the scanned item should be ingested. However, policy-driven scans to catalog items might inadvertently clash with user work intents. See `proposal.md` for full motivation.

## Goals / Non-Goals

**Goals:**
- Provide a strict `catalog_only` policy which bypasses user inventory and wishlist generation.
- Ensure strict separation between F3 Manifestations and user-specific Items/UserWorkIntents.

**Non-Goals:**
- Change the behavior of `inventory` or `wishlist` scan policies.
- Alter the underlying FRBR hierarchical structure beyond the specific API isolation.

## Decisions

1. **Policy Name**: We will explicitly look for `policy == "catalog_only"` in `app/api/scanner.py` (replacing or augmenting `catalog`) and route it to early return after Manifestation creation, guaranteeing no `_scan_to_wishlist` or `_scan_to_library` is called.
2. **Creation Isolation**: We will ensure that `app/core/frbr_service.py` Manifestation creation methods do not auto-instantiate `Item` or `UserWorkIntent` rows. If there are any default hooks doing so, we will bypass them.
3. **Response Schema**: The response for `catalog_only` will omit `item_id` and `intent_id` and set `action` to `"cataloged"`.

## Risks / Trade-offs

- **Risk**: Clients expecting `policy="catalog"` might break if we change it exclusively to `catalog_only`.
  - **Mitigation**: We will support both `"catalog"` and `"catalog_only"` in the handler, but enforce the strict isolation behavior for both.

## Migration Plan

No database migration is required. The changes are strictly confined to API logic.
