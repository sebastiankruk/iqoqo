## Why

Release v0.7.13 is the mid-train hardening milestone between the shipped v0.7.12 (Custodian Workflows & Scanner UX) and the v0.7.14 security release. Core bibliographic properties are still trapped in loose JSON `meta` blobs on FRBR entities, which blocks performant relational querying and complicates the v0.8.0 Linked Open Data work; apostrophes in titles silently break search and faceted filtering; the Allegro integration reports a `/dev` User-Agent on production; and collectors cannot catalog BluRay HiFi Pure Audio releases, concerts, or properly structured board game boxes. This release eradicates that JSON sprawl, fixes the escaping bugs, and expands media format support on a strict FRBR/FRBRoo ontological foundation.

## What Changes

- **Data Normalization (BREAKING schema)**: Migrate core bibliographic properties out of the loose `meta` JSON columns on `Work`, `Expression`, `Manifestation`, and `Item` (`app/db/core.py`) into dedicated relational columns via a reversible Alembic ETL migration. External API payloads are preserved in a read-only `raw_payload` JSONB audit field for provenance and re-scraping resilience.
- **ETL Migration Testing**: Write exhaustive Alembic data-migration pipeline tests proving zero data loss and zero FRBR graph corruption when transforming flat SQL / JSON blobs into the strict normalized graph.
- **Bug Fix — Apostrophes**: Fix single quote (`'`) handling in titles across full-text search and faceted filtering (`app/core/search_service.py`, `app/api/filters.py`) so titles like *Ocean's Eleven* or *L'Armée des Ombres* are findable and filterable.
- **Bug Fix — Allegro User-Agent**: Fix the `/dev` version reporting in the Allegro User-Agent header on the production environment (`app/utils/allegro.py`) so outbound requests identify with the configured `ALLEGRO_APP_NAME` and the real release version (e.g. `iqoqo_cc/0.7.13`) instead of a `/dev` version sentinel.
- **Format Expansion**: Add BluRay HiFi Pure Audio support to the music category (`shared/taxonomy.yaml`, `shared/format_mappings.yaml`, `app/strategies/audio.py`).
- **Data Correction**: Ship an idempotent data-fix migration/script remapping production manifestation `1984` (`https://iqoqo.cc/manifestation/1984`) to Movie / BluRay.
- **Concert Support**: Catalog concerts ontologically as an `Expression` of a Performance Event, realized in a video `Manifestation` (CD/BluRay/DVD) — never flattened into genre tags on physical items.
- **Event-Based Modeling**: Complete and generalize FRBRoo event entities — Composition Event (`WorkContribution`), Performance Event (`ExpressionContribution`), Publication Event (`ManifestationContribution`) — across all media strategies.
- **Board Games as F16 Container Work**: Wire the existing `ContainerAggregation` model into ingestion and display so a board game box aggregates a Rulebook Work plus board/pieces components.
- **Automation**: Add a standalone batch watermarking process in `app/utils/images.py`, invocable as a Makefile batch operation with pytest coverage.

## Capabilities

### New Capabilities

- `relational-metadata-normalization`: Relational schema for core bibliographic properties previously held in JSON `meta`, the reversible ETL migration, `raw_payload` provenance preservation, and zero-data-loss guarantees.
- `search-special-character-handling`: Correct escaping, tokenization, and matching of apostrophes/single quotes in titles across search and faceted filtering.
- `hifi-audio-format-support`: BluRay HiFi Pure Audio as a canonical music format end-to-end (taxonomy, normalizer, audio strategy, UI labels).
- `concert-modeling`: Concert releases modeled as Performance Event Expressions realized in audio/video Manifestations.
- `event-based-modeling`: FRBRoo Composition, Performance, and Publication Events as first-class contribution entities shared by all media strategies.
- `board-game-container-aggregation`: Board games modeled as FRBRoo F16 Container Works aggregating rulebook Works and physical components.
- `batch-watermarking`: Makefile-invocable batch watermarking CLI for existing cover art.

### Modified Capabilities

- `format-normalization`: The normalizer must resolve BluRay Pure Audio raw values (e.g., `"Blu-ray Audio"`, `"BD-A"`) to the new canonical music format.
- `frbr-ontology`: Boundary rules extended with FRBRoo event entities (Composition/Performance/Publication), F16 Container Work aggregation, and the concert hierarchy rule (Work → Performance Expression → video/audio Manifestation).
- `external-api-telemetry`: Outbound Allegro requests must carry a User-Agent built from the real deployed release version, never `/dev` on production.

## Impact

- **Database (BREAKING)**: New Alembic migration alters `works`, `expressions`, `manifestations`, `items` tables (new relational columns, `raw_payload` audit column); requires the ETL backfill to run at deploy time. Rollback path must be rehearsed on a production DB clone.
- **Backend**: `app/db/models.py`/`app/db/core.py`, `app/core/frbr_service.py`, `app/core/data_manager.py`, `app/core/search_service.py`, `app/api/filters.py`, `app/utils/allegro.py`, `app/strategies/audio.py`, `app/utils/images.py`.
- **Shared config**: `shared/taxonomy.yaml`, `shared/format_mappings.yaml` (new format IDs require `make generate-taxonomy` regeneration and frontend type sync).
- **Frontend**: Format labels/icons for BluRay Pure Audio and concert badges flow from regenerated taxonomy types; no new routes.
- **Ops**: New `Makefile` batch target for watermarking; one-off idempotent data-correction script for manifestation 1984 executed against prod after deploy.
- **Testing**: Pytest ETL migration suite, search escaping regression tests, format strategy tests, Makefile/BATS coverage for the watermark target.
