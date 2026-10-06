## 1. Audit Telemetry Recording

- [x] 1.1 Verify `_record_scan_telemetry()` in `app/api/scanner.py` records `status='rejected_oversized'` for barcodes > 128 chars (line 77)
- [x] 1.2 Verify barcode truncation to 120 chars with `...(<length>)` suffix format
- [x] 1.3 Confirm warning log is emitted for oversized barcodes

## 2. Audit Policy/Intent Separation

- [x] 2.1 Trace all code paths from `ScanBarcodeSchema.policy` field through scan endpoints
- [x] 2.2 Verify `policy` mutations only touch `Item.collection_status` column
- [x] 2.3 Verify no code path creates/modifies `UserWorkIntent` records from policy field
- [x] 2.4 Use CodeGraph to map all callers of `collection_status` mutation in scan workflows

## 3. Write Test Suite

- [x] 3.1 Create pytest test: oversized barcode (>128 chars) → `rejected_oversized` telemetry recorded
- [x] 3.2 Create pytest test: normal barcode (≤128 chars) → original status preserved
- [x] 3.3 Create pytest test: scan with policy="owned" → only `Item.collection_status` mutated
- [x] 3.4 Create pytest test: scan with policy → no `UserWorkIntent` records created/modified
- [x] 3.5 Create pytest test: scan with invalid policy → 400 error, no DB mutations

## 4. Verification

- [x] 4.1 Run `make format-python`
- [x] 4.2 Run `make lint-python` — verify no errors
- [x] 4.3 Run `make test-backend` — verify all tests pass
