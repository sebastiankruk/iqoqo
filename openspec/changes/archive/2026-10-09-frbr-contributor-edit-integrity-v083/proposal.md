## Why

Bundled critical bugfixes on FRBR editor and contributor handling:
1. (#bugs #critical #v081): "After editing - Work (changing authors `["Remigiusz Mr\u00f3z"]` to `Remigiusz Mróz`) manifestation does not load - until they are reset, work and manifestation are saved, and some time passes".
2. (#bugs #v080): "FRBR editor - authors and other now require JSON formatting which is very bad UX and if value is provided like Firstname Last name, it is incorrectly rendered - only first capital letter ... and manifestation can't be rendered".
3. (#ux #bugs #v081): "New editor FRBR level selector - weird layout where level selector is on the right ... hanging".
Release planning: v0.8.x, C60 (target v0.8.3).

Premises verified against code:
- **Confirmed: Unsafe author extraction in manifestation API.** In `app/api/manifestations.py:215,300`, `authors = work.meta.get("authors", []) if work.meta else []`. If `work.meta["authors"]` was persisted as a string (e.g. `"Remigiusz Mróz"` or stringified JSON `"[\"Remigiusz Mróz\"]"`), Python passes a `str`. In frontend JavaScript/TypeScript, calling `.map()` or `.join()` on a string either crashes (`authors.map is not a function`), breaking manifestation load, or iterates characters individually (`'R', 'e', 'm', ...`).
- **Confirmed: Contributor-meta sync gap.** `app/core/frbr_service.py:1032` commits `work.meta` before reconciling `sync_entity_contributions`, and never backfills `work.meta["authors"]` from relational contributor rows.
- **Confirmed: Level selector CSS hanging layout.** In `frontend/components/admin/frbr-editor.tsx:499-520`, the level selector container uses `flex justify-between items-center bg-muted/50 p-2 rounded-lg` with an absolute/hanging alignment relative to the tree view beneath it.

## What Changes

- **Backend Defensive Deserialization:** In `app/api/manifestations.py` and `app/core/frbr_service.py`, add `normalize_authors_list()` ensuring `authors` is ALWAYS a `list[str]`. Safely parse JSON strings, unicode escapes (`\u00f3`), and comma-separated strings.
- **Relational Contributor Synchronization:** In `update_work()`, automatically synchronize `work.meta["authors"]` with `WorkContribution` rows so metadata and relational joins never diverge.
- **Data Repair ETL Task:** Provide an idempotent ETL task in `app/core/tasks.py` (or script `scripts/repair_frbr_authors.py`) to sanitize legacy corrupted `authors` fields in `work.meta` with dry-run support.
- **Frontend Level Selector Layout Fix:** Realign the FRBR level selector in `frontend/components/admin/frbr-editor.tsx` to flow naturally into the card/tree container layout without right-hanging gaps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (`skip_specs: true` has been set).

## Impact

- **Backend:** `app/api/manifestations.py`, `app/core/frbr_service.py`, `app/api/admin.py`.
- **Frontend:** `frontend/components/admin/frbr-editor.tsx`, `frontend/components/admin/frbr/types.ts`.
- **Tests:** Pytest for author editing roundtrip with unicode, strings, lists, and manifestation detail loading; Vitest for editor form submission and level selector layout rendering.
