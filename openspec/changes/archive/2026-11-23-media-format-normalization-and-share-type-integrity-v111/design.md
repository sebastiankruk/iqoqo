## Context

See `proposal.md` for motivation. Across the current iqoqo codebase:

1. **FRBR Model & Format Storage (`app/db/core.py`, `shared/taxonomy.yaml`):**
   - `Expression.content_type` (`String(50)`) stores the high-level `iqoqo:MediaCategory` (`text`, `audiobook`, `music`, `movie`, `board_game`, `puzzle`, `lego`).
   - `Manifestation` carries physical format in three locations: `Manifestation.format` (`String(50)`), `Manifestation.format_type` (`String(50)`), and `Manifestation.meta['format']` (`JSON`), plus `Manifestation.raw_payload` (`JSON`) for verbatim provider provenance.
   - Generic category strings (`"music"`, `"audio"`, `"sound"`, `"movie"`, `"video"`) currently persist at write time because:
     - `app/utils/musicbrainz.py:_detect_media_format` maps only Blu-ray Audio labels and collapses all other audio carriers (`CD`, `Vinyl`, `Cassette`, `SACD`, etc.) to `"audio"`.
     - `app/utils/discogs.py:_normalize_release_data` checks case-sensitive `"Vinyl"`, `"CD"`, and Blu-ray Audio labels, falling back to `"audio"` for everything else (`Cassette`, `SACD`, `MiniDisc`, `LP`, lowercase strings).
     - `app/core/ingest.py` (`ingest_from_meta`, `ingest_audio_from_barcode`, `ingest_video_from_barcode`), `app/api/scanner.py` (`_normalize_preview_meta`), `app/api/items.py` (`add_item_manual`), `app/api/manifestations.py` (`persist_isbn_manifestation`, `update_manifestation`), `app/core/frbr_service.py` (`create_manifestation`, `update_manifestation`), and `app/core/data_manager.py` (`import_data`) bypass `FormatNormalizer` or leave `format`/`format_type`/`raw_payload` unsynchronized (`validate_format_type(..., strict=False)` in `app/core/f3_validation.py` accepts any string <= 50 chars).
   - Meanwhile, `shared/format_mappings.yaml:57` maps `audio: cd` unconditionally, omitting `"music"` and `"sound"`, while `expand_format_filter` (`app/core/format_normalizer.py`) ignores `FORMAT_ALIAS_TO_CATEGORY` and `NULL` rows, and `CatalogFilterBuilder._apply_format`, `SearchService._pg_item_fts`, and `DataManager._build_format_facet_query` inspect only `Manifestation.meta['format']`.
   - The current Alembic head is `v1_1_0_serial_issn_issues` (`migrations/versions/v1_1_0_serial_issn_issues.py`).

2. **Shared Collection Filtering & Serialization (`app/api/public_items.py`, `app/core/frbr_service.py`, `frontend/`):**
   - `ShareCollectionDialog` (`frontend/components/collection/share-collection-dialog.tsx`) captures `status`, `category` (as `tags`), and `query`, dropping active `format` filters.
   - `SharedCollectionCreateSchema` (`app/api/schemas.py`) validates `visibility_scope` without normalizing `tags`/`category` or `format`.
   - `app/api/public_items.py` duplicates filter logic across `fetch_shared_collection_with_cache_policy` (used by RDF, content-negotiated JSON-LD/Turtle, and RSS) and `get_shared_collection` (JSON): neither reads `"category"` or `"format"`, empty `tags: []` silently disables category filtering, scalar strings or aliases (`"audio"`, `"sound"`) are unhandled, and `Manifestation` carrier formats are never cross-checked via `FORMAT_TO_CATEGORY`.
   - `get_shared_collection`'s `UserWorkIntent` wishlist branch (`public_items.py:875-985`) applies zero category/format filtering and omits `content_type`/`format` from serialized wishlist items.
   - `renderSharedCollectionJsonLdView` (`frontend/lib/share-server.tsx`) hardcodes audio `@context` keys (`byArtist`, `musicReleaseFormat`, `recordLabel`) across all items, `resolveSchemaType` (`frontend/lib/schema-org.ts`) lets `contentType="music"` override `format="dvd"`, and `_emit_audio_rdf_triples` (`app/core/frbr_service.py`) emits `MusicAlbum`/`MusicRelease`/`musicReleaseFormat` whenever `has_audio_hint` (`catalog_number`, etc.) fires—even on a movie `dvd`—while omitting `bluray_audio`, `cd_dvd_combo`, and `unknown_audio` from `_AUDIO_RELEASE_FORMATS`.

