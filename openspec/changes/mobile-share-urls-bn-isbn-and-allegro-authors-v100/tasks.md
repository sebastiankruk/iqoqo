## 1. Mobile URL Resolution & External Browser Delegation

- [x] 1.1 Implement `getPublicBaseUrl` and `resolvePublicUrl` in `frontend/lib/utils.ts` and verify unit tests in `frontend/__tests__/lib/utils.test.ts`
- [x] 1.2 Implement `openExternalUrl` using `@capacitor/browser` in `frontend/lib/capacitor/navigation.ts` and verify unit tests in `frontend/__tests__/lib/capacitor/navigation.test.ts`
- [x] 1.3 Update `ShareCollectionDialog`, `ShareButton`, and `FreshArrivals` to resolve URLs dynamically and intercept mobile clicks, verifying via Vitest component tests
- [x] 1.4 Create `PublicFeedButton` on `/share/[token]` pages and verify in `frontend/__tests__/components/ui/public-feed-button.test.tsx`

## 2. Shared Collection Search Normalization

- [x] 2.1 Update `build_ilike_search_clause` in `app/core/search_service.py` to index barcode, UPC, and catalog numbers
- [x] 2.2 Extend `fetch_shared_collection_by_token` in `app/api/public_items.py` with multi-field search and diacritic normalization
- [x] 2.3 Verify shared collection filtering via `tests/test_api_public_extended.py`

## 3. Upstream ISBN Providers & Biblioteka Narodowa Integration

- [x] 3.1 Load Google Books API key from `ConfigService.get("GOOGLE_BOOKS_API_KEY")` in `app/utils/isbn.py` to prevent 429 quota exhaustion
- [x] 3.2 Implement `_lookup_biblioteka_narodowa_outcome` in `app/utils/isbn.py` querying `https://data.bn.org.pl` for Polish ISBNs
- [x] 3.3 Expand `fetch_isbn_metadata` to include Biblioteka Narodowa fallback and gap filling with 6.0s timeout ceiling
- [x] 3.4 Verify BN JSON parsing and fallback behavior via `tests/test_isbn.py`

## 4. Allegro Parameter Extraction & FRBR Authors Repair

- [x] 4.1 Implement `_extract_allegro_parameters` in `app/utils/allegro.py` to extract `Autor`, `Wykonawca`, clean title, publisher, and year
- [x] 4.2 Add `_resolve_manifestation_display_author` fallback in `app/api/manifestations.py` to prevent "Undefined" authors
- [x] 4.3 Enhance `scripts/repair_frbr_authors.py` to backfill missing authors from attached manifestations' `raw_payload["parameters"]` and apply to database
- [x] 4.4 Add test coverage for parameter extraction in `tests/test_allegro.py` and FRBR author normalization in `tests/test_frbr_author_normalization.py`

## 5. Maintenance Automation, Docker Stacks & Shared Search Parity

- [x] 5.1 Implement admin one-click maintenance endpoint `POST /api/admin/maintenance/repair-authors` with dry run option in `app/api/admin.py` and verify via `tests/test_api_admin.py`
- [x] 5.2 Add Docker stack-aware `make repair-authors [preview|prod]` target in `Makefile` supporting auto-detection, `dry_run=1`, and explicit environment parameters
- [x] 5.3 Enforce strict non-localhost fallback in `getPublicBaseUrl` (`frontend/lib/utils.ts`), eager preference hydration on module load (`frontend/lib/capacitor/storage.ts`), and build-time URL injection in `frontend/scripts/build-capacitor.js`
- [x] 5.4 Connect `get_shared_collection` and `fetch_shared_collection_by_token` to `SearchService.search_items` on PostgreSQL, and narrow `build_ilike_search_clause` to specific metadata fields to prevent false positive matches against raw JSON descriptions and producer addresses
- [x] 5.5 Extract authors from linked FRBR Work metadata in shared collection item serializer when manifestation lacks inline authors
- [x] 5.6 Verify tests for negative description matching and author fallback in `tests/test_api_public_extended.py` and native fallback in `frontend/__tests__/lib/utils.test.ts`
