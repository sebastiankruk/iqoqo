## Context

See `proposal.md` for motivation. In Capacitor 7 Android and iOS builds, the Next.js frontend is packaged as a static export (`out/`) served from local origin `https://localhost` (Android) or `capacitor://localhost` (iOS). While Axios API requests in `frontend/lib/api/client.ts` are dynamically rewritten by an async request interceptor to target `${instanceUrl}/api`, three categories of browser interactions bypass Axios:
1. OAuth navigation in `login/page.tsx` and `register/page.tsx` (`window.location.href = "/api/auth/login/google"`).
2. Cover art `<Image src={getCoverUrl(...)} />` rendering (`resolveApiUrl()` synchronously returning relative `/api/static/covers/...`).
3. Android 15 (API 35) enforced edge-to-edge window layout where WebView content extends behind the status bar and display cutout unless system window insets and CSS `env(safe-area-inset-*)` are applied.

## Goals / Non-Goals

**Goals:**
- Route native OAuth initiation through `@capacitor/browser` against the remote `instanceUrl` and auto-close the browser sheet upon deep-link completion.
- Ensure top and bottom bars respect system status bar, Pixel camera hole, and navigation bar insets across Android 15+ and iOS.
- Synchronously resolve cover art URLs in `getCoverUrl()` / `resolveApiUrl()` against the active remote `instanceUrl` when running in a native WebView.
- Route unauthenticated users to `/login` after initial server onboarding and expose a persistent `Sign In` / `Profile` tab in the mobile bottom navigation bar.

**Non-Goals:**
- Modifying backend Flask OAuth routes or introducing HTML rendering in Flask.
- Changing web browser relative URL behavior (`/api/static/covers/...` remains relative on standard web).

## Decisions

### 1. Synchronous Instance URL Cache for `resolveApiUrl()`
- **Decision:** Keep an in-memory `cachedInstanceUrl` in `frontend/lib/capacitor/storage.ts` mirrored to `window.localStorage.getItem(INSTANCE_URL_KEY)`. Update it whenever `getInstanceUrl()`, `setInstanceUrl()`, or `clearAllMobileStorage()` runs, and expose a synchronous `getSyncInstanceUrl(): string | null` helper. In `frontend/lib/utils.ts:resolveApiUrl()`, if `isNativeApp()` is true and `getSyncInstanceUrl()` returns a base URL, prefix the resolved `/api/...` path with that instance URL. Also allow `getSyncInstanceUrl()` origin inside `getCoverUrl()` when full URLs are passed.
- **Rationale:** `getCoverUrl()` is called synchronously during React render across dozens of components (`ItemCard`, `FreshArrivals`, `ItemHeader`, `ManifestationDetailClient`). Making `getCoverUrl()` async would require refactoring every image render into an async effect. Mirroring the non-sensitive `instanceUrl` in memory + `localStorage` keeps `getCoverUrl()` 100% synchronous while `@capacitor/preferences` remains the durable native source of truth.
- **Alternatives Considered:** Converting `getCoverUrl()` to an async hook — rejected due to unnecessary render waterfall and broad component churn.

### 2. `@capacitor/browser` for Native OAuth Launch
- **Decision:** In `frontend/app/login/page.tsx` and `frontend/app/register/page.tsx`, extract a shared helper `startNativeOrWebOAuth(provider: "google" | "apple", callbackUrl?: string)`. When `isNativeApp()` is true, read `await getInstanceUrl()`, construct `${instanceUrl}/api/auth/login/${provider}?mobile_origin=capacitor`, and invoke `await Browser.open({ url })`. In `frontend/lib/capacitor/navigation.ts:handleDeepLink()`, call `await Browser.close().catch(() => {})` after persisting the token so the Custom Tab / Safari sheet dismisses cleanly.
- **Rationale:** Google OAuth blocks embedded WebView user agents (`403 disallowed_useragent`), and local WebView origin `https://localhost` has no `/api/auth/login/*` backend. `@capacitor/browser` uses Chrome Custom Tabs on Android and `SFSafariViewController` on iOS, which comply with Google/Apple OAuth policies and share system session state.

### 3. Dual-Layer Inset Protection (Android Theme + CSS Safe-Area)
- **Decision:**
  1. In `frontend/android/app/src/main/res/values/styles.xml`, set `<item name="android:fitsSystemWindows">true</item>` on `AppTheme.NoActionBar`.
  2. In `frontend/app/layout.tsx`, export `export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" }`.
  3. In `frontend/components/dashboard/navbar.tsx` and `frontend/components/scanner/top-bar.tsx`, apply `pt-[env(safe-area-inset-top,0px)]` to the top bar container and `pb-[env(safe-area-inset-bottom,0px)]` to the fixed bottom navigation bar.
- **Rationale:** Android 15 (compileSdk 35) enforces edge-to-edge window drawing by default. Combining `fitsSystemWindows="true"` with CSS `env(safe-area-inset-top)` ensures both Android status bars / camera cutouts and iOS Dynamic Island / Home indicators are respected.

### 4. Onboarding-to-Login Handoff & 5-Tab Bottom Bar
- **Decision:** In `frontend/components/mobile/onboarding-screen.tsx`, when `OnboardingScreen` invokes `onConnected`, check `await getAuthToken()`. If null, call `router.push("/login")`. In `frontend/components/dashboard/navbar.tsx`, add a 5th tab to the mobile bottom navigation bar: when `profile` is present, render **Profile** (`/profile` with `User` icon); when unauthenticated, render **Sign In** (`/login` with `LogIn` icon).
- **Rationale:** Eliminates the dead-end guest state after choosing a server on first launch and ensures authentication / profile / server switching is always one tap away on mobile viewports.

## Risks / Trade-offs

- **[Risk] First render before `getInstanceUrl()` resolves on cold start** → **Mitigation:** `OnboardingGuard` already gates initial native render until `getInstanceUrl()` resolves (`checking` state), which populates `cachedInstanceUrl` before any collection or cover component mounts. Additionally, `localStorage` fallback is synchronous on subsequent cold starts.
- **[Risk] `Browser.close()` throwing on Android if Custom Tab was already dismissed by user or intent** → **Mitigation:** Wrap `Browser.close()` in a `.catch(() => {})` no-op guard.