## Goals / Non-Goals

**Goals:**
- Preserve strict FRBR 4-tier purity: `Expression.content_type` (`MediaCategory`) vs. `Manifestation` physical carrier fields (`MediaFormat`), and `UserWorkIntent` conceptual intent vs. `Item` physical ownership.
- Stop generic category tokens (`music`, `audio`, `sound`, `movie`, `video`) from entering `Manifestation` format fields via any enricher, scanner, manual form, import, or API endpoint.
- Normalize legacy DB records deterministically from `raw_payload` where available and safely degrade ambiguous rows to `unknown_audio`/`unknown_video` without hallucinating `cd` or `dvd`.
- Eliminate every non-audio leak into music/format-filtered shares across owned `Item`s, `UserWorkIntent` wishlist items, PG FTS, SQLite `ILIKE`, JSON, SSR HTML, JSON-LD, RDF Turtle, and RSS, while preserving `visibility_scope` (`public_only` + Friend Bonus, `friends_and_public`, `all`) and `Cache-Control: private, no-store` guarantees.

**Non-Goals:**
- Performing outbound network calls to MusicBrainz/Discogs inside an Alembic migration transaction to resolve ambiguous legacy items lacking `raw_payload` (custodians may optionally use `scripts/fix_physical_kinds.py --interactive` or `scripts/refetch_metadata.py` post-deploy).
- Modifying `Token Scope + Friend Bonus Resolution Across All Share Outputs` in `openspec/changes/v110-pass2-review-remediation-and-finalization/`.
- Removing valid multi-carrier music formats (`cd_dvd_combo`, `bluray_audio`) from `music` shares.

## Decisions

### Decision 1: FRBR Ontological Boundary & Multi-Field Format Synchronization
- **Choice:** Canonicalize `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` to the same `MediaFormat` slug (`shared/taxonomy.yaml`) on every write/update/backfill, while keeping `Expression.content_type` strictly in `MediaCategory` (`music`, `movie`, `text`, `audiobook`, `board_game`, `puzzle`, `lego`). Preserve `Manifestation.raw_payload` across `IngestService` barcode and metadata ingestion.
- **Alternatives Considered:**
  1. *Keep `FormatNormalizer` read-only and leave raw `"music"`/`"audio"`/`"sound"` in DB:* Rejected because `Manifestation.format` and `format_type` already exist as indexed columns read directly by `items.py`, `_serialize_shared_collection_item`, and SQL filters, causing persistent drift between DB queries and display layers.
  2. *Drop `meta['format']` immediately:* Rejected because backward-compatible JSONB readers and user-facing `format_mappings.yaml` tooling expect `meta['format']` parity. Syncing all three fields eliminates drift without breaking callers.
- **Validation tightening:** Update `validate_format_type()` (`app/core/f3_validation.py`) or a dedicated ingest/F3 canonicalizer helper so category-only tokens (`{"music", "audio", "sound", "movie", "video", "text", "book_category"}` — careful: `"book"` IS a valid `MediaFormat`, whereas `"text"`, `"music"`, `"audio"`, `"sound"`, `"movie"`, `"video"` are category/alias tokens) are normalized via `FormatNormalizer.normalize(val, content_type)` when `strict=False` (or rejected when `strict=True`), while keeping non-category unknown test strings like `"future_format"` intact where explicitly tested (updating `tests/test_f3_column_promotion.py` where appropriate).

### Decision 2: `shared/format_mappings.yaml` Default Mapping (`unknown_audio` vs. `cd`) & `expand_format_filter`
- **Choice:** Replace `audio: cd` in `shared/format_mappings.yaml` with `audio: unknown_audio`, `music: unknown_audio`, and `sound: unknown_audio`. Update `expand_format_filter()` (`app/core/format_normalizer.py`) to invert both `FormatNormalizer._mappings` and `FORMAT_ALIAS_TO_CATEGORY` (so `?format=unknown_audio` expands to include `"unknown_audio"`, `"audio"`, `"music"`, `"sound"`, plus `NULL` when scoped to `"music"` or `unknown_*` placeholders). Update `CatalogFilterBuilder._apply_format`, `SearchService._pg_manifestation_fts` / `_pg_item_fts`, and `DataManager` faceting to inspect `coalesce(Manifestation.format, Manifestation.format_type, Manifestation.meta['format'])` / multi-column OR matching with `Expression.content_type` context.
- **Alternatives Considered:**
  1. *Keep `audio: cd` in `shared/format_mappings.yaml`:* Rejected because it violates iqoqo's *"Do Not Hallucinate Metadata"* rule and actively mislabels vinyl, cassette, SACD, and digital releases whose upstream payload collapsed to `"audio"`.
  2. *Use `unknown_audio` only in Python without updating `shared/format_mappings.yaml`:* Rejected because `FormatNormalizer` gives `shared/format_mappings.yaml` precedence over `FORMAT_ALIAS_TO_CATEGORY`, so leaving `audio: cd` in YAML would keep overriding `unknown_audio`.

