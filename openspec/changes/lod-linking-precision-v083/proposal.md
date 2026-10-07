## Why

Dev-note bug (#important): "LOD automated linking produces too many false positives". Release planning: v0.8.x, C62 (target v0.8.3).

Premises verified against `app/core/lod_linking_service.py` (664 lines):

- **Confirmed: string-only matching, first-hit wins.** `DBpediaClient._query_lookup` takes `docs[0]` with no label comparison and no candidate ranking (L259). `resolve_person` passes only the name and `type_name="Person"` (L216-233). `_query_sparql` is an exact lowercase label match with `LIMIT 1` (L291-332).
- **Confirmed: author and year are never used.** `resolve_work(... author=...)` accepts `author` but never reads it (L176-213; caller passes it at L499). Publication year is not passed at all, although the existing `lod-linking` spec already promises disambiguation by "media category and publication year".
- **Confirmed: confidence is not a real signal.** DBpedia Lookup `score` is divided by 100 and clamped to [0.60, 0.95] (L272). Lookup scores are typically far above 100, so almost every hit becomes 0.95. SPARQL is a fixed 0.80, GeoNames a fixed 0.90 (L388), the local WordNet dictionary a fixed 0.95. Nothing compares the score to a threshold, so no candidate is ever rejected. The `lod-reconciliation` spec already mentions a "confidence threshold" (Recording zero-match scenario), but no such threshold exists in code.
- **Confirmed: type constraints are weak.** The `dbo:` class comes only from `MEDIA_CATEGORY_DBO_MAP` (L42-55). Unknown categories (e.g. `comic`, `magazine`, `document`) send no constraint, so a title like "Dune" or "It" can match a place, a band or a disambiguation page. The result URI and class are not checked against the FRBR tier. GeoNames uses `maxRows=1` with no `featureClass=P` (populated place) filter (L361-366), so "Reading" or "Orange" can resolve to a non-city feature.
- **Confirmed: WordNet tags are over-linked.** Tags are matched case-insensitively by exact string against a 17-entry dictionary, with no sense disambiguation: "mystery", "romance", "art" and "history" are polysemous. Everything else becomes a synthesized DBpedia Category URI at 0.70. That is C52 MOD-LOD-1.
- **Premise correction: links are NOT auto-verified.** Every `SemanticLink` is created with `verified=False` (L521, L555, L592, L630). The real defect is the opposite: nothing reads `verified` or `confidence`. `SemanticLink.verified` is a plain `Boolean` (`app/db/core.py:155`). Every consumer treats any row as an applied link: the `lod_status` and `lod_authority` filters (`app/api/filters.py:369-395`, `app/core/data_manager.py:1052-1078`), the dashboard linked counts (`app/api/admin.py:1245-1266`), the unlinked-only batch scope (`app/core/tasks.py:339-397`), and the manifestation links API and UI. So unverified low-quality candidates are presented and counted as links. The fix is to gate application on confidence and add a state, not to stop auto-verifying.
- **Confirmed: no cleanup path.** The only remedy is per-link DELETE (`app/api/manifestations.py:1088`). `EntityAuditLog` exists (`app/api/admin.py:45`) but is not used for links.

## What Changes

- **Scoring (backend).** Replace the opaque confidence with a composite score computed from candidate evidence: label similarity, class compatibility, author or contributor corroboration, year proximity, and the lookup rank margin between the first and second candidates. Evaluate the top N candidates, not just `docs[0]`.
- **Class constraints aligned with FRBR tier and content_type.** Work-level title links must be creative-work classes compatible with the expression `content_type` and the manifestation media category. Contributor links must be Person or Organisation. Manifestation-level place links must be populated places. Candidates in the wrong class, and disambiguation or list pages, are rejected. Unknown categories fall back to a generic creative-work class set, never to an unconstrained search.
- **Threshold and tiers.** Introduce an auto-apply threshold and a lower suggestion threshold. At or above auto-apply, the link is created as `accepted`. Between the two, it is created as `suggested` and excluded from filters, counts, public output and RDF. Below the suggestion threshold, no link is created and the skip is recorded in the audit stream. The thresholds are instance settings with safe defaults.
- **Link status.** Add `status` (`suggested` | `accepted` | `rejected`) beside the existing `verified` boolean. `verified` keeps its meaning of "curator confirmed". A tri-state `verified` was evaluated and rejected, because it would change the meaning of a column used in the API contract and require a nullable-boolean convention across SQLite and PostgreSQL. A curator can accept or reject a suggestion. A rejection is remembered, so a re-link never re-creates the same bad match.
- **Precision regression fixture set.** A committed fixture of known false positives and known true positives, replayed offline against recorded provider responses. The test asserts per-authority precision at or above a target and fails CI on regression.
- **Cleanup of existing bad links.** An admin or custodian dry-run report followed by an apply step. It re-scores existing links with the new scorer, then demotes below-threshold links to `suggested` (never hard-deletes in the default mode). Every change is written to `EntityAuditLog`. Results are visible on the `/admin/lod` dashboard (C39) as suggested, demoted and rejected counts and a review list.
- **Dependency, not duplicated:** C52 `v083-release-review-findings` already owns MOD-LOD-1 (WordNet mapper storing DBpedia URIs under `authority=wordnet`) and MOD-LOD-2 (SemanticLink dedupe on merge). This change builds on both. It adds no WordNet-fallback fix and no merge dedupe. It only adds sense-disambiguation scoring for the local WordNet dictionary, applied to whatever C52 leaves in place. Apply C62 after C52.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `semantic/lod-linking`: DBpedia, WordNet and GeoNames matching requirements gain scoring, class constraints, thresholds and suggested status. The Semantic Links API requirement gains status and accept/reject.
- `semantic/lod-reconciliation`: the zero-match, threshold and audit requirements become real. The dashboard gains suggested and demoted counts and the cleanup flow. Filters and statistics count `accepted` links only.

## Impact

- **Backend:** `app/core/lod_linking_service.py` (scorer, candidate selection, thresholds), `app/db/core.py` (`SemanticLink.status`), a new Alembic migration, `app/core/tasks.py` (audit stream and unlinked scope), `app/api/manifestations.py` (accept/reject), `app/api/admin.py` (cleanup dry-run/apply, stats), `app/api/filters.py` and `app/core/data_manager.py` (accepted-only), and the RDF/SPARQL exporters that read links (accepted only).
- **Migration:** one revision, id of 32 characters or fewer, on top of the single current head. Existing rows are backfilled in batches, with `status=accepted` for `verified=True` rows. Unverified rows are set to `accepted` for compatibility. The cleanup job then re-scores them, so the migration itself performs no network calls.
- **Frontend:** the manifestation LOD panel (a suggested section with Accept/Reject) and `/admin/lod` (cleanup card, counts, review list). Shadcn and Tailwind only, with every control wired.
- **Tests:** existing assertions of `confidence == 0.95/0.90/0.70` in `tests/test_lod_linking.py` (L150, L228, L255, L609) change with the new scorer.
- **Risk:** more links become `suggested` and fewer `accepted`, so recall drops by design. The defaults are tunable per instance.
