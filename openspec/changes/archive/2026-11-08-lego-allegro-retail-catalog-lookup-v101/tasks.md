# Tasks: LEGO Allegro Retail Catalog & Barcode Lookup Fallback

- [x] 1. Enhance Allegro parameter extraction for LEGO sets in `app/utils/allegro.py` (`Numer produktu`, `Numer zestawu`, `Kod producenta`, `Liczba elementów`, `Liczba klocków`, `Seria`, `Linia`) <!-- id: 1 -->
- [x] 2. Update `LegoLookupStrategy` in `app/strategies/lego.py` with Allegro barcode lookup fallback (`format="standard_set"`, `category="lego"`) and secondary Rebrickable enrichment <!-- id: 2 -->
- [x] 3. Update `LegoLookupStrategy.lookup_candidates`, `app/api/scanner.py` (`_normalize_preview_meta` and candidate aggregation), and `frontend/app/scan/page.tsx` (`formatToApiParam("lego")`) <!-- id: 3 -->
- [x] 4. Add unit, API, and frontend tests in `tests/test_lego_allegro.py` and `frontend/__tests__/app/scan/page.test.tsx` <!-- id: 4 -->
- [x] 5. Run test suite and secret scan locally (`make lint`, `make test-parallel`) <!-- id: 5 -->
