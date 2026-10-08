## Context

See `proposal.md` for background.
The v0.8.2 release introduced external LOD entity linking (`app/core/lod_linking_service.py`), FRBR duplicate detection and merge consolidation (`app/core/duplicate_service.py`, `app/core/frbr_merge.py`), keyset pagination, and email-confirmed account deletion. This technical design specifies the remediations for the findings documented during the final release review.

## Goals / Non-Goals

**Goals:**
- Ensure ontological purity in `catalog.semantic_links`: WordNet mappings must only link to real WordNet synset URIs with `authority="wordnet"`.
- Eliminate code duplication between `duplicate_service.py` and `frbr_merge.py` by sharing `repoint_references()` and `consolidate_manifestation_identifiers()`.
- Prevent duplicate `SemanticLink` creation during FRBR entity merges.
- Ensure item sorting by author properly maps to work contributors or author metadata.
- Protect account token confirmation endpoints with rate limiting.

**Non-Goals:**
- Introducing new external LOD authorities or altering the database schema of `semantic_links`.
- Changing the public API contract for account deletion confirmation or FRBR relations.

## Decisions

### 1. WordNet Mapping Disambiguation & Fallback Separation
- **Decision:** In `WordNetMapper.resolve_tag()`, if a tag does not match the local WordNet dictionary, do NOT synthesize a DBpedia category URI and assign it `authority="wordnet"`. Instead, either look up DBpedia categories via the DBpedia Lookup client and record them under `authority="dbpedia"` with `strategy="dbpedia_category"`, or return `None` when unresolved.
- **Rationale:** Preserves ontological integrity. WordNet and DBpedia are separate authorities with different vocabularies and URI namespaces.
- **Alternatives considered:**
  - *Keep string-concatenated DBpedia category under `wordnet`*: Rejected as it pollutes the knowledge graph with fake WordNet links.

### 2. Duplicate Detection Merge Delegation to `frbr_merge.py`
- **Decision:** Replace the manual SQL query execution in `duplicate_service.merge_work` and `duplicate_service.merge_manifestation` with direct calls to `frbr_merge.repoint_references()`, `frbr_merge.consolidate_manifestation_identifiers()`, and `frbr_merge.delete_source_row()`.
- **Rationale:** `frbr_merge.py` is the single source of truth guarded by `test_frbr_merge_coverage.py`. Maintaining duplicate queries in `duplicate_service.py` risks silent data loss when new tables are added.

### 3. SemanticLink Deduplication During Repoint
- **Decision:** Update `repoint_semantic_links` in `app/core/frbr_merge.py` to check for pre-existing links on `target_id` with matching `(authority, external_uri)`. Redundant links from `source_id` are deleted rather than updated.
- **Rationale:** Prevents duplicate rows from accumulating on the survivor when merging two entities that were already linked to the same external authority.

### 4. Author Sorting Fallback
- **Decision:** In `app/api/items.py`, when `sort_by == "author"`, query and sort by `WorkContribution` or `func.lower(Work.meta['authors'][0].as_string())` rather than `Work.title.asc()`.
- **Rationale:** Prevents user confusion when viewing collections sorted by author.

### 5. Rate Limiting on Token Confirmation POSTs
- **Decision:** Add `@limiter.limit("10 per minute")` to `/api/account/email/verify` and `/api/account/deletion/confirm`.
- **Rationale:** Standard defense-in-depth practice to prevent denial-of-service and automated probing.

## Risks / Trade-offs

- **[Risk]** Existing rows in `catalog.semantic_links` may already have `authority="wordnet"` pointing to `dbpedia.org/resource/Category:...`.
  - *Mitigation:* A one-time data cleanup query can update `authority = 'dbpedia'` where `external_uri LIKE '%dbpedia.org%'`.
