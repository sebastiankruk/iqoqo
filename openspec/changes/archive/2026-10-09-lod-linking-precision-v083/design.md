## Context

Dev-note bug (#important): "LOD automated linking produces too many false positives". As analyzed in `proposal.md`, current LOD matching in `app/core/lod_linking_service.py` is largely first-hit wins with static pseudo-confidence scores (0.95/0.80/0.90) and no rejection threshold. All links are stored as unverified rows but treated as active links by consumers. C52 (`v083-release-review-findings`) addresses WordNet authority mapping (MOD-LOD-1) and merge deduplication (MOD-LOD-2). This change focuses on scoring precision, FRBR-aligned class restrictions, status lifecycle (`suggested` | `accepted` | `rejected`), and historical data cleanup.

## Goals / Non-Goals

**Goals:**
- Implement composite candidate ranking using label similarity, creator/year corroboration, and candidate rank margin.
- Enforce strict ontology class boundaries (creative work subtypes for Works, Person/Org for Contributors, populated places `P` for GeoNames).
- Introduce a 3-state lifecycle (`accepted`, `suggested`, `rejected`) in `SemanticLink.status` with an Alembic migration.
- Only surface `accepted` links in search filters, collection facets, and RDF graphs.
- Provide dry-run cleanup task and `/admin/lod` review queue for suggested/false-positive links.
- Create regression test fixtures with known false-positive examples.

**Non-Goals:**
- Replacing DBpedia/GeoNames/WordNet with alternative knowledge graphs (e.g. Wikidata is deferred to v0.9.0).
- Modifying C52's WordNetMapper authority separation logic.
- Automated deletion of existing links without admin/custodian dry-run review.

## Decisions

- **Decision 1: Explicit `status` column rather than nullable or tri-state boolean.**
  - *Rationale:* `SemanticLink.verified` is already a public boolean (`false` by default). Changing its semantics or type breaks API clients and creates SQLite vs PostgreSQL boolean divergences. Adding an explicit `status VARCHAR(20) DEFAULT 'accepted'` (indexed) cleanly separates curator verification (`verified=True`) from automated acceptance tier (`status in ('accepted', 'suggested', 'rejected')`).
  - *Alternatives considered:* Repurposing `verified` as a tri-state (rejected).
- **Decision 2: Dual Thresholds in Instance Settings.**
  - *Rationale:* Auto-apply threshold (`LOD_AUTO_APPLY_THRESHOLD`, default 0.82) automatically commits high-confidence links as `accepted`. A lower threshold (`LOD_SUGGESTION_THRESHOLD`, default 0.55) flags candidates as `suggested` for custodian review. Anything below 0.55 is discarded and audit-logged as skipped.
  - *Alternatives considered:* Single binary cutoff (leaves marginal but useful links discarded completely).
- **Decision 3: Non-destructive Cleanup with Audit Trail.**
  - *Rationale:* Re-scoring existing catalog links in production should demote sub-threshold links from `accepted` to `suggested` rather than deleting rows outright, logging each action to `EntityAuditLog`.

## Risks / Trade-offs

- **[Risk]** Drop in reported LOD linking coverage metric.
  - *Mitigation:* Clear messaging on `/admin/lod` that link precision is prioritized over raw count; suggestions remain accessible in the review queue.
- **[Risk]** Migration on large `semantic_links` table in production.
  - *Mitigation:* Single linear migration adding `status` with default `'accepted'` (no long-running table rewrite), keeping migration identifier `<= 32` characters.
