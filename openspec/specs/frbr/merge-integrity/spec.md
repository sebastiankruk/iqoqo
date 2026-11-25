# frbr/merge-integrity Specification

## Purpose

Guarantees that merging FRBR entities never destroys a referencing row, that
both manual and review-queue merges execute the same audited logic across all
three abstract tiers, and that the detector can classify candidates
deterministically without requiring local inference.

## Requirements

### Requirement: Complete Reference Re-pointing on Merge

The system MUST re-point every table that references a merged FRBR entity onto
the surviving entity, for all three abstract tiers (Work, Expression,
Manifestation). Where a referencing column participates in a natural-key unique
constraint, the system MUST collapse a would-be duplicate row onto the survivor
rather than violating the constraint. The set of covered columns MUST be
enforced mechanically against the database schema so a newly added referencing
column cannot be left un-covered.

#### Scenario: Merging a Work preserves a user's wishlist entry

- **WHEN** a Work `W_source` that is the target of at least one `UserWorkIntent` row is merged into `W_target`

- **THEN** the `UserWorkIntent.work_id` is re-pointed to `W_target` and no wishlist row is deleted.

#### Scenario: Merging a Work preserves box-set membership

- **WHEN** a Work `W_source` that is the container or a part of a `WorkPart` row is merged into `W_target`

- **THEN** the `WorkPart` row is re-pointed to `W_target`; if the target already holds that same part, the source row is deleted and exactly one membership remains.

#### Scenario: Reference coverage drift is detected

- **WHEN** a foreign key targeting `works.id`, `expressions.id`, or `manifestations.id` is added without a corresponding entry in the tier's re-point map

- **THEN** the coverage test fails, naming the uncovered `(model, column)` pair.

### Requirement: Unified Merge Execution Path

The system MUST execute manual merges and review-queue merges through one
implementation with one transaction contract, one row-locking strategy, and one
audit vocabulary, while preserving the existing public signature and API
response shape of the manual merge entry point. A merge MUST re-check that the
two entities still exist under a row lock, and MUST roll the entire
consolidation back on any failure.

#### Scenario: Manual merge delegates to the shared core

- **WHEN** an administrator submits `POST /v1/admin/frbr/relations/merge`

- **THEN** the request is served by the shared merge core, the response retains its `{"success": true, "data": {"id": …}}` shape, and the audit entry uses the tier-specific `change_type`.

#### Scenario: A mid-merge failure rolls back completely

- **WHEN** any step of a manual merge raises an exception

- **THEN** the session is rolled back, leaving both entities and every re-pointed row exactly as they were.

#### Scenario: Concurrency is serialized

- **WHEN** two merges target the same pair of entities concurrently

- **THEN** the `FOR UPDATE` row locks acquired in ascending id order mean one merge observes the other's committed result and refuses rather than double-consolidating.

### Requirement: Cascade-Safe Source Removal

The system MUST remove the source entity with a row-level delete that does not
trigger ORM `delete-orphan` processing over an already-loaded parent collection.
Re-pointing a child by assigning its foreign-key column does not remove it from
the parent's loaded collection, so a cascading ORM delete of the parent would
delete the very row that was migrated. A contributor unique to the source entity
MUST therefore follow the survivor, not disappear.

#### Scenario: A source-only contributor migrates to the survivor

- **WHEN** a Work `W_source` has a contributor that `W_target` does not

- **THEN** that contribution is re-pointed to `W_target` and remains visible on the merged Work.

#### Scenario: A duplicate contribution collapses, a unique one migrates

- **WHEN** a merge encounters a contribution whose natural key already exists on the survivor

- **THEN** the duplicate is removed and exactly one row remains; a contribution with a distinct natural key is migrated rather than removed.

### Requirement: Expression-Tier Merge Safety

