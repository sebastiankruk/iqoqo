## Context

The current `RoadmapItem` has nullable Work, Expression, and Manifestation foreign keys and a check constraint requiring one non-null target. The API accepts those three keys on entry creation and serializes them, while the roadmap UI currently searches only Manifestations. `Item` is a physical exemplar linked to a Manifestation and owned by a user; the existing authenticated item-list API supports search/pagination but can include borrowed Items. See `proposal.md` and `specs/reading-roadmaps/item-level-targets/spec.md` for scope and observable behavior.

The v0.8.1 relation-management migration currently uses `ON DELETE SET NULL` for roadmap target FKs. With an exactly-one-target check, deleting a sole referenced target already fails when the FK tries to null the only populated target. This change makes that effective restriction explicit and consistent for all four target levels.

## Goals / Non-Goals

**Goals:**
- Add an actual `Item` FK while preserving all existing target assignments and response fields.
- Make the exactly-one-of-four rule consistent in the SQLAlchemy model, Alembic schema, API validation, and UI state.
- Keep item-target lookup and mutations owner-scoped, and retain roadmap progress when a catalog/inventory target is deleted.
- Support individual roadmap-entry target replacement and deletion, allowing users to deliberately detach a target before deleting its FRBR record.

**Non-Goals:**
- No changes to wishlist intent semantics or creation of placeholder physical copies.
- No broader FRBR reassignment/merge/split changes, no changes to the v0.8.1 `security-hardening-v081` scope, and no new roadmap status lifecycle or general notes/date editing feature.
- No redesign of roadmap sharing or public access.

## Decisions

1. **Add nullable `item_id` and replace the target check with a four-way cardinality check.** The column references the physical inventory Item primary key (PostgreSQL `inventory.items.id`, SQLite unqualified `items.id`) and receives an index for target lookup and FK enforcement. The check expression counts non-null `work_id`, `expression_id`, `manifestation_id`, and `item_id` and requires the sum to equal one. It remains an integer FK, not a polymorphic string or a link to wishlist intent.
   - *Alternative considered:* store target type plus one generic ID. Rejected because it loses database-enforced referential integrity to four FRBR tables.

2. **Use restrictive deletion for all four target FKs.** Change the three existing target FK actions from `SET NULL` to `RESTRICT` and define the new Item FK as `RESTRICT`. This avoids violating the exactly-one check, preserves target and roadmap progress, and means deleting the roadmap entry is the explicit detach step. Target-deletion endpoints must translate this FK conflict to HTTP 409 with a safe message. Do not cascade-delete roadmap entries or null their target.
   - *Alternative considered:* cascade-delete the roadmap association. Rejected because it silently discards entry notes/status/completion and would leave sequence positions to be repaired after external target deletion. `SET NULL` cannot coexist with exact-one integrity.

3. **Keep existing target IDs and add a derived discriminator/summary.** Roadmap responses continue to include all four nullable ID keys, exactly one populated, and add `target_type` (`work`, `expression`, `manifestation`, or `item`) plus a human-readable summary. Title/creator resolution follows the selected FRBR node to its Work; Item summaries additionally identify the record as the user's particular copy and show edition context. Do not serialize raw Item metadata such as barcodes or condition into roadmap summaries.
   - *Alternative considered:* return only a generic nested entity object. Rejected for this iteration because preserving ID keys minimizes breakage for existing API consumers and the discriminator makes client rendering unambiguous.

4. **Validate Item ownership at the API boundary, not only by FK.** For create/target replacement, resolve Item by both `item_id` and the roadmap owner's user ID. Return 404 for absent, negative/virtual, or non-owned IDs so the API does not confirm another user's inventory. The Item FK enforces existence; ownership remains application-level because it is user-specific.
   - **Explicit product assumption:** an Item remains eligible when its owner has lent it to somebody else; `owner_id`, not current custody or `collection_status`, determines ownership. The chooser displays loan state if the item DTO already provides it, but never offers copies owned by another user or wishlist intent records.