### Decision 3: Hybrid Backfill Strategy (Linear Alembic Migration + Modernized `scripts/fix_physical_kinds.py`)
- **Choice:** Implement a **Hybrid** backfill:
  1. **Linear Alembic Data Migration** branching off `down_revision = "v1_1_0_serial_issn_issues"` with `len(revision) <= 32` (e.g., `v1_1_1_norm_legacy_formats`, 25 chars). Uses SQLAlchemy 2.0 `sa.select()` + keyset pagination (`Manifestation.id > last_id`, `BATCH_SIZE = 500`) across both PostgreSQL and SQLite:
     - First attempts deterministic carrier recovery from `Manifestation.raw_payload` (reusing pure carrier-extraction helpers shared with `musicbrainz.py` / `discogs.py` / `allegro.py`) and unambiguous `meta` fields (`music_release_format`, `video_format`).
     - Normalizes remaining generic category values (`"music"`, `"audio"`, `"sound"` -> `"unknown_audio"`; `"movie"`, `"video"` -> `"unknown_video"`) and synchronizes `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` (storing optional `meta['_legacy_format']` only if needed for non-destructive rollback, or logging counts per rule).
     - **Note on `downgrade()`:** Data normalization of malformed generic tokens is effectively forward-only unless `_legacy_format` provenance is preserved or `downgrade()` is documented as a no-op / restores `_legacy_format` if present; preserve `raw_payload` untouched so provenance is never lost.
  2. **Modernized `scripts/fix_physical_kinds.py`:** Migrate all legacy `.query` / `db.session.query` calls to SQLAlchemy 2.0 `select()`/`update()`, inspect and synchronize all three fields (`meta['format']`, `format`, `format_type`), add `raw_payload` recovery hints to audit/apply output, fix PostgreSQL `COALESCE(CAST(meta AS jsonb), '{}'::jsonb)` for `NULL` `meta`, batch updates via keyset pagination (`id > last_id`, `LIMIT 500`), and support flagging `unknown_audio` rows for custodian interactive review (`--interactive`).
- **Alternatives Considered:**
  1. *Alembic migration only:* Automatically converges all environments on deploy, but cannot provide interactive custodian resolution or `--dry-run` reporting for `unknown_audio` rows later.
  2. *CLI script (`scripts/fix_physical_kinds.py`) only:* Supports `--dry-run` and `--interactive`, but requires manual execution after deploy and risks leaving preview/prod instances with stale `"music"`/`"audio"`/`"sound"` rows.
  - *Trade-off of Hybrid:* Slightly more shared helper code (a pure `recover_carrier_from_raw_payload()` utility callable by both migration and CLI), in exchange for guaranteed zero-touch convergence on deploy plus ongoing operational audit/remediation tooling.

