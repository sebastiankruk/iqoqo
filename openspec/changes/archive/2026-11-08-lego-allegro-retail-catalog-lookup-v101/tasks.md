# Tasks: LEGO Allegro Retail Catalog & Barcode Lookup Fallback

- [x] 1. Enhance Allegro parameter extraction for LEGO sets in `app/utils/allegro.py` (`Numer produktu`, `Liczba elementów`, `Seria`) <!-- id: 1 -->
- [x] 2. Update `LegoLookupStrategy` in `app/strategies/lego.py` with Allegro barcode lookup fallback and secondary Rebrickable enrichment <!-- id: 2 -->
- [x] 3. Update `LegoLookupStrategy.lookup_candidates` and `app/api/scanner.py` candidate aggregation for LEGO searches <!-- id: 3 -->
- [x] 4. Add unit and integration tests in `tests/test_lego_allegro.py` and `tests/test_rebrickable_strategy.py` <!-- id: 4 -->
- [x] 5. Run test suite and secret scan locally (`make lint`, `make test-parallel`) <!-- id: 5 -->
