# Proposal: Address Findings from v0.8.2 Release Review

## Why

Comprehensive pre-release review of `release/0.8.2` revealed several architectural, ontology, and maintainability findings that do not block the 0.8.2 release but should be consolidated and resolved in v0.8.3. These include ontological category mapping errors in LOD linking, duplicate code in the FRBR duplicate detection merge path, redundant semantic links during entity merges, and minor API sorting/rate-limiting enhancements.

## What Changes

- **MOD-LOD-1 (Ontology & Data Integrity):** Fix `WordNetMapper._resolve_dbpedia_category` in `app/core/lod_linking_service.py` so it does not store DBpedia category URIs under `authority="wordnet"`. Stop synthesizing unverified DBpedia categories without validation.
- **MOD-FRBR-1 (Architecture / DRY):** Unify `merge_work` and `merge_manifestation` in `app/core/duplicate_service.py` to delegate to `frbr_merge.py` (`repoint_references`, `lock_pair`, `delete_source_row`), removing 150+ lines of duplicate SQL queries.
- **MOD-LOD-2 (Architecture & Data Cleanliness):** Deduplicate identical `SemanticLink` rows on merge in `app/core/frbr_merge.py:repoint_semantic_links`.
- **LOW-API-1 (API / UX):** Fix `sort=author` in `app/api/items.py` to properly sort by work contributor or author rather than falling back to `Work.title.asc()`.
- **LOW-SEC-1 (Security):** Add rate limiting (`@limiter.limit("10 per minute")`) to `POST /api/account/email/verify` and `POST /api/account/deletion/confirm` in `app/api/account.py`.

## Capabilities

### New Capabilities
None

### Modified Capabilities
None (`skip_specs: true` has been set).

## Impact

- Prevents semantic drift and corrupted LOD authorities in `catalog.semantic_links`.
- Eliminates duplicate merge code across `duplicate_service.py` and `frbr_merge.py`, safeguarding future schema changes.
- Enhances item sorting accuracy for collectors and protects token confirmation endpoints against brute-force / spamming attempts.