The system MUST support merging two Expressions and MUST refuse a merge when
their `language` or `content_type` differ, because those attributes define the
realization an Expression represents. Expression detection MUST NOT use the
parent Work's title as a blocking key, since all Expressions of one Work share
it; a pair whose `language` or `content_type` differs MUST be rejected before
scoring and never queued.

#### Scenario: Merging two realizations of the same Work

- **WHEN** two Expressions of the same Work share a `language` and `content_type` and have near-identical titles

- **THEN** the system queues the pair for review and, on merge, re-parents every child Manifestation onto the survivor.

#### Scenario: Refusing a cross-language Expression merge

- **WHEN** a merge is attempted between an Expression with `language='pl'` and one with `language='en'`

- **THEN** the system refuses the merge with a validation error explaining that distinct realizations must not be merged.

#### Scenario: Expressions of one Work do not collide during screening

- **WHEN** a scan runs over a Work that has several Expressions in different languages

- **THEN** no pair of those Expressions is queued merely because they share the parent Work's title.

#### Scenario: A user's Expression-targeted wishlist row follows the survivor

- **WHEN** a merged Expression is the target of a `UserWorkIntent.expression_id`

- **THEN** that column is re-pointed to the surviving Expression rather than nulled.

### Requirement: Deterministic Candidate Classification

The system MUST classify each screened pair before any inference is requested.
A pair sharing a conclusive identifier (`isbn13`, `ean`, `upc`, or `barcode`)
MUST be classified as an automatic accept; a pair that shares a creator while
failing the title-similarity floor MUST be classified as an automatic reject.
Only the remaining pairs are eligible for language-model evaluation. The system
MUST record each candidate's provenance and MUST NOT require a running inference
service to complete a scan.

#### Scenario: Conclusive identifier match avoids inference

- **WHEN** two Manifestations share an identical `isbn13`

- **THEN** the pair is queued as a candidate with provenance `heuristic` and no inference request is issued.

#### Scenario: Same-creator noise is rejected deterministically

- **WHEN** two Works share a creator but their titles score below the similarity floor

- **THEN** the pair is rejected without an inference request and is counted in the report's rejection tally.

#### Scenario: A scan completes without an inference service

- **WHEN** a scan runs with the default engine while the local inference service is unreachable

- **THEN** the scan completes and queues every deterministically classified candidate, reporting that inference was unavailable.

#### Scenario: Language-model evaluation is still available

- **WHEN** a scan is requested with the `llama` engine

- **THEN** grey-zone pairs are evaluated as before, and their rationale is stored and surfaced to the reviewer.

### Requirement: Merge Operations Are Rate Limited and Audited

Every merge entry point MUST be rate limited, MUST reject a self-merge and any
cross-tier merge, and MUST record an audit entry identifying the removed source
entity, the surviving entity, the acting user, and the per-table re-point
counters — including re-parented Items owned by other users.

#### Scenario: Destructive merge endpoint is rate limited

- **WHEN** a client exceeds the configured merge request rate

- **THEN** the request is rejected with a rate-limit response and no merge is attempted.

#### Scenario: Audit records cross-owner re-parenting

- **WHEN** a merge re-parents Items belonging to users other than the actor

- **THEN** the audit entry's diff includes the re-parented item count alongside the other per-table counters.

#### Scenario: Rejecting invalid merge shapes

- **WHEN** a merge request names the same entity as both source and target, or names entities at different FRBR levels

- **THEN** the system refuses the request with a validation error and performs no writes.

### Requirement: Cross-Media Work Link and Candidate Reference Preservation on Merge

When two same-medium duplicate `Work`s are merged via the shared FRBR merge core (`frbr_merge`), every `works.id` foreign key on `WorkRelation` (`source_work_id`, `target_work_id`) and `WorkLinkCandidate` (`source_work_id`, `target_work_id`) MUST be registered in `REFPOINTS_BY_TIER["work"]` and re-pointed onto the surviving `Work`, collapsing duplicate pairs and deleting any row that would become self-referential (`source_work_id == target_work_id`) after consolidation.

