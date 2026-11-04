## Context

`C95`–`C100c` established Next.js conditional static export (`CAPACITOR_BUILD=true`) with `_placeholder` dynamic route shells across Android and iOS. While FRBR entity pages (`/item/[id]`, `/manifestation/[id]`, `/work/[id]`, `/expression/[id]`) and `/help/[slug]` were wired to client components via `useResolvedRouteParam()`, `/share/[token]` and `/u/[username]` remained pure Server Components that rendered an empty `<Navbar />` shell when exported as `_placeholder.html`. In addition, native WebView edge cases around `EventSource`, `AdminLayout`, `SuccessCard` cover URLs, batch-scanner concurrency, staging URL fallbacks, and native manifest metadata need cleanup prior to tagging `v1.0.0`.

## Goals / Non-Goals

**Goals:**
- Render full interactive `/share/[token]` and `/u/[username]` views inside Android and iOS Capacitor apps while preserving 100% SSR HTML + Schema.org JSON-LD for web crawlers.
- Keep Android `MainActivity.java` and iOS `AppDelegate.swift` routing behavior in strict parity, preferring pre-rendered static `.html` files when present before falling back to `_placeholder.html`.
- Eliminate background `EventSource` error loops, broken `localhost` admin links, broken `SuccessCard` native cover previews, and duplicate in-flight batch scan submissions on mobile.
- Ensure `v1.0.0` release builds, manifests, scripts, skills, and documentation ship with production `https://iqoqo.cc` defaults and zero stale `v0.9.3` blocks or package misnamings.

**Non-Goals:**
- Implementing offline IndexedDB collection caching (scheduled for `v1.0.2` `C109`) or paid store Fastlane signing (`v1.0.2` `C110`).

## Decisions

### 1. Dual SSR + Client-Hydrated Views for `/share/[token]` and `/u/[username]`
- **Decision:** Follow the exact pattern proven on `WorkPage` / `WorkDetailClient`:
  - On web SSR (`token !== "_placeholder"`), `SharedCollectionPage` and `PublicProfilePage` fetch initial data on the server, emit `<JsonLdScript />` and SEO metadata, and pass `initialData` into `<SharedCollectionClient initialToken={token} initialData={...} />` / `<PublicProfileClient initialUsername={username} initialProfile={...} initialItems={...} />`.
  - On Capacitor static export (`token === "_placeholder"`), the page renders `<SharedCollectionClient initialToken="_placeholder" initialData={null} />`, which resolves the runtime `token` / `username` via `useResolvedRouteParam()` and fetches `/api/public/share/${token}` or `/api/public/u/${username}` + `/items` via `apiClient` (resolving `${instanceUrl}/api/...`).

### 2. Synchronous `inFlightBarcodesRef` Lock in Batch Scanner
- **Decision:** Maintain `const inFlightBarcodesRef = useRef<Set<string>>(new Set())` in `ScanPage` (`or` inside `useBatchMode`). Check `if (isCooldownActive(canonicalId) || inFlightBarcodesRef.current.has(canonicalId)) return;` synchronously *before* the first `await`, add `canonicalId` to `inFlightBarcodesRef.current`, and remove it in `finally`. Suppress the redundant initial `triggerScanHaptic()` when batch mode will immediately fire `triggerSuccessHaptic()` / `triggerErrorHaptic()`.

### 3. Production `https://iqoqo.cc` Fallback Without Hijacking Web `window.location.origin`
- **Decision:** In `getPublicBaseUrl()` (`frontend/lib/utils.ts`):
  1. On `isNativeApp()`, return `getSyncInstanceUrl()` -> `NEXT_PUBLIC_INSTANCE_URL` -> `NEXT_PUBLIC_FRONTEND_URL` -> `"https://iqoqo.cc"` (never `localhost`).
  2. On standard web (`!isNativeApp()`), return `NEXT_PUBLIC_FRONTEND_URL` (if non-localhost or explicitly configured) -> `window.location.origin` (allowing local self-hosted web users on `http://localhost:8000` to generate working local share links!) -> `"https://iqoqo.cc"`.

## Risks / Trade-offs

- **[Raising `minSdkVersion` from `23` to `26`]** -> Aligns `variables.gradle` with `docs/MOBILE_TARGETS.md` (Android 8.0+, covering >97% of active Android devices, native adaptive icons `v26`, and hardware-backed Keystore APIs).
