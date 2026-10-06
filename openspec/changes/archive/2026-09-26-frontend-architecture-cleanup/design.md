## Context

See `proposal.md` for problem motivation and scope.

The frontend application currently relies on Next.js 15, React 19, TanStack Query v5, Tailwind CSS, and shadcn/ui. Over iterations v0.1–v0.7.18, several critical and moderate architectural issues accumulated:
- `frontend/lib/api/hooks.ts` grew into a monolithic "god file" (>1,490 lines) combining catalog, collection, roadmap, intents, stats, and admin logic.
- Intent deletion via `deleteWorkIntent` erroneously checks `!res.data.success || res.data.data === null`, throwing unhandled runtime exceptions when the server responds with `{ success: true, data: { status: null } }`.
- Native browser dialogs (`window.confirm`) remain in collection management instead of design-system accessible modals.
- Administrative mutation actions in group management and RBAC fail silently or write solely to `console.error` without user feedback.
- Query client `staleTime` is set too aggressively (10s) for slow-changing FRBR metadata, causing unnecessary re-fetches, while cover processing uses unmanaged `setInterval` timers.
- Direct evaluation of `window.location.host` during server rendering triggers React hydration mismatch errors in admin settings.
- Security-relevant client configurations (cookie security, RUM telemetry privacy masking, API URL allowlists) require baseline hardening.

## Goals / Non-Goals

**Goals:**
- Decompose `hooks.ts` into clean, domain-scoped hook modules while maintaining seamless backward compatibility through barrel re-exports.
- Correct `deleteWorkIntent` API response validation to reliably handle null/empty success payloads.
- Standardize confirmation interactions with accessible shadcn `AlertDialog` and `Dialog` components.
- Integrate Sonner toast notifications into admin component error and success handlers.
- Tune TanStack Query cache configuration (`staleTime: 60_000` for FRBR metadata, `refetchInterval` for cover status polling).
- Fix SSR/client hydration discrepancies in admin settings.
- Resolve all 17 `MOD-FE_ARCH` findings and target `MOD-FE_UI` items from the v0.7.18 review.

**Non-Goals:**
- Decomposing the monolithic `frbr-editor.tsx` (reserved for C8 in v0.8.1).
- Overhauling Contributor UX form rows (reserved for C9 in v0.8.1).
- Separating the Wishlist API into a distinct backend endpoint (reserved for C10 in v0.8.1).
- Upgrading major dependencies (React, Next.js, TanStack Query).

## Decisions

### 1. Modularize `hooks.ts` into Domain Modules with Barrel Re-Export
- **Choice**: Decompose `frontend/lib/api/hooks.ts` into discrete domain files in `frontend/lib/api/hooks/`:
  - `catalog.ts`: Queries and mutations for Works, Expressions, Manifestations, Items, and Catalog shelf.
  - `collections.ts`: User collections, collection items, and item status mutations.
  - `intents.ts`: Work reading/wish intent queries and mutations (`useWorkIntent`, `useSetWorkIntent`).
  - `roadmap.ts`: Roadmap items, milestones, and item status progression.
  - `user.ts`: User profile queries, preferences, and authentication status.
  - `admin.ts`: Administrative queries, task monitors, and system operations.
  - `stats.ts`: System-wide statistics and collection count summaries.
  Retain `frontend/lib/api/hooks.ts` as a barrel file re-exporting all domain hooks and types.
- **Rationale**: Reduces file complexity, isolates concerns, enables parallel frontend feature development, and preserves 100% backward compatibility for existing component imports across the codebase.
- **Alternatives Considered**: In-place replacement of import paths across all 70+ consuming components without a barrel file. Rejected due to high risk of merge conflicts and excessive git churn.

### 2. Intent Deletion API Contract Alignment
- **Choice**: In `frontend/lib/api/intents.ts`, update `deleteWorkIntent`:
  ```ts
  export async function deleteWorkIntent(workId: number): Promise<null> {
    const res = await apiClient.delete<ApiResponse<{ status: null }>>(`/works/${workId}/intent`);
    if (!res.data.success) {
      throw new Error(res.data.error ?? "Failed to delete work intent");
    }
    return null;
  }
  ```
- **Rationale**: The backend returns `{ success: true, data: { status: null } }`. The previous check `res.data.data === null` caused valid responses to throw a "Failed to delete work intent" error. Checking only `!res.data.success` honors the API contract.
- **Alternatives Considered**: Modifying the backend to return `{ success: true, data: { status: "deleted" } }`. Rejected because returning `status: null` accurately reflects that no intent exists for the work.

### 3. Accessible Dialogs via shadcn `AlertDialog` and `Dialog`
- **Choice**:
  - In `frontend/components/collection/manage-collections-modal.tsx`: Replace native `window.confirm("Are you sure you want to delete this collection?")` with a controlled shadcn `AlertDialog` workflow.
  - In `frontend/components/admin/group-management.tsx`: Replace ad-hoc fixed overlay divs with shadcn `Dialog`.
- **Rationale**: Native `window.confirm` blocks browser execution threads, is inaccessible to screen readers, fails mobile responsive design, and cannot be styled to match theme tokens.
- **Alternatives Considered**: Retaining `window.confirm` for administrative simplicity. Rejected per project accessibility and UI consistency standards (`MOD-FE_UI-07`).

