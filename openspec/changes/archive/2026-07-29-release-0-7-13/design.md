## Context

v0.7.13 is a hardening-and-integrity release sitting between the shipped v0.7.12 and the v0.7.14 security release. Four problem areas converge:

1. **JSON sprawl**: FRBR entities (`Work`, `Expression`, `Manifestation`, `Item` in `app/db/core.py`) store core bibliographic properties in a loose `meta = db.Column(db.JSON, default=dict)` blob. Per-media conventions are only documented as constants (`MANIFESTATION_AUDIO_META_KEYS` in `app/db/audio.py`, `MANIFESTATION_GAME_META_KEYS` in `app/db/games.py`) with no schema enforcement, no indexing, and no relational integrity. This blocks performant querying and the v0.8.0 RDF/JSON-LD mapping.
2. **Escaping bugs**: titles containing apostrophes (`Ocean's Eleven`, `L'Armée des Ombres`) fail in full-text search (`websearch_to_tsquery('simple', :q)` in `app/core/search_service.py`) and in faceted filtering (`ilike(f"%{g_clean}%")` patterns in `app/api/filters.py`).
3. **Version reporting**: `Config.VERSION` resolves `APP_VERSION` env → `pyproject.toml` → `"dev-local"` (`app/config.py`). The production container ships neither, so the Allegro User-Agent (`f"{Config.ALLEGRO_APP_NAME}/{Config.VERSION} (+https://iqoqo.cc)"` in `app/utils/allegro.py`) identifies as `/dev`-flavored, polluting vendor-side analytics and our own telemetry.
4. **Format & ontology gaps**: `shared/taxonomy.yaml` music formats stop at `sacd`/`cd_dvd_combo` — no BluRay Pure Audio. Concerts have no ontological home. Groundwork for FRBRoo events already exists (`WorkContribution`/`ExpressionContribution` in `app/db/audio.py`, `ManifestationContribution` in `app/db/video.py`, `ContainerAggregation` in `app/db/games.py`) but is not generalized or wired into ingestion/display.

## Goals / Non-Goals

**Goals:**

- Normalize core bibliographic properties into typed relational columns per FRBR entity with a reversible, batched Alembic ETL migration and exhaustive migration tests.
- Preserve external API payloads in a read-only `raw_payload` JSONB audit column for provenance and re-scraping resilience.
- Make apostrophe-bearing titles round-trip correctly through FTS and faceted filters.
- Guarantee the deployed backend reports its real release version to external vendors.
- Add BluRay HiFi Pure Audio as a canonical music format end-to-end.
- Model concerts as Performance Event Expressions realized in video/audio Manifestations; generalize Composition/Performance/Publication events across strategies; wire board game F16 Container aggregation into ingestion and display.
- Ship an idempotent data-correction for manifestation 1984 (Movie/BluRay) and a Makefile-invocable batch watermarking CLI.

**Non-Goals:**

- No new top-level media category for concerts (it is an Expression-level typing, not a scanner category).
- No UI redesign of the FRBR editor (scheduled for v0.7.15).
- No security work (XXE/SSRF/rate limiting scheduled for v0.7.14).
- No SPARQL/RDF endpoint work (v0.8.0) — normalization only prepares the relational substrate.
- Not all `meta` keys become columns: long-tail, per-media, and provider-specific keys stay in `meta` under the documented key conventions.

## Decisions

