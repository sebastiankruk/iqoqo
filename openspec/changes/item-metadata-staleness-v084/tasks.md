# Tasks: item metadata staleness after a type change

This list is an **investigation**, not an implementation. Sections 1–3 produce the evidence; section 4 is the decision; sections 5+ only apply once a direction is chosen and this file is revised.

## 1. Establish the writers

- [ ] 1.1 Find every code path that writes `format`, `Format` or `type` into `Item.meta`. Candidates to check at minimum: `scripts/restore_covers.py`, `app/core/data_manager.py:import_data()`, the scanner ingest path, `get_or_create_book_manifestation`, and any admin edit endpoint that accepts arbitrary `meta`.
- [ ] 1.2 For each writer, record whether it copies the value from the Manifestation (so the copy is intended to mirror) or sets it independently (so it is a separate fact that merely looks duplicated).
- [ ] 1.3 **State the answer to proposal question 1 explicitly:** if no writer populates the field any more, say so and stop — the fix is then trivial and the investigation is over.

## 2. Establish the readers

- [ ] 2.1 Find every consumer that reads `format`/`Format`/`type` from `Item.meta` **without first consulting the Manifestation**. `frontend/components/item/item-sidebar.tsx` is already known to be correct (`manifestation_meta["format"] ?? meta["format"]`).
- [ ] 2.2 Confirm the export path is the only currently-harmful reader by checking `app/api/works.py` and any search or index build that reads item metadata directly.
- [ ] 2.3 State the answer to proposal question 2 as a list, or "none beyond the export".

## 3. Settle the premise

- [ ] 3.1 Answer proposal question 3: **can an Item's carrier legitimately differ from its Manifestation's?** This is the gate on the whole change. If yes, the copy is not stale data and the premise of every propagating option collapses.
- [ ] 3.2 Answer proposal question 4: is a backfill in scope alongside whichever direction is chosen, or separate work?
- [ ] 3.3 Reproduce the divergence on the merged branch as an executable check, so the fix has something to be proved against. `tests/test_frbr_type_change.py::test_item_level_metadata_is_not_propagated` already asserts the current behaviour and that the two copies disagree — confirm it still passes on `release/0.8.2` before relying on it.

## 4. Decide

- [ ] 4.1 Choose **D1** (resolve at export), **D2** (propagate into `Item.meta`) or **D3** (retire the copy as a read source). Record the choice, the evidence from sections 1–3 that drove it, and what was rejected.
- [ ] 4.2 Revise `proposal.md` and `design.md` to match the decision, replacing the candidate framing with the chosen direction. Do not leave three options standing after a decision exists.
- [ ] 4.3 **Get the decision reviewed before writing code.**

## 5. Implement — only after 4.3

- [ ] 5.1 Write the failing test first. For D1, assert the export resolves the carrier from the Manifestation after a type change. For D2, assert `Item.meta` is updated. For D3, assert each reader resolves from the Manifestation.
- [ ] 5.2 Revert the fix and confirm the test fails, then restore.
- [ ] 5.3 For D1 specifically: a counted-query assertion that the export does not become N+1. This codebase has had that defect before and the symptom is invisible in functional tests.
- [ ] 5.4 Full backend suite green, plus a frontend run if any reader changes.
- [ ] 5.5 Record in `docs/CHANGELOG.md` which direction was taken, and — if the chosen direction leaves existing rows inconsistent — say that plainly rather than implying the data is now clean.
