# Design: item metadata staleness after a type change

**See `proposal.md` — Why** for the defect and the measurement. This document sets out the candidate approaches so the analysis in `tasks.md` has something concrete to decide between.

**Nothing here is decided.** The direction is the output of the investigation, not an input to it.

## Context

Two invariants from the current implementation constrain every option:

- **`Item` has no `format` column.** The Manifestation is the only structural carrier record; `Item.meta["format"]` is a denormalised copy written by whatever ingested the item.
- **`_sync_type_meta(meta, current_format, new_type)` already exists and is already the right primitive.** The Manifestation branch calls it and then writes the result back to both `m.format` and `m.meta`. Any propagating option reuses it rather than inventing a second rule.

Three candidate approaches, cheapest first.

## D1: Resolve at the export boundary

`_export_item_row` is the surface where the staleness is actually observable today. Resolving carrier data from the parent Manifestation at export time leaves `Item.meta` alone.

- **Pros:** smallest change. No write path into a user-owned dict. No backfill needed, because exports stop reporting the stale value immediately for every row. Reversible trivially.
- **Cons:** the inconsistency still exists in the database and in any future consumer. It fixes the symptom at the point it is observed, which is legitimate but leaves the trap set for the next reader.
- **Requires:** the export path to have the Manifestation relationship available, or one extra query per row. Batching matters — a naive per-row lookup turns a linear export into an N+1, and this codebase has already had one of those (`fetch_covers.py`, fixed in v0.8.2).

## D2: Propagate the sync into Items

Apply `_sync_type_meta` to `Item.meta` in each existing branch, mirroring what the Manifestation branch already does.

- **Pros:** the copy becomes correct rather than merely ignored. `Item.meta` remains usable by any current or future reader.
- **Cons:** writes into a dict that also holds user-annotated fields. Runs for every Item under the changed Manifestation, in the same transaction as the type change — on a popular work that is a large write. Must decide whether to touch only `type`/`format`/`Format` or to replace the sub-dict.
- **Requires:** an answer to question 3 in `proposal.md`. If an Item's carrier can legitimately differ from its Manifestation's, D2 is actively wrong and would corrupt data.

## D3: Make readers read the Manifestation

Retire the item's copy as a data source. Audit and fix every consumer that consults `Item.meta` for carrier or type data.

- **Pros:** removes the write obligation permanently. Nothing to maintain, nothing to backfill for new writes.
- **Cons:** only as cheap as the read-site audit. If writers keep populating the field, the field still drifts and the fix is incomplete.

## Decisions deferred to the investigation

- **Which of D1/D2/D3.** `tasks.md` gathers the evidence.
- **Whether a backfill accompanies the chosen direction.** Existing rows are already inconsistent; a code fix does not repair them.
- **Scope of the key set for D2.** `type`/`format`/`Format` only, or the whole sub-dict?

## Risks / Trade-offs

- **[Risk] Choosing D2 without answering question 3.** If an Item's carrier can legitimately differ from its Manifestation's, propagating the sync writes wrong data into every Item on the work. Irreversible without a restore, and the user's own annotations in that dict would be at risk.
- **[Risk] Choosing D1 and calling it done.** It silences the export and leaves the database inconsistent. Acceptable only if the export is consciously the whole scope — which should be written down, not assumed.
- **[Risk] D1 introduces an N+1.** Covered in the entry above; verify with a counted-query test, not by reading the code.
- **[Risk] An audit of read sites misses one.** The stale copy is harmless to display and harmful on export, so a missed reader is invisible. The export path is the one that must be checked; the UI readers are the ones that can be assumed correct only because the Manifestation copy is read first.

## Migration Plan

None for D1 or D3. D2 is a single-transaction code change with no schema change, but it writes to existing rows, so a backfill is a separate decision (proposal question 4). All three are cleanly revertible; D2 is the only one where reverting does not un-write already-written values.

## Open Questions

None that can be deferred past the investigation. The five questions in `proposal.md` are the investigation itself.