### 4. Admin Action Feedback with Sonner Toasts
- **Choice**: Import `toast` from `sonner` in `group-management.tsx` and `rbac-sheet.tsx`. Replace raw `console.error` calls with descriptive `toast.error(message)` invocations and add `toast.success(message)` upon completed role/permission updates.
- **Rationale**: Administrators previously received no user feedback when operations failed or succeeded, leading to confusion and repeated clicks (`MOD-FE_UI-22`, `MOD-FE_UI-24`).
- **Alternatives Considered**: Adding inline alert banners inside tables. Rejected because transient toast notifications communicate state changes without causing table layout shifts.

### 5. Query Cache Lifetimes and Declarative Polling
- **Choice**:
  - In `frontend/components/providers.tsx`: Configure QueryClient default `staleTime: 60_000` (60 seconds) for general queries.
  - In `frontend/lib/api/escalations.ts`: Increase `staleTime` from 10s to 30s (`MOD-FE_ARCH-04`).
  - In `frontend/components/manifestation/manifestation-actions.tsx`: Replace manual `setInterval` polling with TanStack Query's declarative `refetchInterval` function that polls every 3,000ms only while `cover_status === 'processing'`.
- **Rationale**: FRBR catalog metadata changes infrequently during a user session; a 60s cache prevents redundant background refetches. Declarative polling prevents memory leaks and uncancelled intervals when components unmount.
- **Alternatives Considered**: Setting `staleTime: Infinity`. Rejected because concurrent updates from background sync or other tabs would not reflect without manual reload.

### 6. Settings Page Hydration Mismatch Remediation
- **Choice**: In `frontend/app/admin/settings/page.tsx`, avoid direct server-side execution of `window.location.host`. Use an environment fallback (`process.env.NEXT_PUBLIC_API_URL` or standard placeholder) or access `window` inside a `useEffect` / `mounted` state guard.
- **Rationale**: React 19 throws hydration mismatch warnings when initial server HTML diverges from browser-rendered DOM, degrading performance and causing UI flicker (`MOD-FE_UI-36`).
- **Alternatives Considered**: Using `suppressHydrationWarning`. Rejected because suppressing the warning leaves the layout shift unaddressed and masks future hydration defects.

### 7. Comprehensive MOD-FE_ARCH Hardening Sweep
- **Structured error handling (`MOD-FE_ARCH-01`)**: Inspect `axios.isAxiosError(err)` and HTTP status codes (e.g. 401, 404) in `useProfile` rather than fragile error string pattern matching.
- **Page size constant (`MOD-FE_ARCH-03`)**: Export `DEFAULT_INFINITE_PAGE_SIZE = 20` from `infinite-hooks.ts`.
- **Type-safe FRBR entity updates (`MOD-FE_ARCH-06`)**: Provide overloaded or discriminated function signatures for `updateFrbrEntity` in `admin.ts` to replace `data as any`.
- **Manifestation metadata types (`MOD-FE_ARCH-07`)**: Add typed media strategy metadata properties to `Manifestation.meta` in `frontend/types/frbr.ts`.
- **URL allowlist validation (`MOD-FE_ARCH-08`)**: Validate URL protocols (`http:`, `https:`) and authorized hosts in `resolveApiUrl` before returning URLs.
- **NaN guard in timestamp util (`MOD-FE_ARCH-09`)**: Return an empty string or fallback timestamp if `new Date(val).getTime()` is `NaN` in `frontend/lib/utils.ts`.
- **Expression escalation href (`MOD-FE_ARCH-10`)**: Map Expression target hrefs to parent Work pages with expression anchor tags (`/work/${workId}#expression-${id}`) in `escalation-utils.tsx`.
- **DevTools console patch isolation (`MOD-FE_ARCH-12`)**: Move the JSON-LD `console.error` filter out of `theme-provider.tsx` into a separate development utility.
- **Secure locale cookie (`MOD-FE_ARCH-13`)**: Append `; Secure; SameSite=Lax` to `NEXT_LOCALE` cookie updates in `language-toggle.tsx`.
- **Dynamic translation mock (`MOD-FE_ARCH-14`)**: Load `frontend/messages/en.json` in `vitest.setup.ts` instead of maintaining an out-of-sync hardcoded mock dictionary.
- **Unmasked Axios mock (`MOD-FE_ARCH-15`)**: Provide test utilities to mock Axios rejection without letting default mocks mask 4xx/5xx status codes in `vitest.setup.ts`.
- **Secure RUM defaults (`MOD-FE_ARCH-16`, `MOD-FE_ARCH-17`)**: Default `insecureHTTP: false` and set `defaultPrivacyLevel: "mask-user-input"` in `browser-openobserve-rum.tsx`.

## Risks / Trade-offs

- **[Risk] Circular dependency between barrel `hooks.ts` and domain hook modules** → Mitigation: Domain modules in `frontend/lib/api/hooks/` import directly from `client.ts` or sibling domain files, never from the barrel `hooks.ts`.
- **[Risk] Increased staleTime hides immediate catalog updates** → Mitigation: Keep cache mutation invalidation rules intact; all mutations (`useCreateWork`, `useUpdateItem`, etc.) immediately invalidate affected query keys regardless of `staleTime`.
- **[Risk] Vitest suite regressions due to dynamic i18n mock changes** → Mitigation: Validate test suites across all frontend modules using `npm test` before finalizing implementation.
