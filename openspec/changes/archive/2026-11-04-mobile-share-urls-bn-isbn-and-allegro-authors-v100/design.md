# Technical Design: Mobile Share URLs, BN ISBN Fallback, and Allegro Parameter Extraction

## Context

Mobile clients built with Capacitor run on `capacitor://localhost` or `https://localhost`. Hardcoded `window.location.origin` links when shared or opened externally point to the local device. The RSS feed (`/api/public/feed.xml`) served as raw XML causes mobile WebViews to fail. On the backend, unauthenticated Google Books API lookups suffer from quota exhaustion (429), and Polish books lack coverage in Open Library. In addition, Allegro catalog data was omitting authorship parameters during ingestion, leaving items with "Undefined" authors.

See `proposal.md` for motivation and `specs/` for normative requirements.

## Goals / Non-Goals

**Goals:**
- Dynamically resolve public sharing and feed URLs to active instance endpoints (`getSyncInstanceUrl()`).
- Route RSS feeds and outbound shared links on mobile devices through native browser windows (`@capacitor/browser`).
- Expand shared collection search to match diacritics, barcodes, UPCs, and creator names.
- Integrate Biblioteka Narodowa (`data.bn.org.pl`) as an open REST API provider for Polish publications without requiring keys.
- Extract structured parameters (`Autor`, `Tytuł`, `Wydawnictwo`, `Rok`) from Allegro payloads and repair existing catalog data.

**Non-Goals:**
- Introducing external authentication for Biblioteka Narodowa (it is an open, unauthenticated public API).
- Altering core FRBR entity schema (all fields are mapped into existing FRBR Work/Expression/Manifestation models).

## Decisions

### Decision 1: Client URL Resolution via `resolvePublicUrl`
- **Choice**: Introduce `getPublicBaseUrl()` and `resolvePublicUrl(path)` in `frontend/lib/utils.ts`. On native platforms (`Capacitor.isNativePlatform()`), it inspects `getSyncInstanceUrl()` from stored preferences, falling back to `window.location.origin` on web browsers.
- **Alternatives Considered**: Passing backend-rendered URLs in API responses. Rejected because Flask is API-only and client components manage their own navigation state.

### Decision 2: External Browser Delegation for Mobile RSS Feeds
- **Choice**: In `frontend/lib/capacitor/navigation.ts`, implement `openExternalUrl(url)` backed by `@capacitor/browser`. Use this in `PublicFeedButton` and `FreshArrivals` when clicking RSS links on mobile devices.
- **Alternatives Considered**: Rendering RSS XML directly in Next.js or in-app WebView. Rejected because WebView cannot render XML feeds and throws HTTP response code failure errors.

### Decision 3: National Library of Poland (Biblioteka Narodowa) Upstream Provider
- **Choice**: Implement `_lookup_biblioteka_narodowa_outcome` targeting `https://data.bn.org.pl/api/bibs.json?isbnIssn={isbn}`. Trigger automatically for Polish ISBN prefixes (`978-83...` and `979-83...`) when primary providers return empty results.
- **Alternatives Considered**: Requiring Allegro token for all Polish books. Rejected because Allegro requires OAuth configuration and operator credentials, whereas Biblioteka Narodowa is open, free, and needs no keys.

### Decision 4: Parameter Normalization in Allegro and FRBR Serialization
- **Choice**: In `app/utils/allegro.py`, add `_extract_allegro_parameters` to harvest creator names, cleaned titles, publishers, and release years. In `app/api/manifestations.py`, add `_resolve_manifestation_display_author` to fallback from `work.meta["authors"]` to manifestation parameters and contributions. Update `scripts/repair_frbr_authors.py` to backfill database records.
- **Alternatives Considered**: Deleting empty-author manifestations and re-ingesting. Rejected because manifestations already have user item links and historical collections.

### Decision 5: Shared Collection Search Parity with PostgreSQL Full-Text Search
- **Choice**: In `app/api/public_items.py`, route `get_shared_collection` and `fetch_shared_collection_by_token` through `SearchService.search_items` on PostgreSQL. In `app/core/search_service.py`, restrict `build_ilike_search_clause` to specific searchable bibliographic fields (titles, authors, tags, genres, publisher, label, identifiers), removing broad full-JSON dump substring matching (`_meta_text(Manifestation.meta)`). Also pull authors from both Work and Manifestation tiers.
- **Alternatives Considered**: Leaving hand-rolled ILIKE query in public sharing endpoint. Rejected because substring matching over 20KB provider payloads produced 25+ false positives on short query tokens like "dom".

### Decision 6: Native Mobile Anti-Localhost Guarantees
- **Choice**: Hardened `getPublicBaseUrl` to never return `localhost` or `capacitor://localhost` on native apps or localhost origins, falling back to `NEXT_PUBLIC_FRONTEND_URL` / `https://preview.iqoqo.cc`. Eagerly hydrate native preferences on JS module initialization in `storage.ts`, and inject the canonical URL during static export in `build-capacitor.js`.
- **Alternatives Considered**: Requiring explicit server URL input before any share link or RSS button is rendered. Rejected because user experience on cold launch should display clean public links immediately.

### Decision 7: Docker Stack-Aware Operational Catalog Maintenance
- **Choice**: Implemented `POST /api/admin/maintenance/repair-authors` with dry run support, and updated `make repair-authors [preview|prod]` with Docker stack auto-detection for instant one-command repair across both environments.
- **Alternatives Considered**: Requiring operators to manually attach to docker containers with shell heredocs. Prohibited by project guidelines.

## Risks / Trade-offs

- **[Risk] Biblioteka Narodowa API availability or latency spikes** → Mitigation: Governed by the global `max_duration` ceiling (6.0s) and bounded TCP connect timeouts (1.5s min) in `_calc_timeout()`.
- **[Risk] Allegro parameter structure variations** → Mitigation: Checks both `valuesLabels` and `values` across common Polish field names (`Autor`, `Autorzy`, `Wykonawca`, `Twórca`, `Reżyser`), stripping trailing punctuation and deduplicating names.
