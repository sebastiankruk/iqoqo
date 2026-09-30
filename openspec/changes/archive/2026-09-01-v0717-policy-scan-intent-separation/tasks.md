## 1. Scanner API Updates

- [x] 1.1 Update `app/api/scanner.py` to intercept `policy == "catalog_only"` (or both `"catalog"` and `"catalog_only"`) and return the Manifestation ID with a `"cataloged"` action, explicitly bypassing `_scan_to_wishlist` and `_scan_to_library`. Verify by running the existing unit tests for the scanner.
- [x] 1.2 Add a new Pytest in the scanner tests directory to test that a scan with `policy="catalog_only"` results in a Manifestation but DOES NOT insert rows into `inventory.items` or `inventory.user_work_intents`. Verify by running the new test.
- [x] 1.3 Add or verify a Pytest ensuring that regular scanning (without a policy, or `policy="inventory"`) still correctly inserts Items. Verify by running the test and ensuring `Item` rows exist.
- [x] 1.4 Add or verify a Pytest ensuring that `policy="wishlist"` correctly inserts `UserWorkIntent` rows. Verify by running the test.

## 2. Integrity Assurance

- [x] 2.1 Audit `app/core/frbr_service.py` to ensure methods called during the `catalog_only` flow (like `IngestService.ingest_from_meta`) do not inadvertently auto-create Items under the hood. Verify by running full test suite to check for unintended side-effects.
