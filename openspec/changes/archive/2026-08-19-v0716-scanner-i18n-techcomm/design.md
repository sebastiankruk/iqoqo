## Context

Scanner components `camera-capture.tsx` (16KB) and `bottom-sheet.tsx` (18KB) are the primary user-facing scanner workflow screens. They contain hardcoded English strings that bypass the established `next-intl` internationalization system, blocking Polish localization of the scanner flow.

## Goals / Non-Goals

**Goals:**

- Extract all user-visible English strings from both scanner components into `next-intl` translation keys
- Add English translations to `frontend/messages/en.json` under a `scanner` namespace
- Add Polish translations to `frontend/messages/pl.json` using sentence case convention
- Maintain existing component logic and behavior — zero functional changes
- Add Vitest tests verifying translation key rendering

**Non-Goals:**

- Refactoring scanner component architecture
- Adding new languages beyond English and Polish
- Translating non-user-visible strings (logs, error codes)

## Decisions

### Decision 1: `scanner` namespace in translation files
**Choice:** Group all scanner translations under `scanner.cameraCapture.*` and `scanner.bottomSheet.*` namespaces.
**Rationale:** Follows existing namespace conventions in the project (e.g., `dashboard.*`, `common.*`).

### Decision 2: `useTranslations` hook pattern
**Choice:** Use `useTranslations('scanner')` hook at component top level, then `t('cameraCapture.buttonLabel')` for individual strings.
**Rationale:** Matches existing i18n patterns in other iqoqo components.

## Risks / Trade-offs

- **Risk:** Missing translation keys cause runtime errors → **Mitigation:** `next-intl` falls back to key name; Vitest tests verify all keys exist
- **Risk:** Polish translations may need native speaker review → **Mitigation:** Use sentence case per project rules; flag for human review in PR
