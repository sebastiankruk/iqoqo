## Why

Users have reported ambiguity during the barcode scanning process, unsure if the app is processing data. We need to introduce prominent visual waiting indicators and robust error fallbacks to improve the ingestion UX.

## What Changes

- Integrate a prominent, high-visibility visual waiting indicator (e.g., animated overlay) triggered immediately upon image capture while awaiting asynchronous API lookup payloads.
- Enforce graceful error fallback: network timeouts or unrecognized captures must cleanly dismiss the loading indicator and revert to the manual EAN/barcode entry form.
- Pass captured metadata directly into the fallback manual entry form.

## Capabilities

### New Capabilities

- `scanner-visual-waiting`: High-visibility animated overlay during asynchronous scanner API lookups.
- `scanner-error-fallback`: Graceful fallback mechanism to manual entry form with pre-filled metadata upon lookup failures.

### Modified Capabilities

## Impact

- **Frontend**: `frontend/components/scanner/camera-capture.tsx`, `frontend/components/scanner/error-boundary.tsx`, `frontend/components/scanner/manual-entry-form.tsx`.
- **Testing**: Playwright regression tests in `frontend/__tests__/e2e/scanner_workflow.spec.ts` simulating delayed and failed API responses.
