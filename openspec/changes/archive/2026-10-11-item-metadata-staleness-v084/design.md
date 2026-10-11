# Design: item metadata staleness after a type change

**See `proposal.md` — Why** for the defect and the measurement. This document sets out the candidate approaches so the analysis in `tasks.md` has something concrete to decide between.

**Nothing here is decided.** The direction is the output of the investigation, not an input to it.

## Context

Two invariants from the current implementation constrain every option:

- **`Item` has no `format` column.** The Manifestation is the only structural carrier record; `Item.meta["format"]` is a denormalised copy written by whatever ingested the item.
- **`_sync_type_meta(meta, current_format, new_type)` already exists and is already the right primitive.** The Manifestation branch calls it and then writes the result back to both `m.format` and `m.meta`. Any propagating option reuses it rather than inventing a second rule.

Three candidate approaches, cheapest first.

## Chosen Direction: D2 (Propagate Sync into Items)
 
 Apply `_sync_type_meta` to `Item.meta` in `update_frbr_entity_type`, mirroring what the Manifestation branch already does.
 
 - **Decision Rationale:**
   - Direction D1 (resolve only at export) was rejected because leaving the database permanently inconsistent leaves a latent bug for any other caller or query.
   - Direction D3 (remove from readers) was rejected because leaving dead/stale copies in stored item metadata creates drift without saving complexity.
   - D2 ensures that when a Work, Expression, or Manifestation changes its type or carrier, all child Items with carrier/type keys in `Item.meta` (`format`, `Format`, `type`) have those specific keys synchronized via `_sync_type_meta` in the same transaction.
   - User-annotated metadata keys in `Item.meta` are preserved untouched.
   - No N+1 queries are added to the export path.
 
 ## Implementation Details
 
 - In `app/core/frbr_service.py`:
   - Added helper `_sync_manifestation_items_type(manifestation_id, carrier, new_type)`.
   - Iterates through `Item` rows linked to the manifestation.
   - For each item where `item.meta` is a dict and has any of `format`, `Format`, or `type`:
     - Creates a copy of `item.meta`.
     - Calls `_sync_type_meta(i_meta, carrier, new_type)`.
     - Assigns back `item.meta = i_meta` and flags modified session state.
   - Called from `update_frbr_entity_type` in the `Manifestation`, `Expression`, and `Work` branches.

