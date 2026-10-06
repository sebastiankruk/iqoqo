## 1. LOD Linking & WordNet Authority Harmonization

- [ ] 1.1 In `app/core/lod_linking_service.py`, update `WordNetMapper.resolve_tag()` to record DBpedia category fallbacks with `authority="dbpedia"` instead of `authority="wordnet"`, and verify via tests that no DBpedia category URI is saved under `wordnet`.
- [ ] 1.2 Add validation or live lookup before persisting DBpedia categories to prevent hallucinating non-existent category URIs. Verify with `tests/test_lod_linking.py`.
- [ ] 1.3 In `app/core/frbr_merge.py:repoint_semantic_links`, deduplicate identical `SemanticLink` rows before updating `entity_id`. Verify with a targeted unit test in `tests/test_frbr_merge_integrity.py`.

## 2. Duplicate Detection Merge Consolidation

- [ ] 2.1 Refactor `merge_work` in `app/core/duplicate_service.py` to delegate to `frbr_merge.repoint_references()` and `frbr_merge.delete_source_row()`. Verify with `tests/test_duplicate_detection.py`.
- [ ] 2.2 Refactor `merge_manifestation` in `app/core/duplicate_service.py` to delegate to `frbr_merge.repoint_references()`, `frbr_merge.consolidate_manifestation_identifiers()`, and `frbr_merge.delete_source_row()`. Verify with `tests/test_duplicate_detection.py`.
- [ ] 2.3 Remove unused redundant helper functions `_repoint_simple`, `_repoint_unique_child`, and `_repoint_semantic_links` from `duplicate_service.py`.

## 3. Catalog API Enhancements & Rate Limiting

- [ ] 3.1 Update `/api/items` sorting in `app/api/items.py` when `sort_by == "author"` to order by `Work.meta['authors']` or `WorkContribution` rather than falling back to `Work.title.asc()`. Verify with a unit test.
- [ ] 3.2 Add `@limiter.limit("10 per minute")` to `POST /api/account/email/verify` and `POST /api/account/deletion/confirm` in `app/api/account.py`. Verify with `tests/test_account_deletion.py`.
