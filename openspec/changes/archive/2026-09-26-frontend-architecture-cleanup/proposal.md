## Why

The frontend architecture accumulated significant technical debt across state management, API client bindings, and UI consistency, including a 1,500-line monolithic hooks file, silent failure paths, fragile intent mutation logic, native browser dialogs, and hydration mismatches. Addressing these issues in v0.8.1 (C13) stabilizes the client runtime, strengthens type safety, eliminates unhandled mutation rejections, and improves developer velocity ahead of federation.

## What Changes

- **Hooks God File Decomposition (`MOD-FE_ARCH-02`)**: Modularize `frontend/lib/api/hooks.ts` (~1,500 lines) into focused domain modules (`catalog`, `collection`, `stats`, `roadmap`, `user`, `intents`, `admin`, `system`) while maintaining backward-compatible re-exports.
- **Intent Deletion Fix (`MOD-FE_ARCH-05`)**: Correct the `deleteWorkIntent` API client method in `frontend/lib/api/intents.ts` so successful `{ success: true, data: { status: null } }` responses do not throw errors.
- **Accessible Dialogs (`MOD-FE_UI-07`, `MOD-FE_UI-23`)**: Replace native `window.confirm()` in `manage-collections-modal.tsx` with accessible shadcn `AlertDialog`, and replace custom ad-hoc modal overlays in `group-management.tsx` with shadcn `Dialog`.
- **Admin Toast Notifications (`MOD-FE_UI-22`, `MOD-FE_UI-24`)**: Add accessible Sonner toast feedback for error and success events in `group-management.tsx` and `rbac-sheet.tsx` instead of silent `console.error` logs.
- **Query Cache Tuning & Staleness (`MOD-FE_ARCH-04`, `MOD-FE_ARCH-11`)**: Increase default `staleTime` for FRBR metadata from 10s to 60s in `providers.tsx` (overriding to 0 for volatile mutations), and extend escalation poll intervals from 10s to 30–60s in `escalations.ts`.
- **Settings Hydration Fix (`MOD-FE_UI-36`)**: Eliminate server/client HTML hydration mismatches in `admin/settings/page.tsx` by using server-safe environment variables or mounted checks rather than client-only `window.location.host`.
- **Declarative Polling (`CRIT-FE_ARCH-09`)**: Replace manual `setInterval` polling loops with declarative TanStack Query `refetchInterval` in `manifestation-actions.tsx`.
- **Structured Error Handling (`MOD-FE_ARCH-01`)**: Replace fragile substring error matching in `useProfile` with typed HTTP status code inspection and structured error models.
- **Pagination Constants (`MOD-FE_ARCH-03`)**: Extract hardcoded page size literals in `infinite-hooks.ts` into shared, exported constants.
- **Type Safety & Entity Mutations (`MOD-FE_ARCH-06`, `MOD-FE_ARCH-07`)**: Remove unsafe `any` casts in `updateFrbrEntity` in `admin.ts` using discriminated entity signatures, and refine `Manifestation.meta` typing with media strategy discrimination in `frontend/types/frbr.ts`.
- **URL & Utility Hardening (`MOD-FE_ARCH-08`, `MOD-FE_ARCH-09`, `MOD-FE_ARCH-10`)**: Add hostname allowlist validation to `resolveApiUrl`, add `NaN` guards to `getCoverTimestamp` in `frontend/lib/utils.ts`, and add Expression-to-Work fallback resolution in `escalation-utils.tsx`.
- **DevTools & Telemetry Hardening (`MOD-FE_ARCH-12`, `MOD-FE_ARCH-16`, `MOD-FE_ARCH-17`)**: Isolate console monkey-patching out of `theme-provider.tsx` into a dedicated development-only component, invert `insecureHTTP` default to `false` (secure), and configure production RUM privacy masking (`mask-user-input`) in `browser-openobserve-rum.tsx`.
- **Cookie Security (`MOD-FE_ARCH-13`)**: Append `; Secure` attribute to `NEXT_LOCALE` cookie updates in `language-toggle.tsx`.
- **Test Suite Modernization (`MOD-FE_ARCH-14`, `MOD-FE_ARCH-15`)**: Replace the 340-line hardcoded i18n mock in `vitest.setup.ts` with dynamic `messages/en.json` imports, and configure the Axios mock to support test-specific error status overrides without hiding failures.

## Capabilities

### New Capabilities
- `frontend/architecture-v081`: Architectural cleanup of frontend state management, modularized domain hooks, robust intent mutations, accessible modal dialogs, hydration consistency, telemetry privacy, and query cache optimization.

### Modified Capabilities

## Impact

- **Frontend Core**: `frontend/lib/api/hooks.ts` split into domain files under `frontend/lib/api/hooks/`; imports preserved via barrel re-exports.
- **API Clients & Utils**: `frontend/lib/api/intents.ts`, `frontend/lib/api/admin.ts`, `frontend/lib/utils.ts`, and `frontend/lib/escalation-utils.tsx`.
- **Components & Modals**: `manage-collections-modal.tsx`, `group-management.tsx`, `rbac-sheet.tsx`, `manifestation-actions.tsx`, `theme-provider.tsx`, `language-toggle.tsx`, and `browser-openobserve-rum.tsx`.
- **Pages**: `frontend/app/admin/settings/page.tsx`.
- **Testing & Tooling**: `frontend/vitest.setup.ts` dynamic i18n mocking and unmasked Axios mock behavior.
