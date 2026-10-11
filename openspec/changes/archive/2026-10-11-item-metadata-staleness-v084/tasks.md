# Tasks: item metadata staleness after a type change

This list is an **investigation**, not an implementation. Sections 1–3 produce the evidence; section 4 is the decision; sections 5+ only apply once a direction is chosen and this file is revised.

## 1. Establish the writers

- [x] 1.1 Find every code path that writes `format`, `Format` or `type` into `Item.meta`. Candidates to check at minimum: `scripts/restore_covers.py`, `app/core/data_manager.py:import_data()`, the scanner ingest path, `get_or_create_book_manifestation`, and any admin edit endpoint that accepts arbitrary `meta`.
- [x] 1.2 For each writer, record whether it copies the value from the Manifestation (so the copy is intended to mirror) or sets it independently (so it is a separate fact that merely looks duplicated).
- [x] 1.3 **State the answer to proposal question 1 explicitly:** Ingest/scanner paths now write `format`/`type` to Manifestation only; `Item.meta` receives format/type only from historical imports or initial clones. No new writer sets divergent item carriers.

## 2. Establish the readers

- [x] 2.1 Find every consumer that reads `format`/`Format`/`type` from `Item.meta` **without first consulting the Manifestation**. `frontend/components/item/item-sidebar.tsx` is already known to be correct (`manifestation_meta["format"] ?? meta["format"]`).
- [x] 2.2 Confirm the export path is the only currently-harmful reader by checking `app/api/works.py` and any search or index build that reads item metadata directly.
- [x] 2.3 State the answer to proposal question 2 as a list, or "none beyond the export". Export path in `DataManager._export_item_row` was the primary observable defect where stale `item.meta` escaped.

## 3. Settle the premise

- [x] 3.1 Answer proposal question 3: **can an Item's carrier legitimately differ from its Manifestation's?** No. Under FRBR ontology, an Item is a physical exemplar of a Manifestation; it cannot legitimately possess a carrier conflicting with its parent Manifestation.
- [x] 3.2 Answer proposal question 4: is a backfill in scope alongside whichever direction is chosen, or separate work? Separate work / deferred; active sync on `update_frbr_entity_type` repairs on type modification.
- [x] 3.3 Reproduce the divergence on the merged branch as an executable check, so the fix has something to be proved against. Tested in `tests/test_frbr_type_change.py::test_item_level_metadata_is_not_propagated` (updated to assert sync behavior and export parity).

## 4. Decide

- [x] 4.1 Choose **D1** (resolve at export), **D2** (propagate into `Item.meta`) or **D3** (retire the copy as a read source). Direction **D2** chosen: propagate `_sync_type_meta` to child Items' metadata when `format`, `Format`, or `type` is present. Preserves user annotations while ensuring consistency in both database and export without N+1 query penalties.
- [x] 4.2 Revise `proposal.md` and `design.md` to match the decision, replacing the candidate framing with the chosen direction. Do not leave three options standing after a decision exists.
- [x] 4.3 **Get the decision reviewed before writing code.** Decision reviewed and approved.

## 5. Implement — only after 4.3

- [x] 5.1 Write the failing test first. For D2, assert `Item.meta` is updated and export matches.
- [x] 5.2 Revert the fix and confirm the test fails, then restore. Confirmed failure (`assert 'book' == 'unknown_audio'`).
- [x] 5.3 For D1 specifically: N/A since D2 chosen (zero extra N+1 queries introduced).
- [x] 5.4 Full backend suite green, plus a frontend run if any reader changes.
- [x] 5.5 Record in `docs/CHANGELOG.md` which direction was taken, and — if the chosen direction leaves existing rows inconsistent — say that plainly rather than implying the data is now clean.

