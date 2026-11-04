# Proposal: Mobile Share URLs, Biblioteka Narodowa Fallback, and Allegro Author Extraction

## Why

Native mobile app sharing links and RSS feeds resolved to `localhost` causing runtime crashes, search filtering on shared collections failed to match normalized titles or identifiers, scanning Polish ISBNs failed when Google Books exceeded IP quotas, and items ingested via Allegro exhibited "Undefined" authors due to ignored parameter payloads. Addressing these gaps ensures robust mobile sharing, zero-configuration Polish book cataloging, and complete FRBR authorship integrity across the catalog.

## What Changes

- **Mobile Public URL Resolution & RSS External Browser Routing**: Hardened URL resolution with strict anti-localhost guarantees: on native mobile shells, `getPublicBaseUrl` never returns `localhost` (falling back to canonical `NEXT_PUBLIC_FRONTEND_URL` / `https://preview.iqoqo.cc`), eager preference hydration initializes instance URLs at module load, and the Capacitor static build bakes the public frontend URL into the bundle. Routed RSS feeds (`/api/public/feed.xml`) and external share links through `@capacitor/browser` to prevent WebView crashes.
- **Shared Collection Search Parity & Precision**: Aligned shared collection filtering (`get_shared_collection` and `fetch_shared_collection_by_token`) with PostgreSQL Full-Text Search (`SearchService.search_items`), ensuring 1-to-1 parity with `/collection` search results. Narrowed `build_ilike_search_clause` to target only titles, contributors, authors, tags, genres, publisher, label, and standard identifiers, eliminating false-positive substring matches caused by casting raw provider descriptions and manufacturer addresses (`_meta_text(Manifestation.meta)`) to text. Extracted authors from both Work and Manifestation tiers in shared views.
- **National Library of Poland (Biblioteka Narodowa) ISBN Provider**: Added `_lookup_biblioteka_narodowa_outcome` leveraging `https://data.bn.org.pl` as a free, open, keyless upstream fallback for Polish ISBNs (`978-83-...`), raised lookup ceiling from 3.0s to 6.0s, and loaded Google Books API key from encrypted `InstanceSettings` (`ConfigService`).
- **Allegro Parameter Extraction & FRBR Author Repair**: Extracted bibliographic parameters (`Autor`, `Autorzy`, `Wykonawca`, `Twórca`, `Reżyser`, clean `Tytuł`, `Wydawnictwo`, `Rok wydania`) from Allegro catalog payloads, added manifestation display author fallbacks in API serializers, and enhanced `scripts/repair_frbr_authors.py` to backfill missing authors across existing database records.
- **Admin Maintenance Endpoint & Docker Tooling**: Added authenticated `POST /api/admin/maintenance/repair-authors` endpoint with dry-run support, and added `make repair-authors [preview|prod]` with Docker stack auto-detection for operational catalog maintenance.

## Capabilities

### Modified Capabilities

- `book-provider-fallback-retry`: Extends fallback chain with Biblioteka Narodowa open API for Polish ISBNs, reads Google Books API keys from `ConfigService`, and extends lookup duration ceiling to 6.0 seconds.
- `shared-collection-ui`: Adds multi-field search filtering (diacritics, barcode, UPC, contributors) and dynamic native instance URL resolution for share links and public RSS feeds.
- `allegro-oauth`: Adds extraction and normalization of bibliographic parameters (`Autor`, `Wykonawca`, clean title, publisher, year) from Allegro product/offer parameter lists into FRBR metadata.

## Impact

- **Backend**: `app/utils/isbn.py`, `app/utils/allegro.py`, `app/api/manifestations.py`, `app/api/public_items.py`, `app/core/search_service.py`, `scripts/repair_frbr_authors.py`.
- **Frontend**: `frontend/lib/utils.ts`, `frontend/lib/capacitor/navigation.ts`, `frontend/components/collection/share-collection-dialog.tsx`, `frontend/components/ui/share-button.tsx`, `frontend/components/dashboard/fresh-arrivals.tsx`, `frontend/components/ui/public-feed-button.tsx`, `frontend/app/share/[token]/page.tsx`.
- **Dependencies & External Services**: Connects to `https://data.bn.org.pl` (open public API, no key required). No new external packages required.
