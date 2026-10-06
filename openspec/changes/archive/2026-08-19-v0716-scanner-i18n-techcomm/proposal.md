## Why

Scanner components `camera-capture.tsx` and `bottom-sheet.tsx` contain hardcoded English UI strings that bypass the `next-intl` internationalization system. This blocks Polish (and future) localization of the scanner workflow — one of the most frequently used user-facing flows in iqoqo.

## What Changes

- **Extract** all hardcoded English strings from `frontend/components/scanner/camera-capture.tsx` into `next-intl` translation keys
- **Extract** all hardcoded English strings from `frontend/components/scanner/bottom-sheet.tsx` into `next-intl` translation keys
- **Add** corresponding translation entries to `frontend/messages/en.json` and `frontend/messages/pl.json`
- **Ensure** Polish translations follow sentence case convention per project rules (not Title Case)

## Capabilities

### New Capabilities

- `scanner-i18n`: Internationalization of scanner camera capture and bottom sheet components

### Modified Capabilities

- None — existing i18n infrastructure used, no spec-level behavior changes

## Impact

- **Frontend Files:** `frontend/components/scanner/camera-capture.tsx`, `frontend/components/scanner/bottom-sheet.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`
- **Tests:** Vitest snapshot tests for translated scanner components
- **Risk:** Low — mechanical string extraction with no logic changes
- **i18n Constraint:** Polish strings must use sentence case (e.g., "Zeskanuj kod kreskowy", not "Zeskanuj Kod Kreskowy")