#### Scenario: Merging a duplicate Work preserves its cross-media derivative links without creating self-links

- **GIVEN** a duplicate novel `Work` `W_source` merged into surviving novel `Work` `W_target`, where `W_source` holds a confirmed `WorkRelation` to film `Work` `W_film` and a `WorkLinkCandidate` pointing to `W_target`
- **WHEN** `frbr_merge` executes the Work-tier merge
- **THEN** the `WorkRelation` linking `W_film` and `W_source` MUST be re-pointed to `W_target` (or collapsed cleanly if `W_target` already holds that identical `(source, target, relation_type)` edge), the intra-pair row that would become `(W_target, W_target)` MUST be deleted, and `tests/test_frbr_merge_coverage.py` MUST pass with zero uncovered `works.id` foreign keys.

### Requirement: Unordered Reversed-Pair and Third-Party Collision Safety for Work Relations and Candidates

Both the ORM FRBR merge engine (`app/core/frbr_merge.py`) and the raw-SQL ETL Work merge execution path (`scripts/etl/merge.py`) SHALL prevent `UniqueViolation` / `IntegrityError` crashes on `uq_work_link_candidates_pair` (unordered `(MIN(source_work_id, target_work_id), MAX(source_work_id, target_work_id))`) and `uq_work_relations_triple` (`(source_work_id, target_work_id, relation_type)`) whenever a merged `source` `Work` and surviving `target` `Work` both link to a shared third-party `Work` `C` in either edge direction:

1. **`app/core/frbr_merge.py` (`merge_works`):** Before repointing `WorkLinkCandidate` foreign keys, the merge engine MUST delete direct `(source_id, target_id)` / `(target_id, source_id)` self-pairs AND MUST delete any `WorkLinkCandidate` row attached to `source_id` whose peer `Work` `C` already has an existing `WorkLinkCandidate` row with `target_id` in either direction (`(target_id, C)` or `(C, target_id)`).
2. **`scripts/etl/merge.py` (`apply_work_merge_plan`):** Before executing raw SQL `UPDATE` statements repointing `source_work_id` and `target_work_id` from `:source` to `:target`, the ETL merge plan MUST delete direct `:source <-> :target` self-pairs AND MUST delete third-party `work_relations` rows on `:source` whose repointed `(source_work_id, target_work_id, relation_type)` triple already exists on `:target`, as well as third-party `work_link_candidates` rows on `:source` whose peer `Work` `C` already has an unordered candidate pair with `:target` (`(target, C)` or `(C, target)`).

#### Scenario: ORM merge_works succeeds when source and target hold reversed-direction candidates to a third Work

- **GIVEN** three `Work` records `S`, `T`, and `C`, with `WorkLinkCandidate(source_work_id=S, target_work_id=C)` and reversed-direction `WorkLinkCandidate(source_work_id=C, target_work_id=T)`
- **WHEN** `merge_works(S.id, T.id)` executes
- **THEN** the colliding candidate on `S` is pruned prior to repointing, `S` merges cleanly into `T` without raising `IntegrityError` on `uq_work_link_candidates_pair`, and `WorkLinkCandidate(source_work_id=C, target_work_id=T)` survives intact

#### Scenario: ETL apply_work_merge_plan succeeds when source and target share third-party WorkRelation and WorkLinkCandidate peers

- **GIVEN** three `Work` records `S`, `T`, and `C`, where both `(S, C, "is_adaptation_of")` and `(T, C, "is_adaptation_of")` exist in `catalog.work_relations` and both `(S, C)` and `(C, T)` exist in `catalog.work_link_candidates`
- **WHEN** `apply_work_merge_plan()` merges `S` into `T`
- **THEN** colliding third-party `work_relations` and `work_link_candidates` rows on `S` are deleted before raw `UPDATE` repointing, zero `UniqueViolation` errors occur, `S` is deleted, and `T`'s links to `C` remain intact
