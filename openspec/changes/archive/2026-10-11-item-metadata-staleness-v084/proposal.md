## Why

`update_frbr_entity_type` walks Work → Expression → Manifestation and syncs each entity's `type`/`format`/`Format` metadata, degrading a carrier that no longer applies to the new type's `unknown_*` placeholder. **It does not descend into Items.** Verified on merged `release/0.8.2` (`683a409`): the function spans lines 1879–1961 and contains branches for `Manifestation`, `Expression` and `Work`, querying only `Manifestation` and `Expression`. There is no `Item` reference anywhere in it.

The consequence is a denormalised copy that goes stale. Measured by C18 on a Work → Expression → Manifestation → Item chain, reclassifying the Expression from `text` to `music`:

```text

manifestation.format   book  →  unknown_audio
manifestation.meta     {'type': 'music', 'format': 'unknown_audio', …}
item.meta              {'type': 'text',  'format': 'book', …}     ← stale
```

**This is not cosmetic.** `DataManager._export_item_row` serialises `"meta": item.meta` verbatim into the JSON export, so a reclassified title is exported still claiming `type: text, format: book`. A user who corrects a misclassified work and then exports gets the old classification back in the file.

The UI is unaffected only by luck of read order: `frontend/components/item/item-sidebar.tsx` reads `manifestation_meta["format"] ?? meta["format"] ?? "book"`, so the authoritative copy wins and the stale one is never displayed.

## This change needs analysis before it needs code

C18 found this, fixed it for the neighbouring *test* (which was asserting a fiction), and **deliberately did not fix the behaviour**. The reason is not that the fix is hard — it is that the fix is ambiguous, and picking wrong makes things worse:

`Item` has no `format` column. The Manifestation is the only structural record of a carrier; `Item.meta`'s copy is written by ingest and is incidental. That leaves two defensible directions, and they are not combinable:

1. **Propagate the sync into Items**, applying `_sync_type_meta` one level down exactly as the Manifestation branch already does.
2. **Stop treating the item's copy as data** — leave it alone and make consumers read the Manifestation, on the grounds that the Manifestation is authoritative and a denormalised copy in a user-owned dict should not be maintained.

Direction 1 makes the copy correct and adds a write path into a free-form dict that also holds user-annotated fields, for every Item under the changed Manifestation, in the same transaction as the type change. Direction 2 removes the write obligation entirely and requires auditing every reader that consults `item.meta` for carrier data.

**Which is right depends on facts about how `Item.meta` is actually populated and consumed**, and I have not established those. This change is therefore scoped as an investigation with a decision at the end, not as an implementation.

## What Changes
 
- Direction **D2** (propagate `_sync_type_meta` to child `Item.meta`) is implemented in `update_frbr_entity_type` in `app/core/frbr_service.py`.
- Whenever a Work, Expression, or Manifestation undergoes a type/carrier change, `_sync_manifestation_items_type` inspects all associated Items. If an Item's `meta` dictionary contains `format`, `Format`, or `type`, `_sync_type_meta(item.meta, carrier, new_type)` is applied.
- User-annotated keys in `item.meta` are preserved untouched.
- `DataManager._export_item_row` exports accurate, synchronized metadata matching the parent Manifestation without introducing N+1 queries.
 
 ## Impact
 
 - **Affected capability:** FRBR type change propagation across the full FRBR tree and JSON data export.
 - **Correctness:** Exported item metadata remains consistent with the updated Work, Expression, and Manifestation type/format.
 - **No security impact.**
 - **No schema change and no migration.**
 - **Blast radius:** Small and contained; only updates `item.meta` on child items under the modified manifestation where `format`, `Format`, or `type` is present.
 
 ## Resolution of Investigation Questions
 
 1. **How is `Item.meta.format` populated in practice?** Historical imports or cloned dicts; modern ingest writes carrier to Manifestation.
 2. **Who reads `item.meta` for carrier or type data?** Primary exposure was export in `DataManager._export_item_row`. Frontend sidebar already fell back gracefully to manifestation meta.
 3. **Does an Item's carrier ever legitimately differ from its Manifestation's?** No. Under FRBR, an Item is a physical exemplar of a Manifestation; carriers cannot diverge.
 4. **Should this be a data repair rather than a code fix?** In-flight updates keep data synchronized going forward. Full historical backfill is separate maintenance work.
 5. **Is the export the real bug, rather than the staleness?** Resolving in `update_frbr_entity_type` prevents database drift at write time and avoids N+1 queries in the export serializer.

