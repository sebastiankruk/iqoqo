## 1. Taxonomy & Format Expansion (additive — no data movement)

- [x] 1.1 Add `bluray_audio` (label "Blu-ray Pure Audio") under the `music` category in `shared/taxonomy.yaml`, including format aliases for `Blu-ray Audio`, `BD-A`, `BluRay HiFi`, `Pure Audio Blu-ray`.
- [x] 1.2 Add `format_normalizations` entries for BluRay audio raw values in `shared/format_mappings.yaml` and run `make validate-yaml`.
- [x] 1.3 Run `make generate-taxonomy` and commit regenerated backend constants + frontend types; fix any type drift in the frontend.
- [x] 1.4 Teach `app/strategies/audio.py` (and the video strategy boundary) the Work-driven classification rule: music Work on BD carrier → `music`/`bluray_audio`; live-performance Expression on BD carrier → `movie`/`bluray`.
- [x] 1.5 Add pytest strategy tests pinning the classification boundary (BluRay-audio music release → `music`/`bluray_audio`; concert BD → not `bluray_audio`) and normalizer tests for the new aliases.

## 2. Event-Based Modeling & FRBR Integrity

- [x] 2.1 Audit and confirm `WorkContribution`, `ExpressionContribution`, `ManifestationContribution`, and `Contributor` are shared catalog-schema entities importable by all strategies (text, audio, video, board game, puzzle); consolidate any per-media duplication.
- [x] 2.2 Add `expression.kind` support (controlled vocabulary, initial value `live_performance`) to the Expression model with an Alembic migration and service-layer accessors in `app/core/frbr_service.py`.
- [x] 2.3 Wire concert ingestion: live recordings create/link a Performance Event Expression (`kind = 'live_performance'`, `ExpressionContribution` performers + venue/date when available) realized in a video/audio Manifestation — never genre tags or item flags.
- [x] 2.4 Expose event contributions (creators/performers/publishers) in Work, Expression, and Manifestation API payloads; update facet computation so live performances are distinguishable from studio releases.
- [x] 2.5 Wire board game ingestion to create F16 Container Work structure via `ContainerAggregation` (rulebook as aggregated Work, board/pieces/cards as components) and surface contents in the manifestation API payload and detail view.
- [x] 2.6 Add pytest coverage: event-level boundary integrity (creator → Work, performer → Expression, publisher → Manifestation), concert graph shape, container aggregation check-constraint behavior, and payload exposure.

## 3. Data Normalization (Schema & ETL Migration)

- [x] 3.1 Freeze the per-entity inventory of "core" keys to promote (manifestation format/publisher/release date/identifiers, expression language/kind, work title sort keys) and document what stays in `meta` per the `*_META_KEYS` constants.
- [x] 3.2 Add the new typed relational columns and indexes to `app/db/core.py` (`works`, `expressions`, `manifestations`, `items`) plus the read-only `raw_payload` JSONB audit column.
- [x] 3.3 Write the Alembic migration: schema changes + batched server-side backfill from `meta` into the new columns; implement a reversible `downgrade()` that drops the new columns without touching `meta`.
- [x] 3.4 Persist verbatim provider payloads to `raw_payload` at ingestion time in all external-metadata strategies (BGG, Discogs, TMDB, MusicBrainz, Allegro).
- [x] 3.5 Refactor `app/core/frbr_service.py` and `app/core/data_manager.py` to read normalized properties column-first with `meta` fallback for NULL columns.
- [x] 3.6 Add a post-migration verification query/health check comparing column vs `meta` values, failing deploy health on non-zero drift.

## 4. ETL Migration Pipeline Tests

- [x] 4.1 Build representative flat-SQL/JSON fixtures (per media type, including edge cases: NULL meta, typographic apostrophes, missing keys).
- [x] 4.2 Write pytest migration tests asserting row-count parity, per-key value parity, and FRBR graph integrity (Work → Expression → Manifestation → Item links) after upgrade.
- [x] 4.3 Write a downgrade test asserting `meta` content is unchanged after a downgrade/upgrade round-trip.
- [x] 4.4 Rehearse the migration on a production DB clone (or sanitized dump) and record timings/results in the PR description.

## 5. Core Bug Fixes

- [x] 5.1 Canonicalize apostrophe variants (`’`, `‘`, `ʼ` → `'`) when building `fts_simple` vectors and facet keys; include a one-time rebuild of affected facet keys/vectors in the migration.
- [x] 5.2 Sanitize user input before `websearch_to_tsquery` in `app/core/search_service.py` so quotes/apostrophes never break tsquery parsing or silently empty results.
- [x] 5.3 Parameterize facet `ilike` comparisons in `app/api/filters.py` with explicit escaping of `%`, `_`, `\` metacharacters.
- [x] 5.4 Add pytest regression tests: search finds `Ocean's Eleven`-style titles; facet values with apostrophes/metacharacters match literally; add Playwright/Vitest coverage where facet UI state is involved.
- [x] 5.5 Bake `APP_VERSION` into the production image (Docker build ARG from `pyproject.toml`/`VERSION` promoted to `ENV APP_VERSION`) and add a startup/health validation that fails fast on `dev*` version sentinels in prod.
- [x] 5.6 Add a pytest asserting the Allegro User-Agent matches `^{Config.ALLEGRO_APP_NAME}/\d+\.\d+\.\d+ \(\+https://iqoqo\.cc\)$` (prefix from env config, not hardcoded) when `APP_VERSION` is set; verify post-deploy telemetry shows the real UA.

## 6. Data Correction

- [x] 6.1 Write an idempotent script (guarded by manifestation id + current-state check) remapping manifestation `1984` to `movie`/`bluray`; safe to re-run as a no-op.
- [x] 6.2 Add pytest coverage for the correction script (applies when needed, no-ops when already correct).
- [x] 6.3 Execute the correction script against production after deploy and verify `https://iqoqo.cc/manifestation/1984` renders as Movie / BluRay.

## 7. Batch Watermarking Automation

- [x] 7.1 Add a standalone CLI entrypoint in `scripts/generate_ai_covers.py` (`python scripts/generate_ai_covers.py --batch-all-unwatermarked`) with `--dry-run` and `--limit` support.
- [x] 7.2 Implement idempotent reprocessing via perceptual-hash skip detection so already-watermarked files are never re-watermarked.
- [x] 7.3 Add prompt template resolution and CLI watermarking parameters.
- [x] 7.4 Add pytest coverage (processing, idempotent skip, dry-run).

## 8. Wrap-up

- [x] 8.1 Run the full test suite (Pytest, Vitest, Playwright) and fix regressions.
- [x] 8.2 Update documentation (`docs/CHANGELOG.md`, migration runbook noting the ETL deploy step and rollback rehearsal, taxonomy/format docs for `bluray_audio`).
- [x] 8.3 Bump version to `0.7.13` (`make bump-version` / `make sync-version`).
- [x] 8.4 Update MemPalace CLI graph indexing.
