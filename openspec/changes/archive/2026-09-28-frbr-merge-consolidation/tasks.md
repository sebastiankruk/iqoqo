# Tasks — FRBR Merge Consolidation

## 0. Preconditions

- [x] 0.1 Confirm the P0 on real PostgreSQL, not just SQLite with `PRAGMA foreign_keys=ON`. **Done** against the dedicated E2E instance (PostgreSQL 18, `127.0.0.1:55432`, project `iqoqo-e2e-test`, throwaway `iqoqo_merge_probe` database): 8 of 9 referencing rows destroyed by `merge_frbr_entities`, all 9 preserved by `merge_work`. See the tables in `proposal.md`.
- [x] 0.2 Investigate the `WorkContribution` count reading `0` on the manual path, which the aggregate probe could not explain. **Done** — it is a *second* defect: a delete-orphan cascade on `Work.contributions` (`lazy="selectin"`) deletes the source's **unique** contributor instead of migrating it, because `merge_frbr_entities` ends in `db.session.delete(source)`. The survivor ends up with 2 contributions where 3 are correct. `merge_work` is correct only because its Core-level `_delete_source_row()` bypasses the ORM cascade; that must become an explicit property of the shared core, not an accident.
- [x] 0.3 Archive `duplicate-detection-service` so its `operations/duplicate-detection` capability lands in the main specs, and rebase this branch onto the result.
- [x] 0.4 Get explicit approval for the shared-core refactor (implementation rule 9: large refactors need an approved plan first).

## 0a. Already fixed ahead of this change

- [x] 0a.1 **Fixed separately** (commit `fix(dedup): keep create_all valid on PostgreSQL`): the C15 ORM model built `uq_duplicate_candidates_pair` with `db.case(...)`, which SQLAlchemy renders unparenthesized. PostgreSQL parses that as a column separator inside `CREATE INDEX`, so `db.create_all()` — and therefore `scripts/init_db.py` — failed with `syntax error at or near "CASE"` on a fresh PostgreSQL install. The Alembic migration already emitted the parenthesized form, and SQLite accepts the broken form, so no existing test caught it. Now uses parenthesized `db.text(...)` matching the migration, verified by running `init_db.py --reset` against PostgreSQL, and guarded by `test_duplicate_candidates_model_index_compiles_for_postgresql`.

## 1. Reference map and coverage gate (P0 — the release gate)

- [x] 1.1 Add the `_RefPoint` dataclass and the `_WORK_REFPOINTS` / `_EXPRESSION_REFPOINTS` / `_MANIFESTATION_REFPOINTS` maps in a new shared merge module (`app/core/frbr_merge.py`), moving `_repoint_simple`, `_repoint_unique_child`, `_repoint_semantic_links`, and `_delete_source_row` into it unchanged, including their docstrings.
- [x] 1.2 Make the Core-level delete the **only** way the shared core removes a source row, and document why: an ORM `session.delete()` cascades `delete-orphan` over a `lazy="selectin"` collection whose child FK was re-pointed at the column level, silently deleting the row that was supposed to migrate. Add a regression test for the source-only contribution shape per 0.2.
- [x] 1.3 Populate all three maps exhaustively: Work 13 columns, Expression 7, Manifestation 9, plus one polymorphic `SemanticLink` entry per tier. Add a module docstring stating the counts and the rule that a column is only omitted via the coverage allowlist.
- [x] 1.4 Add `tests/test_frbr_merge_coverage.py`: reflect every foreign key targeting `works.id`, `expressions.id`, and `manifestations.id` from SQLAlchemy metadata and assert each `(model, column)` is in the matching tier map. Any intentional exclusion must appear in an allowlist with a per-entry justification comment.
- [x] 1.5 In that same test file, add behavioral cases per tier that build one referencing row of every kind, merge, and assert every row survived and now points at the survivor. Cover the `UserWorkIntent` and `WorkPart` cases explicitly, since those are the proven losses. Run these against PostgreSQL in CI, not only SQLite — SQLite's permissive default masked the original defect.
- [x] 1.6 Add a CI job or Makefile target that runs the merge-integrity suite against the dedicated E2E PostgreSQL instance, so `create_all`-level and cascade-level defects are caught by the pipeline rather than by hand.

