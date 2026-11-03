# Proposal: Mobile Share URLs, Biblioteka Narodowa Fallback, and Allegro Author Extraction

## Why

Native mobile app sharing links and RSS feeds resolved to `localhost` causing runtime crashes, search filtering on shared collections failed to match normalized titles or identifiers, scanning Polish ISBNs failed when Google Books exceeded IP quotas, and items ingested via Allegro exhibited "Undefined" authors due to ignored parameter payloads. Addressing these gaps ensures robust mobile sharing, zero-configuration Polish book cataloging, and complete FRBR authorship integrity across the catalog.

## What Changes

- **Mobile Public URL Resolution & RSS External Browser Routing**: Replaced hardcoded `window.location.origin` fallbacks with dynamic `resolvePublicUrl(path)` against the active instance URL (`getSyncInstanceUrl()`) on native mobile environments, and routed RSS feeds (`/api/public/feed.xml`) and external share links through `@capacitor/browser` to prevent WebView crashes.
- **Shared Collection Comprehensive Search Clause**: Extended shared collection and intent search filter queries to match diacritic-normalized titles, authors, manifestations' barcodes, UPCs, and catalog numbers.
- **National Library of Poland (Biblioteka Narodowa) ISBN Provider**: Added `_lookup_biblioteka_narodowa_outcome` leveraging `https://data.bn.org.pl` as a free, open, keyless upstream fallback for Polish ISBNs (`978-83-...`), raised lookup ceiling from 3.0s to 6.0s, and loaded Google Books API key from encrypted `InstanceSettings` (`ConfigService`).
- **Allegro Parameter Extraction & FRBR Author Repair**: Extracted bibliographic parameters (`Autor`, `Autorzy`, `Wykonawca`, `Twórca`, `Reżyser`, clean `Tytuł`, `Wydawnictwo`, `Rok wydania`) from Allegro catalog payloads, added manifestation display author fallbacks in API serializers, and enhanced `scripts/repair_frbr_authors.py` to backfill missing authors across existing database records.

## Capabilities

### Modified Capabilities

- `book-provider-fallback-retry`: Extends fallback chain with Biblioteka Narodowa open API for Polish ISBNs, reads Google Books API keys from `ConfigService`, and extends lookup duration ceiling to 6.0 seconds.
- `shared-collection-ui`: Adds multi-field search filtering (diacritics, barcode, UPC, contributors) and dynamic native instance URL resolution for share links and public RSS feeds.
- `allegro-oauth`: Adds extraction and normalization of bibliographic parameters (`Autor`, `Wykonawca`, clean title, publisher, year) from Allegro product/offer parameter lists into FRBR metadata.

## Impact

- **Backend**: `app/utils/isbn.py`, `app/utils/allegro.py`, `app/api/manifestations.py`, `app/api/public_items.py`, `app/core/search_service.py`, `scripts/repair_frbr_authors.py`.
- **Frontend**: `frontend/lib/utils.ts`, `frontend/lib/capacitor/navigation.ts`, `frontend/components/collection/share-collection-dialog.tsx`, `frontend/components/ui/share-button.tsx`, `frontend/components/dashboard/fresh-arrivals.tsx`, `frontend/components/ui/public-feed-button.tsx`, `frontend/app/share/[token]/page.tsx`.
- **Dependencies & External Services**: Connects to `https://data.bn.org.pl` (open public API, no key required). No new external packages required.
