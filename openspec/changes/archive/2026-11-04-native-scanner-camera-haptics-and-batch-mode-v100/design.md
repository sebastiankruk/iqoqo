## Context

From `1.0.0-ux-audit-report.md` and `origin/feat/1.0.0/mobile-capacitor`, two major scanner UX gaps were identified for mobile collectors: (1) scanning a shelf of 50 books required redirecting to `/item/[id]` and navigating back to `/scan` after every single barcode, and (2) manual lookup required 4 clicks due to a mandatory tab switch.

## Goals / Non-Goals

**Goals:**
- Deliver `BatchScanToggle` (`useBatchMode`) with native `@capacitor/haptics` tactile feedback (`isNativeApp()` guarded) so collectors can scan an entire shelf continuously.
- Reduce manual lookup/addition on `/scan` to $\le 3$ clicks by exposing a unified quick-lookup input on the main scanner screen.
- Configure native iOS (`Info.plist`) and Android (`AndroidManifest.xml`) camera permissions cleanly.

**Non-Goals:**
- YOLO "Magic Shelf" multi-spine computer vision (scheduled for `v1++`).

## Decisions

### Guarded Haptics & Continuous Batch Scan Loop
* **Decision:** Wrap all `@capacitor/haptics` calls in `if (isNativeApp())` checks inside `batch-scan-toggle.tsx` and `scan/page.tsx` so web browsers never throw plugin errors, and reset the scanner state immediately after toast confirmation when `batchMode` is active.
* **Rationale:** Eliminates redirect friction during bulk shelf ingestion while keeping Web and Capacitor code paths unified.

## Risks / Trade-offs

- **Risk:** Duplicate rapid scans of the same barcode while holding the phone steady in Batch Mode.
  - **Mitigation:** Debounce identical consecutive barcode reads within a 3-second cooldown window in `useBatchMode`.