## 2. Route the manual merge through the shared core (P0)

- [x] 2.1 Refactor `frbr_service.merge_frbr_entities` to resolve its tier to the shared map and delegate the re-pointing to it, keeping the signature `merge_frbr_entities(entity_type, source_id, target_id, user_id)` and its return value.
- [x] 2.2 Add the `try/except Exception: db.session.rollback(); raise` wrapper it currently lacks, so a mid-merge failure cannot leave a partially flushed session.
- [x] 2.3 Acquire `SELECT … FOR UPDATE` on both entities in ascending id order before any write, matching `merge_work`/`merge_manifestation`.
- [x] 2.4 Replace the generic `change_type="merge"` with `merge_work` / `merge_expression` / `merge_manifestation` so audit queries span both entry points, and record the per-table re-point counters (including `reparented_items` and `reparented_contributions`) in the diff.
- [x] 2.5 Reconcile ISBNs in the manual Manifestation merge by reusing the dedupe path's rules: primary wins, a source ISBN the primary lacks is adopted, a conflict is preserved in `meta["alternate_isbn13"]`, and the same for `meta["alternate_barcodes"]`. Keep them strictly on the F3 tier.
- [x] 2.6 Extract the shared identifier-reconciliation helper rather than duplicating the logic, and have `duplicate_service.merge_manifestation` call it, so the two paths cannot drift.
- [x] 2.7 Add `@limiter.limit(...)` to `POST /v1/admin/frbr/relations/merge` matching the scan endpoint's posture, and confirm `/reassign` and `/split` are considered for the same treatment.
- [x] 2.8 Add the first-ever tests for `merge_frbr_entities` across all three tiers: child re-parenting, contribution migration *and* de-duplication as distinct cases, metadata merge, self-merge rejection, cross-tier rejection, missing-entity rejection, rollback on failure, and reference preservation per 1.5.
- [x] 2.9 Verified manually in the browser on 2026-09-28: Relation Management -> Merge renders and submits correctly with no console errors. Verify the existing `RelationManagementDialog` is unaffected: response shape, toast copy, and the post-merge tree refresh all still work (component test plus a manual pass).

## 3. Expression tier (P1) — DEFERRED to C41 `duplicate-expression-tier` (v0.8.3)

> **Do not implement this group here.** It was moved out of the 0.8.2 release gate
> on 2026-09-28 and is now tracked as **C41: duplicate-expression-tier** in the
> v0.8.3 section of the release plan, so the two changes cannot implement the same
> requirements twice.
>
> **No capability is lost by deferring it.** `merge_frbr_entities` already merges
> Expressions correctly today through the shared `_EXPRESSION_REFPOINTS` map, via
> the Relation Management dialog; group 3 only exposes F2 in the *review queue*,
> which is a discoverability improvement. It also keeps a third migration off a
> chain that already failed once this release.
>
> The `Expression-Tier Merge Safety` requirement these tasks implement remains
> declared in this change's `frbr/merge-integrity` capability and is **not**
> duplicated by C41.
>
> Original task text, kept for reference:


