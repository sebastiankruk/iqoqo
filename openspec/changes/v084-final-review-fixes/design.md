## Context

During the pre-tagging audit of release `0.8.4`, Gemini Argon and Principal Code Review identified 2 critical blockers and 8 moderate reliability/security issues across provider merging, multi-series synchronization, rich text SSR sanitization, metadata display projection, catalog search ranking, and item ownership account discovery. See `proposal.md` for motivation and background.

## Goals / Non-Goals

**Goals:**
- Eliminate catalog data corruption in `ProviderMergeDialog` by extracting genuine provider candidates from `raw_payload` and recorded provenance, synchronizing selection state reactively, and updating the top-level `manifestation.cover_url` column alongside `meta["cover_url"]`.
- Enforce canonical hierarchy lock order (`Work -> Expression -> Manifestation`) using `with_for_update()` before reading/mutating entities during provider merges to eliminate transaction deadlocks.
- Restore multi-series persistence and round-trip fidelity by serializing `series_memberships` in `get_frbr_tree` and `_get_physical_item_detail`.
- Fix SQLAlchemy 2.0 query crash in `frbr_service.update_work` during series membership deletion using set-based reconciliation and SQLAlchemy 2.0 `select()` syntax.
- Eliminate N+1 queries by adding `lazy="selectin"` to `WorkSeriesMembership.series`.
- Modernize `WorkEditor` series search using `apiClient`, cancel in-flight queries with `AbortController`, display actual series titles, and eliminate synchronous `setState` in effects.
- Include server `display` projection in `GET /api/manifestations/<id>` to eliminate metadata field leakage on manifestation detail views.
- Make metadata suppression case-insensitive, precompute lowercased keys in `app/core/meta_display.py`, filter internal `_`-prefixed keys, and restore interactive `<DiscoveryPivot>` clicks on category/mechanics tags.
- Secure SSR rich text sanitization by stripping `<script>` and `<style>` blocks and preventing unclosed/malformed HTML tag execution.
- Bound `GET /api/v1/admin/ownership/accounts` with SQL `LIMIT`/`OFFSET` pagination, and add `custodian` role check in the frontend ownership UI.
- Add deterministic tie-breakers (`id DESC`) to catalog FTS search ordering, enforce socket timeout bounds in ISBN lookup, break circular module imports in `item-sidebar.tsx`, and complete missing `docs/CHANGELOG.md` entries.

**Non-Goals:**
- Schema changes or new database migrations (the relational tables and columns already exist).
- Redesigning the FRBR data model or altering the core four-tier hierarchy.
- Adding third-party external provider network requests during client-side merge dialog rendering.

## Decisions

### 1. Genuine Provider Candidate Extraction in ProviderMergeDialog
- **Problem**: `buildFieldComparisonsFromTree` in `provider-merge-dialog.tsx` synthesized fake strings (e.g., `"${workTitle} (OpenLibrary)"`, `"en"`, `"${publisher} Press"`) and hardcoded provider labels.
- **Decision**: Extract real candidate values by inspecting `tree.manifestation.raw_payload` (which stores raw provider response payloads from Google Books and Open Library) and entity `_provenance` records. If a provider's candidate value is not present in the payload or provenance, only present genuine available candidates without fabricating synthetic entries.
- **Alternatives considered**: Querying external APIs in the browser when opening the dialog — rejected because it adds network latency, API rate-limit exhaustion, and requires API keys in the client.

### 2. Reactive Selection State in ProviderMergeDialog
- **Problem**: `selectedProviders` was initialized via `useState(() => ...)` only once, leaving selections un-synchronized if `tree` loaded or updated after mount.
- **Decision**: Track `comparisons` and use an effect or state reset whenever `comparisons` change so selections cleanly bind to the active manifestation's candidates.

### 3. Canonical Lock Ordering in apply_custodian_provider_merge
- **Problem**: Entities were locked by sorting IDs across distinct tables (`entities_to_lock.sort(key=lambda item: item[1])`), creating cross-table lock inversions and deadlock risks against standard hierarchy mutations.
- **Decision**: Lock entities strictly in canonical hierarchy order: `Work` first, then `Expression`, then `Manifestation`. Read rows directly with `with_for_update()` to ensure identity map freshness.