- **Normalize only "core" keys, keep `meta` for the long tail.** We extract properties that are (a) queried/filtered/sorted across all media or (b) required for strict FRBR graph integrity — e.g. `Manifestation.format`, publisher, release date, EAN/ISBN/identifiers, `Work.title` sort keys, `Expression.language`/expression type. Per-media keys (`track_list`, `matrix_number`, `min_players`, …) remain in `meta` JSONB governed by the existing `*_META_KEYS` constants. Alternative considered: full JSONB→relational flattening — rejected as over-engineering that would explode the schema and migration surface for rarely-queried data.
- **Dual-write cutover via one Alembic ETL migration, not incremental dual-writing.** A single migration revision (a) adds columns + indexes, (b) backfills from `meta` in server-side batched `UPDATE ... FROM (SELECT id, meta->>...)` statements, (c) leaves `meta` in place as the fallback read source. The service layer reads normalized-columns-first with `meta` fallback for one release; `meta` cleanup of migrated keys is deferred to a later release to keep rollback trivial. Alternative considered: application-level dual-write before migration — rejected; it prolongs the inconsistent window and complicates v0.7.12 hotfixing.
- **`raw_payload` audit column.** External provider payloads (BGG, Discogs, TMDB, MusicBrainz, Allegro) are stored verbatim in a read-only JSONB column at ingestion time, separate from curated `meta`. This decouples provenance from curation and enables future re-scraping without re-calling vendors.
- **Apostrophe fix at three layers.** (1) Ingestion/normalization: canonicalize typographic apostrophes (`’`, `‘`, `ʼ`) to ASCII `'` when building `fts_simple` vectors and facet keys, so stored data is uniform. (2) Query side: sanitize user input before `websearch_to_tsquery` (strip/quote characters that the parser treats as operators) and parameterize all facet `ilike` values with explicit `ESCAPE` handling for `%`/`_`/`\`. (3) Regression tests pinning `Ocean's Eleven`-style titles through search + facet round-trips. Alternative considered: replacing `websearch_to_tsquery` with `plainto_tsquery` — rejected, it would silently drop the advanced query syntax users may already rely on.
- **Fix version at deploy, not in code lookup order.** Bake `APP_VERSION` into the production image (Docker `ARG` from the repo `VERSION`/`pyproject.toml`, promoted to `ENV APP_VERSION`) and assert at container health-check that `Config.VERSION` is not a `dev*` sentinel on prod. Add a pytest asserting the Allegro UA matches `^{ALLEGRO_APP_NAME}/\d+\.\d+\.\d+ \(\+https://iqoqo\.cc\)$` with the prefix read from `Config.ALLEGRO_APP_NAME` (env-configurable per deployment: `iqoqo_cc`/`iqoqo_pre`/`iqoqo_dev`) — never hardcoded — when `APP_VERSION` is set. Alternative considered: shipping `pyproject.toml` in the image — rejected as the sole fix; env-baked version is explicit, observable, and matches the twelve-factor posture already used elsewhere.
- **BluRay Pure Audio = new music format `bluray_audio`, not a video format.** Add `bluray_audio` (label "Blu-ray Pure Audio") under the `music` category in `shared/taxonomy.yaml`, alias raw values (`Blu-ray Audio`, `BD-A`, `BluRay HiFi`, `Pure Audio Blu-ray`) in `format_aliases` / `format_mappings.yaml`, run `make generate-taxonomy` to sync generated types/frontend constants, and teach `app/strategies/audio.py` + the video strategy boundary that a music Work with a BD carrier resolves to `music`/`bluray_audio`. This keeps faceted counts honest: a HiFi Pure Audio disc of a studio album is music, not a movie.
- **Concerts = Performance Event Expression + video/audio Manifestation.** We add an `expression.kind` (e.g. `live_performance`) on the Expression linked to `ExpressionContribution` (Performance Event) rows capturing performers/venue/date; the Manifestation carries the carrier format (`dvd`/`bluray`/`cd`). Facets and badges derive "Concert" from `expression.kind`, never from a genre tag or item-level flag — preserving the v0.7.12 ontological guardrail that studio albums and live recordings must not conflate.
- **Generalize events by reuse, not new tables.** Composition (`WorkContribution`), Performance (`ExpressionContribution`), Publication (`ManifestationContribution`) tables already exist; we (a) move/confirm them as shared catalog-schema entities usable by every strategy, (b) ensure each media strategy populates the appropriate event rows at ingestion, (c) expose them in manifestation/expression API payloads. No parallel per-media contribution tables.
- **Board games: activate the existing F16 model.** `ContainerAggregation` stays the single aggregation mechanism; we wire it into the board-game ingestion path (creating a Rulebook aggregated Work plus board/pieces aggregated components) and surface contents on the manifestation view. The box itself is the container Work; the rulebook is an aggregated Work; physical components are aggregated items/components — no format tags pretending to be structure.
- **Data correction as an idempotent script, run once per environment.** A small `scripts/` job (guarded by manifestation id + current state check) remaps manifestation 1984 to `movie`/`bluray`, recorded in tasks; it must be safe to re-run and produce a no-op.
- **Watermark CLI reuses `app/utils/images.py` primitives.** A module entrypoint (e.g. `python -m app.utils.images watermark-batch --root <covers-dir> [--dry-run]`) walks stored cover art, applies the existing overlay/watermark primitive idempotently (skip files whose perceptual hash is already watermarked), and is wrapped in a `make batch-watermark` target with pytest + BATS coverage, matching the `validate-yaml`/`fix-physical-kinds` precedent.

## Risks / Trade-offs

- [Risk] ETL backfill mis-maps a `meta` key and silently corrupts the catalog graph. → Mitigation: exhaustive migration tests (row-count parity, per-key spot checks, graph integrity assertions) plus a rehearsal on a production DB clone before deploy; migration is batched and reversible.
- [Risk] Dual-source reads (column-first, `meta` fallback) mask partial backfills. → Mitigation: a post-migration verification query comparing column vs `meta` values, failing deploy health on drift beyond zero rows.
- [Risk] Apostrophe canonicalization changes existing facet groupings (e.g. `'` vs `’` buckets merge). → Mitigation: intended behavior; ship a one-time facet key rebuild in the same migration and call it out in CHANGELOG.
- [Risk] `bluray_audio` misclassification of video concert BDs (and vice versa) degrades facet trust. → Mitigation: decision rule is Work-driven: if the Expression is `live_performance` of a musical Work, carrier `bluray` under `movie`; studio/album audio on BD is `music`/`bluray_audio`; strategy-level tests pin the boundary.
- [Risk] Batch watermarking is CPU-heavy on large libraries and could reprocess files. → Mitigation: idempotency via perceptual-hash skip list, `--dry-run` default-safe flags, and processing outside the request path (Makefile/CLI only).
- [Risk] Baking `APP_VERSION` at build time can drift from runtime checkouts. → Mitigation: single source of truth in `pyproject.toml`/`VERSION` consumed by both `make sync-version` and the Docker build arg; CI fails the build if they disagree.

## Migration Plan

1. Land taxonomy + strategy changes (`bluray_audio`, concert `expression.kind`) — additive, no data movement.
2. Deploy the normalization migration on staging clone; run verification queries; rehearse `downgrade()` one step.
3. Deploy to prod with the backfill in the same release; run the manifestation-1984 correction script post-deploy.
4. Rebuild facet keys / FTS vectors affected by apostrophe canonicalization (migration-embedded rebuild).
5. Rebuild the prod image with `APP_VERSION` baked; confirm telemetry shows the real UA.
6. Rollback: one-step Alembic downgrade drops new columns (meta untouched); taxonomy additions are backward-compatible and need no rollback.

## Open Questions

- Exact per-entity column list (final inventory of "core" keys) to be frozen in the first implementation task before writing the migration.
- Whether `expression.kind` needs a controlled vocabulary beyond `live_performance` in this release (e.g. `remix`, `directors_cut`) — default: only what concerts require.
- Watermark placement/opacity parameters for the batch run — reuse current single-image defaults unless the custodian overrides via flags.