- 3.1 Implement `merge_expression` in the dedupe path using `_EXPRESSION_REFPOINTS`: re-parent child Manifestations, reconcile `ExpressionContribution`, and re-point `UserWorkIntent.expression_id`, `RoadmapItem`, `EscalationRequest`, `SocialFeedback`, `SocialNote`, and `SemanticLink`.
- 3.2 Refuse a merge when `language` or `content_type` differ, with a `DuplicateServiceError` explaining that distinct realizations must not be merged. Confirm the refusal happens before any write.
- 3.3 Add Alembic migration `v0_8_2_merge_expression_tier` (linear, single head, `down_revision = "v0_8_2_duplicate_candidates"`): relax `ck_duplicate_candidates_entity_tier` to include `'expression'`, add `resolution_source` and nullable `confidence`, backfill from `llm_reasoning`. Implement the lossy-but-documented `downgrade()` described in `design.md`.
- 3.4 Update `DUPLICATE_ENTITY_TIERS` in `app/db/core.py` and every validation site (`candidate_query`, `list_candidates`, `record_candidate`, the CLI `--tier` choices, the scan endpoint's `tier` field) to accept `expression`.
- 3.5 Add expression blocking keys built from the Expression's own identity — normalized label plus the `(language, content_type)` pair — and **no** parent-Work title fallback. Reject a differing `(language, content_type)` pair before scoring.
- 3.6 Update `tests/test_migration.py::test_alembic_single_head_and_unbroken_lineage` for the new head and revision walk, and add migration tests for the new revision's upgrade and downgrade.
- 3.7 Add service and API tests: expression merge re-parents Manifestations, cross-language refusal, two Expressions of one Work not blocking on each other, and an end-to-end expression candidate lifecycle through the review queue.

## 4. Deterministic classification and optional inference (P2)

- [x] 4.1 Introduce a three-way classification (`AUTO_ACCEPT` / `AUTO_REJECT` / `NEEDS_LLM`) evaluated before inference, keyed off the conclusive-identifier early return in `_score_pair` and the creator-overlap rule at `duplicate_service.py:752`.
- [x] 4.2 Make `confidence` nullable in the model and store `resolution_source`; set `llm_reasoning` to the heuristic reasons when there is no LLM explanation so the review UI always has something to show.
- [x] 4.3 Add `--engine heuristic|llama` to `scripts/detect_duplicates.py`, defaulting to `heuristic`, and keep the existing exit codes (0 ok, 1 failure, 2 missing prerequisite or bad argument). An unreachable inference service must be a hard prerequisite only in `llama` mode.
- [x] 4.4 Add an `engine` field to `POST /v1/admin/duplicates/scan` (default `heuristic`), and stop requiring the Ollama health pre-check unless the requested engine is `llama`.
- [x] 4.5 Add `--engine` coverage to `tests/test_scripts.py` and engine-specific API tests.
- [x] 4.6 Document in `scripts/detect_duplicates.py` and the CHANGELOG that a scan no longer requires Ollama by default, and that `llama` remains available.

## 5. Frontend (P2, follows the backend)

> 5.1, 5.2 and the Expression half of 5.5 moved to **C41** with the rest of the F2
> work, since a `DuplicateSide` member without a tier to produce it would be dead
> code. C41 tasks 5.1, 5.2 and 5.4 cover them.

- [x] 5.3 Label the confidence badge by provenance: `LLM 0.92` versus `heuristic 1.00 (identical ISBN)`, and fall back to the heuristic reasons when no LLM rationale exists. A heuristic score must not be presented as a calibrated probability.
- [x] 5.4 Update the empty-state copy, which currently implies a scan needs inference, and expose the engine choice only if it can be done without adding a control to the card.
- [x] 5.5 Add component tests for the provenance-labelled badge and the unchanged button count for a read-only and an editable viewer.

## 6. Verification and release

- [x] 6.1 `make lint` green (ruff, black, isort, markdownlint, license headers, gitleaks).
- [x] 6.2 `make test` green, with the only tolerated failure being the pre-existing environment-dependent `test_redis_missing_configures_memory_defaults`.
- [x] 6.3 Re-run the PostgreSQL proof from 0.2 and confirm the manual merge now preserves the wishlist row, `WorkPart`, `WorkExpansionLink`, `ContainerAggregation`, `SocialFeedback`, and `EscalationRequest`.
- [x] 6.4 Update `docs/CHANGELOG.md` under `[0.8.2]`, explicitly calling out the silent data loss in the manual merge as a fix and the `change_type` audit vocabulary change.
- [x] 6.5 Ticked in `.context/notes/plan/0.8.x-release-plan.md` and add it to the v0.8.2 exit checklist.