### Decision 4: Unified `SharedCollection` Filtering & `FORMAT_TO_CATEGORY` Consistency Guard
- **Choice:** Extract a single shared filtering pipeline in `app/api/public_items.py` consumed by `fetch_shared_collection_with_cache_policy` (RDF, Turtle, content-negotiated JSON-LD, RSS) and `get_shared_collection` (JSON):
  - Parse `filters` canonically: merge `tags` and `category` (scalar or list), normalize category aliases via `FORMAT_ALIAS_TO_CATEGORY`, parse `format` (and `formats` alias) via `expand_format_filter()`.
  - **Fail-closed empty filter arrays:** If `"tags"`, `"category"`, or `"format"` is explicitly present with an empty list (`[]`) or unrecognized scalar/type, add `sa.false()` (mirroring `status: []` behavior) rather than widening to the entire library.
  - **`FORMAT_TO_CATEGORY` cross-tier guard:** When category filter `C` (e.g. `{"music"}`) is active, in addition to `Expression.content_type.in_(categories)`, exclude any `Manifestation` whose resolved non-null canonical format (`Manifestation.format`, `Manifestation.format_type`, `Manifestation.meta['format']`) belongs to a different category in `FORMAT_TO_CATEGORY` (e.g., `dvd` -> `"movie"` != `"music"`). Compute the allowed-or-null format set directly from `FORMAT_TO_CATEGORY` + category aliases (`unknown_audio`, `cd`, `vinyl`, `sacd`, `cassette`, `minidisc`, `cd_dvd_combo`, `bluray_audio`) so the guard executes purely in SQL across both PostgreSQL FTS and SQLite `ILIKE`.
  - Pass normalized `category` and `format_filter` into `SearchService.search_items()` and update `_pg_item_fts` + `CatalogFilterBuilder._apply_format` to match across `(Manifestation.format, Manifestation.format_type, Manifestation.meta['format'])`.
- **Alternatives Considered:**
  1. *Trust `Expression.content_type` alone:* Rejected because cross-tier drift (a movie `dvd` under a `music` expression, or `cd_dvd_combo` ambiguity) leaks directly into shares.
  2. *Post-filter in Python after SQL `LIMIT`/`OFFSET`:* Rejected per iqoqo's SQL pagination rule — post-filtering corrupts `total`, `pages`, and `per_page` page counts. Encoding the `FORMAT_TO_CATEGORY` guard as a SQL predicate preserves exact SQL `LIMIT`/`OFFSET` counts.

### Decision 5: `UserWorkIntent` Wishlist Query Parity & Bound Realization Resolution
- **Choice:** Apply the same normalized `category`, `format`, and `FORMAT_TO_CATEGORY` predicates to the `UserWorkIntent` query in `get_shared_collection` (and document wishlist vs. RDF surface alignment):
  - Eager-load `UserWorkIntent.expression` and `UserWorkIntent.manifestation` alongside `work -> expressions -> manifestations`.
  - When `intent.manifestation_id` or `intent.expression_id` is bound, filter against that bound `Expression.content_type` and `Manifestation` carrier format; when unbound (Work-level intent), match when at least one `Expression` (and matching `Manifestation`, if `format` filter is active or to verify `FORMAT_TO_CATEGORY`) on the `Work` satisfies the category/format filters.
  - Serialize `content_type`, `format`, `ean`, `upc`, `publisher`, `publication_year`, `catalog_number`, and `country` on wishlist items using the bound `Expression`/`Manifestation` (falling back to the matching `Work` realization) so JSON and SSR JSON-LD render accurate types instead of `"CreativeWork"` or empty metadata.
- **Alternatives Considered:**
  1. *Exclude wishlist items whenever `tags`/`format` filters are active:* Rejected because collectors deliberately share filtered wishlists (e.g. "Music Wishlist — Vinyl").

### Decision 6: Type-Safe JSON-LD & RDF Serialization (`share-server.tsx`, `schema-org.ts`, `frbr_service.py`)
- **Choice:**
  - In `renderSharedCollectionJsonLdView` (`frontend/lib/share-server.tsx`), replace the hardcoded audio-only `@context` shortcuts (`a: "byArtist"`, `f: "musicReleaseFormat"`, `l: "recordLabel"`) with type-safe per-item serialization: resolve `@type` per item via `resolveSchemaType(item.content_type, undefined, item.format)`, emit `musicReleaseFormat`/`byArtist`/`recordLabel` only when `@type` is `MusicAlbum` or `MusicRelease`, and use neutral Schema.org properties (`author`, `publisher`, `isbn`/`gtin13`, `datePublished`, `encodingFormat`) for non-audio items (`Movie`, `Book`, `Game`, `Product`).
  - In `resolveSchemaType` (`frontend/lib/schema-org.ts`), check explicit carrier-format category overrides (`dvd`/`bluray`/`vhs`/`4k_uhd`/`laserdisc` -> `"Movie"`, `magazine` -> `"Periodical"`, `audiobook*` -> `"Audiobook"`) **before** trusting `normType` (`contentType`), preventing drifted `contentType="music"` + `format="dvd"` from resolving to `"MusicAlbum"`.
  - In `app/core/frbr_service.py`, expand `_AUDIO_RELEASE_FORMATS` with `"bluray_audio"`, `"cd_dvd_combo"`, and `"unknown_audio"`, align `_AUDIO_CONTENT_TYPES` (`{"music", "audio", "sound"}`), and guard `_emit_audio_rdf_triples()` so that if `norm_fmt` is a known `FORMAT_TO_CATEGORY` format belonging to a non-music category (e.g., `"dvd"` -> `"movie"`), audio triples (`schema:MusicAlbum`, `schema:MusicRelease`, `schema:musicReleaseFormat`) are **never** emitted even when `has_audio_hint` (`catalog_number`, etc.) or drifted `content_type` is present.
