## ADDED Requirements

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
