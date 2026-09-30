## 1. Scanner API Refactoring

- [x] 1.1 Update `lookup_barcode_preview` in `app/api/scanner.py` to discard DB cache hit if title is "Unknown Title" and author is None.
- [x] 1.2 Verify external metadata provider strategy fallthrough returns rich metadata payload linked to existing manifestation ID.

## 2. Quality Assurance & Testing

- [x] 2.1 Write regression unit test `test_lookup_barcode_discards_legacy_broken_db_record` in `tests/test_api_scanner.py`.
- [x] 2.2 Execute backend test suite to verify 100% pass rate.
