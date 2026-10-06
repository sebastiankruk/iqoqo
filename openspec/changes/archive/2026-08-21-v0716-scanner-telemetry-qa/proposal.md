## Why

Scanner API telemetry records silently drop oversized barcode submissions and the `ScanBarcodeSchema.policy` field may inadvertently mutate `UserWorkIntent` records instead of strictly targeting `Item.collection_status`. Both issues undermine auditing integrity and violate the FRBR ontological boundary between user intent (wishlist) and physical inventory (owned items).

## What Changes

- **Audit** `_record_scan_telemetry()` in `app/api/scanner.py` to confirm oversized barcodes are recorded with `status='rejected_oversized'` rather than silently returned (code inspection shows this is already implemented at line 77)
- **Enforce** that `ScanBarcodeSchema.policy` mutations strictly target `Item.collection_status` and never touch `UserWorkIntent` setup guides
- **Add comprehensive tests** for both behavioral contracts — oversized barcode rejection recording and policy/intent separation

## Capabilities

### New Capabilities

- `scanner-policy-intent-separation`: Enforcement and test suite ensuring scan policy mutations respect the FRBR Item vs UserWorkIntent boundary

### Modified Capabilities

- `telemetry-sanitization`: Adding auditable rejection recording for oversized barcodes with test coverage

## Impact

- **Files:** `app/api/scanner.py`
- **Tests:** New pytest tests in `tests/test_scanner_telemetry.py`
- **Risk:** Medium — policy/intent separation touches core scanner logic
- **FRBR Constraint:** Policy mutations must target `Item` (F5 level), never `UserWorkIntent` (user preference layer)
