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

- **Nothing yet.** This change documents the defect, the evidence, and the two candidate directions, and asks the questions that decide between them.
- The questions are the deliverable. Once they are answered, the proposal is revised with the chosen direction before any code is written.

## Impact

- **Affected capability:** the FRBR type-change path and, downstream of it, data export.
- **Correctness:** exported item metadata can misreport the type and carrier of a reclassified title.
- **No security impact.** No authentication, authorisation, or input-handling concern.
- **No schema change and no migration** under either direction.
- **Blast radius:** direction 1 writes to every `Item.meta` beneath a changed Manifestation — potentially thousands of rows in one transaction. Direction 2 touches only read sites.

## Questions to answer before this becomes an implementation

1. **How is `Item.meta.format` populated in practice?** Ingest adapters, `import_data()`, the scanner, and user edits are all candidates. If nothing writes it any more, direction 1 is maintaining a field nobody uses and direction 2 is clearly right. If several writers do, direction 2 is a larger audit than it looks.
2. **Who reads `item.meta` for carrier or type data, outside the sidebar's already-correct read order?** Anything found is a candidate for divergence after a type change, and each one needs its own check.
3. **Does an Item's carrier ever legitimately differ from its Manifestation's?** An Item is the physical object; a Manifestation describes the edition. If a user may attach a copy of a book to a manifestation whose carrier metadata is about something else, then "the copy" is not stale at all and the premise collapses.
4. **Should this be a data repair rather than a code fix?** Existing rows are already inconsistent. Correcting them on the next type change only fixes rows touched from now on; a one-off backfill would cover the rest. Those are different pieces of work.
5. **Is the export the real bug, rather than the staleness?** If only the export surface matters, the minimal correct fix is to resolve carrier data at export time from the Manifestation, leaving `Item.meta` untouched. That is smaller than both directions above and should be considered first.
