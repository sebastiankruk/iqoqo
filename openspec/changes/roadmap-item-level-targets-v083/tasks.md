## 1. Schema and FRBR target integrity

- [ ] 1.1 Add nullable `item_id` to `RoadmapItem`, mapped to the inventory Item table with an indexed, restrictive FK; update the model check constraint to require exactly one of Work, Expression, Manifestation, or Item, and verify model metadata exposes the expected FK/index/check.
- [ ] 1.2 Create a new linear Alembic migration that adds `item_id`, its index/FK, replaces the three-level constraint with the four-level constraint, and changes all target FKs to `RESTRICT`; preserve existing target IDs, preflight invalid cardinality without destructive repair, and verify both upgrade and safe downgrade behavior.
- [ ] 1.3 Make downgrade refuse while any `item_id` target exists and verify it restores the three-level check and prior FK actions when no Item target remains.
- [ ] 1.4 Add database tests proving every single target level persists and zero/multiple targets fail; verify deleting a referenced target is blocked and removing the roadmap entry permits deletion without affecting the roadmap or sibling entries.

## 2. Roadmap API validation, serialization, and entry lifecycle

- [ ] 2.1 Extend create validation to accept exactly one positive integer target ID from all four levels, check referenced catalog entities exist, require Item ownership by the roadmap owner, and verify malformed, missing, ambiguous, nonexistent, virtual, and non-owned Item targets return the specified 400/404 responses.
- [ ] 2.2 Extend roadmap item serialization with nullable `item_id`, `target_type`, and a safe human-readable summary; resolve title/creator and Item edition context and verify old Work/Expression/Manifestation payloads remain compatible.
- [ ] 2.3 Add owner-authorized target replacement and individual entry deletion endpoints; verify target replacement preserves position/status/notes/dates/completion and deletion compacts only the affected roadmap's positions while retaining the target entity.
- [ ] 2.4 Keep reorder/create/list behavior correct across all four target types and verify cross-user create, replace, reorder, and delete attempts return not found without mutation.
- [ ] 2.5 Translate roadmap-target FK violations from Work, Expression, Manifestation, and Item deletion paths to safe HTTP 409 responses; verify unrelated FK failures retain existing handling and no target or roadmap progress is silently deleted.
- [ ] 2.6 Extend backend roadmap tests to cover all target types, exactly-one validation at API and DB levels, serialization, target replacement, entry deletion/order compaction, ownership isolation, and restricted target deletion; run the focused roadmap and ontology suites.

## 3. Owned Item candidate search

- [ ] 3.1 Add an authenticated owner-only filter to `/api/items` that applies `Item.owner_id == current_user` in SQL while retaining search and pagination; verify it excludes borrowed/public copies and does not change default list behavior.
- [ ] 3.2 Extend the React Query item hook/query key with the owner-only option and verify matching request parameters and cache separation in hook tests.
- [ ] 3.3 Test candidate search for duplicate owned copies of one Manifestation, a lent-out copy still owned by the requester, and an Item owned by another user; verify only the authenticated user's physical Item rows are returned.

## 4. Four-level roadmap UI

- [ ] 4.1 Extend roadmap DTOs and mutation hooks for `expression_id`, `item_id`, `target_type`, summary, target replacement, and entry deletion; verify all four IDs and operation payloads are typed and forwarded correctly.
- [ ] 4.2 Add an explicit Work/Expression/Manifestation/Item selector with level-appropriate search results; clear stale selection when the level changes and verify each submitted payload contains exactly one target ID.
- [ ] 4.3 Connect Item candidates to owner-only search and display each choice as an actual copy with title/edition context; verify wishlist intentions and borrowed copies are never shown as selectable targets.
- [ ] 4.4 Render a visible target-level label and contextual target summary on roadmap entries, including an Item/copy distinction; verify existing three-level entries still render and reordering remains intact.
- [ ] 4.5 Add component tests for selecting each target level, switching levels, displaying multiple copies of one edition, Item search loading/empty/error results, and entry target replacement/deletion controls.

## 5. Integration verification

- [ ] 5.1 Extend roadmap E2E coverage to create and display Work, Expression, Manifestation, and owned Item targets, replace a target without losing entry state, remove an entry, and confirm another user's Item cannot be selected.
- [ ] 5.2 Verify referenced-target deletion returns a conflict with roadmap data intact, then remove the entry and confirm deletion succeeds; run the focused backend, frontend, migration, and E2E suites and record any environment-dependent skip.
- [ ] 5.3 Run the repository's applicable lint/type checks for changed backend and frontend modules and verify no edits were made to `security-hardening-v081` artifacts.
