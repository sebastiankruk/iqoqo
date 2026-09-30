## 1. Providers Refactoring

- [x] 1.1 Refactor `app/utils/allegro.py` to accept `max_results=10` and remove `limit=1` truncation, verify by checking the return lists.
- [x] 1.2 Refactor `app/utils/isbn.py` to accept `max_results=10` and remove early `break`, verify by checking the return lists.
- [x] 1.3 Refactor `app/strategies/book.py` title lookup to aggregate up to `max_results` candidates instead of returning just one, verify by testing the strategy.

## 2. API Update

- [x] 2.1 Update `app/api/scanner.py` to return the multi-candidate response when confidence is split on title search, verify by checking the endpoint response schema.

## 3. End-to-End Verification

- [x] 3.1 Write and run Pytest `tests/test_scanner_lookup.py` to assert title lookups for ambiguous titles return >= 3 candidates without truncation.