5. **Extend existing item-list search with an owner-only mode for the picker.** Add an explicit owner-only filter to the authenticated `/api/items` list query and its React Query hook. In this mode filter strictly by `Item.owner_id == current_user`, retaining existing text search and pagination. The roadmap picker loads only these candidates and labels each level distinctly. Use the existing catalog search/read paths for Work, Expression, and Manifestation; selecting a candidate submits exactly one matching ID.
   - *Alternative considered:* add a roadmap-specific Item search endpoint. Rejected to avoid a duplicate inventory search API when `/api/items` already supports pagination, search, and Item summaries.

6. **Make roadmap-item entry mutations explicit and narrowly scoped.** Keep existing POST create, GET list, and position PATCH routes; extend their payload/DTOs for `item_id`. Add `PATCH /api/v1/roadmaps/items/<id>` for replacing only the FRBR target, requiring exactly one target key and preserving all other entry state, and `DELETE` on the same entry path for deliberate removal. DELETE compacts subsequent positions in that roadmap. All operations verify roadmap ownership; non-owned roadmap resources return 404.
   - *Alternative considered:* require deleting and recreating an entry to change target. Rejected because that loses notes, status, dates, completion state, and position.

7. **Migrate existing rows without reclassification.** Add a new linear Alembic revision after the then-current repository head. Existing valid Work/Expression/Manifestation rows remain unchanged and get `item_id = NULL`; no inferred Item links or backfills are performed. Replace the check constraint and target FKs/indexes in a dialect-aware way. Preflight invalid cardinality and fail without deleting or rewriting roadmap rows. A downgrade must refuse while any Item-targeted roadmap rows exist; when safe, it removes the new column/index/FK and restores the three-target constraint and prior FK behavior.

8. **Treat a blocked target deletion as a conflict, not an internal error.** The catalog and Item delete paths that can reach these FKs should identify the roadmap-target constraint violation and return HTTP 409 without exposing SQL or rolling back unrelated work. The user can remove the roadmap entry and retry. Existing unrelated integrity failures retain their current handling.

## Risks / Trade-offs

- [Restrictive deletion can surprise a user deleting a catalog record] → Return a clear 409 explaining that a roadmap entry references it and provide the roadmap-entry removal path; add API tests at each target level.
- [Changing existing `SET NULL` FK actions may vary across database dialects] → Inspect actual constraint names at the current migration head, test PostgreSQL upgrade/downgrade and SQLite model/migration behavior, and fail preflight before destructive changes.
- [Four selector modes increase picker complexity and risk wrong-level selection] → Require explicit level selection, show level badges/context, and test every mode including distinct Item copies of one Manifestation.
- [Owner-only candidates can be incomplete if the collection endpoint's search path leaks borrowed rows] → Apply the ownership predicate in SQL for owner-only mode, not only in the client, and independently verify ownership on writes.
- [Existing consumers may assume only three target keys] → Keep the existing keys and semantics unchanged, add `item_id` as nullable plus `target_type`, and retain three-key request compatibility.

## Migration Plan

1. Apply the Alembic migration before deploying application code that writes `item_id`; it adds a nullable FK/index and replaces the target check without backfilling existing rows.
2. Deploy model/API changes: four-way validation and serialization, owner-only candidate filtering, entry target PATCH/DELETE, and safe 409 handling for referenced-target deletions.
3. Deploy frontend target selection/display and verify existing three-level entries render unchanged; then run migration, API, frontend, and E2E suites.
4. Roll forward by correcting any failed preflight data explicitly; never auto-delete or guess target mappings. Downgrade only after item-target entries have been removed or retargeted. The migration must abort downgrade if any row still uses `item_id`, protecting target identity from loss.

## Open Questions

None. The ownership rule for lent-out copies and the restrictive deletion policy are explicit proposal assumptions for this change.
