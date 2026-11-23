## Why

Inspecting shared music collections revealed two compounding data-integrity defects: 31 audio items carry generic category strings (`music`, `audio`, `sound`) instead of specific physical carrier formats (`cd`, `vinyl`, `unknown_audio`), and non-audio items such as movie DVDs leak into music-filtered shared collections across owned items, wishlist entries, and JSON-LD/RDF outputs. Left unaddressed, upstream enrichers and ingest paths continue persisting category names into `Manifestation` format fields while share endpoints and UI dialogs drop or bypass media-category and carrier-format constraints.

## What Changes

- **Prevent generic category format persistence at ingest & write paths:** Update MusicBrainz and Discogs enrichers to map full audio carrier vocabularies (`cd`, `vinyl`, `cassette`, `sacd`, `minidisc`, `cd_dvd_combo`, `bluray_audio`) with `"unknown_audio"` fallback instead of `"audio"`, and enforce canonical normalization plus `raw_payload` preservation across `IngestService`, scanner preview/lookup, manual item creation, `frbr_service` manifestation CRUD, and `DataManager.import_data`.
- **Synchronize `Manifestation` format fields & read/filter/facet paths:** Keep `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` synchronized on write and backfill; update `shared/format_mappings.yaml` to map `"audio"`, `"music"`, and `"sound"` to `"unknown_audio"` instead of guessing `"cd"`; extend `expand_format_filter` (`FORMAT_ALIAS_TO_CATEGORY` + `NULL` support), `CatalogFilterBuilder`, `SearchService`, and `DataManager` faceting to evaluate all three format fields consistently.
- **Hybrid backfill (Alembic + modernized `scripts/fix_physical_kinds.py`):** Ship a linear, keyset-batched Alembic data migration off `v1_1_0_serial_issn_issues` (`len(revision) <= 32`) and modernize `scripts/fix_physical_kinds.py` to SQLAlchemy 2.0 `select()` with deterministic `raw_payload` carrier recovery, `"unknown_audio"` fallback for ambiguous rows without `raw_payload`, and multi-column synchronization.
- **Enforce `SharedCollection` media-category & format integrity:** Capture `format` alongside `category` filters in `ShareCollectionDialog`, validate/normalize `tags`/`category` and `format` in `SharedCollectionCreateSchema`, unify share filtering across `public_items.py` and `SearchService` (PG FTS and SQLite ILIKE) with fail-closed empty arrays and `FORMAT_TO_CATEGORY` cross-tier guards, extend parity to `UserWorkIntent` wishlist queries and serialization, and make `renderSharedCollectionJsonLdView`, `resolveSchemaType`, and `_emit_audio_rdf_triples` type-safe across all formats (including `bluray_audio` and `cd_dvd_combo`).

## Capabilities

### New Capabilities
- `shared-collection-type-integrity`: Media-category and carrier-format filter enforcement across `SharedCollection` owned items, `UserWorkIntent` wishlist entries, `FORMAT_TO_CATEGORY` cross-tier consistency guards, PG FTS/SQLite search parity, and `visibility_scope` preservation.

### Modified Capabilities
- `format-normalization`: Reject/normalize generic category strings (`music`, `audio`, `sound`, `movie`, `video`) at ingest and manifestation writes, preserve `raw_payload`, sync `Manifestation.format`/`format_type`/`meta['format']`, replace `audio: cd` with `unknown_audio` in `shared/format_mappings.yaml`, and unify filtering/faceting + `expand_format_filter` across all three fields.
- `format-mapping-cli`: Extend `scripts/fix_physical_kinds.py` (paired with Alembic backfill) to use SQLAlchemy 2.0 `select()`, keyset batching, deterministic `raw_payload` carrier recovery, ambiguous `unknown_audio` normalization, and multi-column sync across `format`, `format_type`, and `meta['format']`.
- `shared-collection-ai-feed`: Guard `renderSharedCollectionJsonLdView`, `resolveSchemaType`, and `_emit_audio_rdf_triples` against mis-typing non-audio carriers (e.g., movie `dvd` with `catalog_number` or drifted `content_type`) as `MusicAlbum`/`MusicRelease`, and recognize `bluray_audio`, `cd_dvd_combo`, and `unknown_audio` in audio RDF emission.
- `shared-collection-visibility-scope`: Capture `format` alongside `category` filters in `ShareCollectionDialog` and normalize/validate share filter payloads (`tags`, `category`, `format`) in `POST /api/sharing/` (`SharedCollectionCreateSchema`).

## Impact

- **Backend Core & Enrichers:** `app/utils/musicbrainz.py`, `app/utils/discogs.py`, `app/utils/tmdb.py`, `app/core/ingest.py`, `app/core/format_normalizer.py`, `app/core/f3_validation.py`, `app/core/frbr_service.py`, `app/core/search_service.py`, `app/core/data_manager.py`, `app/core/meta_display.py`, `shared/format_mappings.yaml`.
- **Backend API & Schemas:** `app/api/scanner.py`, `app/api/items.py`, `app/api/manifestations.py`, `app/api/filters.py`, `app/api/sharing.py`, `app/api/public_items.py`, `app/api/public_rdf.py`, `app/api/schemas.py`.
- **Database & CLI:** New linear Alembic migration off `v1_1_0_serial_issn_issues` (`len(revision) <= 32`) and `scripts/fix_physical_kinds.py`.
- **Frontend & i18n:** `frontend/components/collection/share-collection-dialog.tsx`, `frontend/lib/share-server.tsx`, `frontend/lib/schema-org.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests:** Updates to `tests/test_bluray_audio.py`, `tests/test_f3_column_promotion.py`, `tests/test_format_normalizer.py`, `tests/test_fix_physical_kinds.py`, `tests/test_api_public_extended.py`, `tests/test_public_rdf_audio.py`, `tests/test_public_feeds.py`, `tests/test_catalog_filter_builder.py`, and `frontend/__tests__/components/collection/share-collection-dialog.test.tsx`.