### 4. Set-Based Series Reconciliation in update_work
- **Problem**: Passing `~WorkSeriesMembership.series_work_id.in_(desired_series_ids) if desired_series_ids else True` passed a literal Python `bool` `True` into `.filter()`, crashing under SQLAlchemy 2.0. Additionally, looping executed individual queries per item.
- **Decision**: Use set-based reconciliation:
  1. Fetch existing `WorkSeriesMembership` records for `work.id` in a single query: `select(WorkSeriesMembership).where(WorkSeriesMembership.work_id == work.id)`.
  2. Map by `series_work_id`.
  3. Desired entries are validated (verifying `int(s_id) != work.id` to prevent self-membership, using explicit `sm_dict.get("series_work_id")` without conflating membership ID).
  4. Delete memberships present in database but absent from desired set using `db.session.delete(existing)`.
  5. Add new or update sequence for existing entries.
  6. Synchronize legacy `WorkPart` in lockstep.
- **Alternatives considered**: Raw SQL `DELETE FROM work_series_memberships WHERE work_id = :id` followed by bulk inserts — rejected because `WorkPart` legacy synchronization and ORM session caching require entity awareness.

### 5. Multi-Series Serialization in FRBR Tree and Item APIs
- **Problem**: `get_frbr_tree` (`app/api/admin.py`) and `_get_physical_item_detail` (`app/api/items.py`) omitted `series_memberships` from the serialized `work` payload, causing UI forms to default to `[]` and overwrite existing series links.
- **Decision**: Serialize `series_memberships` on `work` uniformly:
  ```python
  "series_memberships": [
      {
          "id": sm.id,
          "series_work_id": sm.series_work_id,
          "title": sm.series.title if sm.series else "",
          "sequence": sm.sequence,
      }
      for sm in getattr(work, "series_memberships", [])
  ]
  ```

### 6. Manifestation Detail Display Projection
- **Problem**: `GET /api/manifestations/<id>` returned raw `meta` without `display`, forcing `/manifestation/[id]` pages to fall back to `fallbackEntries`, which leaked dedicated attributes like `catalog_number`, `disc_count`, and `min_players`.
- **Decision**: Call `build_display_projection(m.meta)` in `get_manifestation_detail` and return `"display"` in the response payload.
- **Case-insensitivity**: In `meta.ts` and `extended-metadata.tsx`, match keys case-insensitively against all dedicated section keys. In `meta_display.py`, precompute the lowercased keys set once at module level and filter `raw_key.startswith("_")`.

### 7. SSR Rich Text Sanitization Hardening
- **Problem**: In SSR passes without DOMPurify, `dirty.replace(/<[^>]*>/g, "")` leaked script bodies (e.g., `alert(1)`) into the output and allowed malformed tags into `dangerouslySetInnerHTML`.
- **Decision**: Strip `<script[\s\S]*?<\/script>` and `<style[\s\S]*?<\/style>` (including contents) case-insensitively, then remove HTML tags and HTML-entity-encode any residual `<` and `>` characters before returning.

### 8. SQL Pagination for Ownership Accounts
- **Problem**: `GET /api/v1/admin/ownership/accounts` performed an unpaginated query `select(User).all()`, risking unbounded memory usage and exposing all user emails to any contributor.
- **Decision**: Add query parameter support (`q`, `limit`, `offset`) with a default limit of 20 (max 50) and SQL-level `LIMIT`/`OFFSET`. Return only necessary fields (`id`, `username`, `display_name`, `is_active`) and email if authorized.

## Risks / Trade-offs

- **[Risk]** Legacy records without `raw_payload` in `ProviderMergeDialog`.
  - *Mitigation*: Fall back to displaying recorded `_provenance` or current catalog value without generating fake provider candidates.
- **[Risk]** Large user directories in ownership transfer dropdown.
  - *Mitigation*: The frontend Combobox/search input passes the search term `q` to the paginated backend endpoint.
- **[Risk]** TagCloud clickability regression.
  - *Mitigation*: Restore `<DiscoveryPivot>` in `extended-metadata.tsx` so users can click category and genre chips to navigate to filtered catalog views.
