## Context

The scanner API in `app/api/scanner.py` records telemetry for every scan operation. Two behavioral issues were flagged: (1) oversized barcodes were silently dropped (now fixed — `rejected_oversized` status at line 77); (2) `ScanBarcodeSchema.policy` may leak mutations into `UserWorkIntent` records instead of strictly targeting `Item.collection_status`. The policy/intent separation is a critical FRBR boundary — wishlists (intent) and physical inventory (items) must never contaminate each other.

## Goals / Non-Goals

**Goals:**

- Verify `_record_scan_telemetry()` correctly records `rejected_oversized` status for oversized barcodes
- Audit `ScanBarcodeSchema.policy` handling to ensure mutations target only `Item.collection_status`
- Add pytest tests proving both behavioral contracts hold
- Document the FRBR boundary between `Item` (F5) and `UserWorkIntent` in test docstrings

**Non-Goals:**

- Refactoring scanner ingestion pipeline
- Adding new scan telemetry fields
- Modifying barcode validation rules

## Decisions

### Decision 1: Policy mutation audit scope
**Choice:** Trace all code paths from `ScanBarcodeSchema.policy` through the scan endpoint to database writes, verifying only `Item.collection_status` is mutated.
**Rationale:** A comprehensive audit prevents future regressions better than point fixes.

### Decision 2: Test with realistic barcode data
**Choice:** Use real-world barcode patterns (EAN-13, UPC-A, oversized strings) in test fixtures.
**Rationale:** Realistic test data catches encoding edge cases that synthetic data misses.

## Risks / Trade-offs

- **Risk:** Policy/intent boundary violation may be deeply embedded in conditional logic → **Mitigation:** Use CodeGraph to trace all callers of `collection_status` mutation paths
- **Risk:** Changing telemetry status vocabulary breaks downstream analytics → **Mitigation:** `rejected_oversized` is already in production; no vocabulary change needed
