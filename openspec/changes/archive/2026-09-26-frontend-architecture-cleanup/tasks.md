## 1. Domain Hooks Decomposition

- [x] 1.1 Create `frontend/lib/api/hooks/` directory with domain modules (`catalog.ts`, `collections.ts`, `intents.ts`, `roadmap.ts`, `user.ts`, `admin.ts`, `stats.ts`) and split hooks from `hooks.ts` into their corresponding domain modules, verifying with `npm --prefix frontend run typecheck`
- [x] 1.2 Convert `frontend/lib/api/hooks.ts` into a backward-compatible barrel file that re-exports all domain hooks, interfaces, and query key helpers, verifying that existing component imports resolve without TypeScript errors via `npm --prefix frontend run typecheck`

## 2. Intent Handling & Error Resilience

- [x] 2.1 Fix `deleteWorkIntent` in `frontend/lib/api/intents.ts` to check only `!res.data.success` instead of rejecting when `res.data.data === null`, verifying with unit tests in `frontend/__tests__/lib/api/intents.test.ts`
- [x] 2.2 Refactor `useProfile` in `frontend/lib/api/hooks/user.ts` to replace fragile string matching on error messages with structured HTTP status checks (`axios.isAxiosError(err)` and status code 401/404), verifying error state handling with unit tests

## 3. Accessible Dialogs & Modals

- [x] 3.1 Replace native `window.confirm()` in `frontend/components/collection/manage-collections-modal.tsx` with shadcn `AlertDialog` component, verifying keyboard interaction, cancelation, and deletion execution in component tests
- [x] 3.2 Replace custom absolute/fixed modal overlay in `frontend/components/admin/group-management.tsx` with shadcn `Dialog`, verifying modal open/close accessibility and form submission via component test

## 4. Admin Component Toast Notifications

- [x] 4.1 Integrate Sonner `toast.error` and `toast.success` notifications into `frontend/components/admin/group-management.tsx` for permission saving, role creation, and role deletion, verifying notification triggers with unit tests
- [x] 4.2 Integrate Sonner `toast.error` and `toast.success` notifications into `frontend/components/admin/rbac-sheet.tsx` for role assignment and revocation, verifying notification triggers with unit tests

## 5. Query Cache Tuning & Polling Refactoring

- [x] 5.1 Update `frontend/components/providers.tsx` QueryClient default configuration to set `staleTime: 60_000` (60s) for metadata queries while preserving zero-stale overrides for volatile queries, verifying default query options with unit tests
- [x] 5.2 Increase escalation query `staleTime` from 10s to 30s in `frontend/lib/api/escalations.ts`, verifying query options with unit tests
- [x] 5.3 Replace manual `setInterval` polling in `frontend/components/manifestation/manifestation-actions.tsx` with TanStack Query's declarative `refetchInterval` condition (`cover_status === 'processing'`), verifying automated polling start and stop behavior with component tests

## 6. Hydration Mismatch & UI Hardening

- [x] 6.1 Fix hydration mismatch in `frontend/app/admin/settings/page.tsx` by replacing direct `window.location.host` render references with mounted state checks or environment fallback, verifying SSR output matches client DOM without console warnings
- [x] 6.2 Extract hardcoded page size literals in `frontend/lib/api/infinite-hooks.ts` into exported `DEFAULT_INFINITE_PAGE_SIZE = 20`, verifying hook query params with unit tests
- [x] 6.3 Replace unsafe `(data as any)` type casts in `updateFrbrEntity` in `frontend/lib/api/admin.ts` with discriminated entity payload signatures, verifying type safety with `npm --prefix frontend run typecheck`
- [x] 6.4 Refine `Manifestation.meta` interface in `frontend/types/frbr.ts` to include typed media strategy fields, verifying TypeScript compilation with `npm --prefix frontend run typecheck`
- [x] 6.5 Update `getTargetHref` and `getAdminTargetHref` in `frontend/lib/escalation-utils.tsx` to route Expression escalation items to their parent Work URL with fragment anchor, verifying escalation link paths with unit tests

## 7. Security, Utilities & Telemetry Hardening

- [x] 7.1 Add allowed host validation and protocol guards to `resolveApiUrl` in `frontend/lib/utils.ts`, verifying host filtering with unit tests
- [x] 7.2 Add `isNaN` guard to `getCoverTimestamp` in `frontend/lib/utils.ts` to return empty string on invalid dates, verifying timestamp parsing with unit tests
- [x] 7.3 Extract JSON-LD console error filter from `frontend/components/theme-provider.tsx` into a dedicated development-only utility, verifying clean theme provider rendering
- [x] 7.4 Append `; Secure; SameSite=Lax` to `NEXT_LOCALE` cookie updates in `frontend/components/language-toggle.tsx`, verifying cookie attributes with unit tests
- [x] 7.5 Update `frontend/components/browser-openobserve-rum.tsx` to set default `insecureHTTP: false` and set `defaultPrivacyLevel: "mask-user-input"`, verifying initialized configuration with unit tests

## 8. Frontend Test Suite Modernization

- [x] 8.1 Replace hardcoded 340-line translation dictionary in `frontend/vitest.setup.ts` with dynamic import of `frontend/messages/en.json`, verifying localized component tests execute properly
- [x] 8.2 Refactor Axios mock in `frontend/vitest.setup.ts` to expose customizable mock handlers for error status codes without global success masking, verifying error test assertions
- [x] 8.3 Execute full frontend lint, typecheck, and test suite via `IQOQO_AI_MODE=1 make lint` and `npm --prefix frontend test` to verify zero regressions across the codebase
