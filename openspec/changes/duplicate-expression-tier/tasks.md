# Tasks — Duplicate Expression Tier (F2)

Target release: **0.8.3**. Implements the Expression-tier requirements already
declared by `frbr-merge-consolidation`; see that change's `frbr/merge-integrity`
capability for the contract.

## 0. Preconditions

- [x] 0.1 Confirm `frbr-merge-consolidation` is archived so `frbr/merge-integrity` exists in the main specs; rebase this branch onto the result.
- [x] 0.2 Confirm `v0_8_2_duplicate_provenance` is the current Alembic head and that the target environment has already applied it, so the new revision is genuinely appended rather than folded in.

## 1. Screening (do this first — it is the only real hazard)

- [x] 1.1 Add `expression` to `_DETECTION_TIERS` handling so `_resolve_tiers` accepts it, and verify `run_detection(tier="expression")` screens without raising.
- [x] 1.2 Implement Expression blocking keys from `normalize_title(expression.label)` plus the `(language, content_type)` pair, with **no** parent-Work title or sort-title fallback. Verify with a test asserting two Expressions of one Work in different languages produce `candidate_pairs == 0`.
- [x] 1.3 Discard any pair whose `language` or `content_type` differ at the blocking stage, before scoring. Verify neither engine can queue such a pair, and that the report does not count it.
- [x] 1.4 Add `_describe_expression` and an `Expression` member to the entity-description layer, returning `tier`, `id`, `label`, `language`, `content_type`, `manifestation_count`, and `creators`. Verify it is a self-describing payload so the frontend union stays a true discriminated union.
- [x] 1.5 Verify a positive case: two Expressions of one Work sharing `language`, `content_type`, and normalized label are classified `AUTO_ACCEPT` and queued with no inference call under the default engine.

## 2. Persistence

- [x] 2.1 Widen `DUPLICATE_ENTITY_TIERS` in `app/db/core.py` and every validation site: `record_candidate`, `list_candidates`, `candidate_query`, and the `_describe_for_tier` dispatch.
- [x] 2.2 Add migration `v0_8_3_duplicate_expression_tier` (linear, `down_revision = "v0_8_3_roadmap_item_target"`) relaxing `ck_duplicate_candidates_entity_tier` to include `'expression'`. Do **not** modify `v0_8_2_duplicate_provenance`.
- [x] 2.3 Implement `downgrade()` so it restores the two-value constraint and **fails loudly** if any `expression`-tier candidate exists, rather than deleting review history. Verify the failure message names the blocking rows.
- [x] 2.4 Update `tests/test_migration.py::test_alembic_single_head_and_unbroken_lineage` for the new head and revision walk, and add migration tests covering upgrade, the constraint actually admitting `expression`, and the downgrade refusal. Guard the schema-qualification rule: pass `schema=` separately rather than embedding it in the table name, since SQLite cannot express the distinction and would pass broken code.

## 3. Merge through the review queue

- [x] 3.1 Implement `merge_expression` in `app/core/duplicate_service.py` by resolving the tier to `_EXPRESSION_REFPOINTS` and delegating to the shared `repoint_references()` / `delete_source_row()` / audit path. Re-parent child Manifestations and re-point `UserWorkIntent.expression_id` rather than nulling it.
- [x] 3.2 Refuse a merge when `language` or `content_type` differ, raising before any write. Verify with a service test and a 400-level API test.
- [x] 3.3 Record the `merge_expression` audit entry with the acting user, the removed source id, the survivor, and the per-table re-point counters. Verify it lands in the same `change_type` vocabulary as `merge_work` and `merge_manifestation`.
- [x] 3.4 Verify the shared core's coverage test still passes unchanged — the Expression map already existed, so no new re-point column may be needed or added.

## 4. API and CLI

- [x] 4.1 Accept `tier: "expression"` on `POST /duplicates/scan` and `entity_tier=expression` on `GET /duplicates`, and add a filter test for the listing total.
- [x] 4.2 Verify `POST /duplicates/<id>/merge` resolves an Expression candidate end to end, including a cross-language refusal returning 400.
- [x] 4.3 Add `expression` to `scripts/detect_duplicates.py --tier` choices and extend `tests/test_scripts.py` for it.
- [x] 4.4 Re-run `make test-merge-integrity-pg` so the new tier is exercised against real PostgreSQL, not only SQLite.

## 5. Review UI

- [x] 5.1 Add the Expression member to the `DuplicateSide` discriminated union in `frontend/lib/api/admin.ts`, keeping the union discriminated on `tier` so no casts are needed. Verify `tsc --noEmit` is clean.
- [x] 5.2 Render the Expression comparison in the existing candidate card: label, language, content type, child Manifestation count, creators, and covers. **Add no controls** — the card's action row must stay byte-identical to the Work and Manifestation tiers.
- [x] 5.3 Verify the provenance-labelled confidence badge from 0.8.2 reads correctly for an Expression candidate queued by the classifier (NULL confidence, no percentage shown).
- [x] 5.4 Add component tests for the Expression card, the unchanged control count for a read-only viewer, and the unchanged control count for an editable viewer.
- [x] 5.5 Add a page test asserting the Expression tier is reachable from the shared `AdminSidebar` and that the sidebar's link set is unchanged by this work.

## 6. Verification and release

- [x] 6.1 `make lint` green and `make test` green, tolerating only the pre-existing environment-dependent `test_redis_missing_configures_memory_defaults`.
- [x] 6.2 Re-verify the no-parent-title-fallback rule against a production clone: a scan must not queue sibling Expressions of one Work, and must report the discarded cross-realization pairs separately.
- [x] 6.3 Update `docs/CHANGELOG.md` under the 0.8.3 heading, noting the widened tier vocabulary and the migration.
- [x] 6.4 Tick this change in `.context/notes/plan/0.8.x-release-plan.md` and add its exit checks to the 0.8.3 section.
