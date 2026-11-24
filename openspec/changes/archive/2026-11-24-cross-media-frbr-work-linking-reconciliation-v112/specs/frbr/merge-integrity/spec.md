## ADDED Requirements

### Requirement: Cross-Media Work Link and Candidate Reference Preservation on Merge

When two same-medium duplicate `Work`s are merged via the shared FRBR merge core (`frbr_merge`), every `works.id` foreign key on `WorkRelation` (`source_work_id`, `target_work_id`) and `WorkLinkCandidate` (`source_work_id`, `target_work_id`) MUST be registered in `REFPOINTS_BY_TIER["work"]` and re-pointed onto the surviving `Work`, collapsing duplicate pairs and deleting any row that would become self-referential (`source_work_id == target_work_id`) after consolidation.

#### Scenario: Merging a duplicate Work preserves its cross-media derivative links without creating self-links

- **GIVEN** a duplicate novel `Work` `W_source` merged into surviving novel `Work` `W_target`, where `W_source` holds a confirmed `WorkRelation` to film `Work` `W_film` and a `WorkLinkCandidate` pointing to `W_target`
- **WHEN** `frbr_merge` executes the Work-tier merge
- **THEN** the `WorkRelation` linking `W_film` and `W_source` MUST be re-pointed to `W_target` (or collapsed cleanly if `W_target` already holds that identical `(source, target, relation_type)` edge), the intra-pair row that would become `(W_target, W_target)` MUST be deleted, and `tests/test_frbr_merge_coverage.py` MUST pass with zero uncovered `works.id` foreign keys.