- **Alternatives Considered:**
  1. *Rely solely on share query filtering without fixing serializers:* Rejected because existing unfiltered mixed shares (or direct RDF exports of mixed collections) would still corrupt non-audio items with `MusicAlbum`/`musicReleaseFormat`.

### Decision 7: OpenSpec Capability Packaging Without Merge Conflict
- **Choice:** Place new share filtering & wishlist parity requirements in a new capability `shared-collection-type-integrity`, use `## ADDED Requirements` in `shared-collection-visibility-scope` (for `ShareCollectionDialog` and `SharedCollectionCreateSchema`), and modify `format-normalization`, `format-mapping-cli`, and `shared-collection-ai-feed`. This avoids touching `Token Scope + Friend Bonus Resolution Across All Share Outputs` in `v110-pass2-review-remediation-and-finalization`.

## Risks / Trade-offs

- **[Risk] Existing unit tests assert legacy behavior** (`tests/test_bluray_audio.py` pins `"audio"` fallback for CD/non-Blu-ray; `tests/test_f3_column_promotion.py` checks `"future_format"` pass-through in non-strict mode; `tests/test_format_normalizer.py` isolated YAML masks `shared/format_mappings.yaml` `audio: cd`; `tests/test_catalog_filter_builder.py` checks single-column `meta['format']`) -> **Mitigation:** Explicitly include test expectation updates in `tasks.md`, distinguish category/alias tokens (`music`/`audio`/`sound`/`movie`/`video`) from unknown future format pass-through if needed, and verify all suites pass.
- **[Risk] Ambiguous legacy rows (`raw_payload = NULL`) normalize to `unknown_audio` instead of `cd`** -> **Mitigation:** Surface clear `unknown_audio` counts in `scripts/fix_physical_kinds.py` audit output and UI ("Unknown Audio Format") so custodians can optionally re-enrich or map via `--interactive` without silently mislabeling vinyl/cassettes as CDs.
- **[Risk] Data migration on large `manifestations` tables could lock rows or exhaust memory** -> **Mitigation:** Keyset batching (`WHERE id > last_id ORDER BY id ASC LIMIT 500`) using SQLAlchemy 2.0 `select()`, compatible with both PostgreSQL (`COALESCE(CAST(meta AS jsonb), '{}'::jsonb)`) and SQLite, plus idempotency on re-run.
- **[Risk] `UserWorkIntent` unbound Work-level filtering when a `Work` spans multiple `Expression`s/categories** -> **Mitigation:** Prioritize `intent.expression_id` and `intent.manifestation_id` when bound, and use `EXISTS` subqueries over `Work -> Expression -> Manifestation` when unbound to avoid duplicate wishlist rows or 1-to-many join inflation.

## Migration Plan

1. Deploy code changes (enricher extractors, write-time normalizers, `shared/format_mappings.yaml`, `expand_format_filter`, share query helper, serializers, `ShareCollectionDialog`).
2. Run `flask db upgrade` (executes linear migration off `v1_1_0_serial_issn_issues` in batches of `500` rows, upgrading `raw_payload`-determinable rows to canonical formats, converting residual `music`/`audio`/`sound` to `unknown_audio`, and syncing `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']`).
3. Refresh search indexes (`FTS` / `tsvector` update if triggered outside ORM hooks) and run `make fix-physical-kinds` in audit mode to confirm zero remaining generic category strings (`music`, `audio`, `sound`, `movie`, `video`) and inspect any `unknown_audio` count.
4. **Rollback:** Code changes revert cleanly via Git/container rollback. Because `Manifestation.raw_payload` is never overwritten by the migration (and legacy raw format strings were lossy category names), `downgrade()` should safely restore any preserved `_legacy_format` tag if recorded or operate as a schema-compatible data no-op without breaking `v1_1_0_serial_issn_issues`.
