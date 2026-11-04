## Why

Principal review of `v1.0.0` (PR #392) uncovered one `CRITICAL` mobile route rendering failure, six `MODERATE` mobile shell/scanner/build defects, and six `LOW` native-manifest, script, skill, and documentation gaps:
1. **Blank `/share/[token]` and `/u/[username]` Screens on Mobile (`CRITICAL`):** Both `frontend/app/share/[token]/page.tsx` and `frontend/app/u/[username]/page.tsx` are Server Components that short-circuit `token === "_placeholder"` / `username === "_placeholder"` to `<div className="min-h-screen"><Navbar /></div>` with **zero client data-fetching component**. Opening any `iqoqo://share/<token>` or `/u/<username>` deep link on Android or iOS renders a permanently empty blank screen!
2. **Native Routers, SSE Loop & Admin Browser URL Bugs:** Both Android `MainActivity.java` and iOS `AppDelegate.swift` rewrite `/help/<slug>` directly to `/help/_placeholder.html` even when pre-rendered `/help/<slug>.html` exists; `item/[id]/page.tsx` and `manifestation/[id]/page.tsx` omit `id === "_placeholder"` guards (`fetch("/api/items/NaN")` during static build); `TransitionEventsListener` (`providers.tsx`) opens an infinite failing relative `EventSource("/api/v1/events/stream")` loop on native mobile; and `AdminLayout` (`admin/layout.tsx`) opens `https://localhost/admin` instead of `${instanceUrl}/admin`.
3. **Scanner Batch Concurrency Race & Native `SuccessCard` Cover Bug:** `ScanPage` batch mode only activates cooldown *after* `await apiClient.post("/scan")` completes, allowing multi-frame camera scans to fire duplicate concurrent `/scan` requests while in-flight, omits `["works", "shelf"]` / `["expressions", "shelf"]` invalidations, and `SuccessCard.tsx` uses `${process.env.NEXT_PUBLIC_API_URL || ""}${coverUrl}` instead of `getCoverUrl(coverUrl)`.
4. **Staging `preview.iqoqo.cc` Fallbacks, Native Manifests, Scripts & Docs:** `utils.ts`, `build-capacitor.js`, and `mobile-build.yml` bake staging `"https://preview.iqoqo.cc"` into `1.0.0` production builds (and hijack local web share origins); `AndroidManifest.xml` leaves `android:allowBackup="true"`, `variables.gradle` sets `minSdkVersion = 23` (vs documented `26`), `build.gradle` sets `versionName "1.0"`, and `Info.plist` lists legacy 32-bit `armv7`; `setup-android-sdk.sh` uses predictable `/tmp/cmdline-tools-linux-$$` without checksums; 17 AI Skills/Gems retain duplicate `## Upcoming (v0.9.3 & Beyond)` sections; and `CHANGELOG.md` / `MOBILE_SIDELOAD.md` list inaccurate package/CI artifact names.

## What Changes

- **Client Hydration for `/share/[token]` & `/u/[username]` + Static Placeholder Guards:**
  - Extract `SharedCollectionClient` (`useResolvedRouteParam("token")`) and `PublicProfileClient` (`useResolvedRouteParam("username")`) so SSR preserves full HTML/JSON-LD on web while Capacitor `_placeholder.html` hydrates and renders shared collections and public profiles on Android and iOS.
  - Add `id === "_placeholder"` build-time short-circuits to `item/[id]/page.tsx` and `manifestation/[id]/page.tsx`, and wrap fallback `manifestation.meta?.["cover_url"]` in `getCoverUrl()`.
- **Native Router Asset Preference, SSE Guard, `AdminLayout` & Prod URLs:**
  - Update Android `MainActivity.java` and iOS `AppDelegate.swift` to serve existing `<path>.html` bundle assets (such as pre-rendered `/help/<slug>.html`) before falling back to `_placeholder.html`.
  - Skip relative cookie `EventSource` in `TransitionEventsListener` (`providers.tsx`) when `isNativeApp()` is `true` and add `/auth-exchange` to `isPublicRoute`.
  - Import `isNativeApp` in `AdminLayout` and open `${instanceUrl}${pathname}` via `openExternalUrl`.
  - Switch default public fallback URL from `"https://preview.iqoqo.cc"` to `"https://iqoqo.cc"` across `utils.ts`, `build-capacitor.js`, and `mobile-build.yml`, preserve `window.location.origin` on non-Capacitor local web instances, and add `SIGINT`/`SIGTERM` cleanup handlers to `build-capacitor.js`.
- **Scanner Batch In-Flight Lock & `SuccessCard` Native Cover Resolution:**
  - Add synchronous `inFlightBarcodesRef` deduplication before `await apiClient.post("/scan")` in `ScanPage`, check `res.data?.success`, avoid double haptics, invalidate `["works", "shelf"]` and `["expressions", "shelf"]`, and replace `${NEXT_PUBLIC_API_URL}` with `getCoverUrl(coverUrl)` in `SuccessCard.tsx`.
- **Native Manifests, Setup Scripts, Skills/Docs Cleanup & OpenSpec Archive Gate:**
  - Set `android:allowBackup="false"`, `minSdkVersion = 26`, `versionName "1.0.0"`, iOS `MARKETING_VERSION = 1.0.0`, and remove `armv7` from `Info.plist`.
  - Harden `scripts/setup-android-sdk.sh` (`mktemp -d` + `trap` + SHA-256 verification), modernize `scripts/setup-ios-tools.sh` CocoaPods pin, make `Makefile` `test-e2e-mobile` `--grep` case-insensitive, remove duplicate `## Upcoming (v0.9.3 & Beyond)` from 17 Skills/Gems, align `CHANGELOG.md` / `MOBILE_SIDELOAD.md`, and archive completed `v1.0.0` OpenSpecs on completion.

## Capabilities

### New Capabilities
- `mobile-shell-routes-scanner-and-ci`: Client-hydrated `/share` & `/u` mobile views, Android/iOS router asset resolution, native SSE/Admin guards, scanner batch concurrency lock, production `iqoqo.cc` defaults, hardened native manifests/scripts, and `v1.0.0` documentation/skills synchronization.

### Modified Capabilities
- None.

## Impact

- **Frontend & Native:** `frontend/app/share/[token]/page.tsx`, `frontend/components/public/shared-collection-client.tsx` (new), `frontend/app/u/[username]/page.tsx`, `frontend/components/public/public-profile-client.tsx` (new), `frontend/app/item/[id]/page.tsx`, `frontend/app/manifestation/[id]/page.tsx`, `frontend/components/manifestation/manifestation-detail-client.tsx`, `frontend/components/providers.tsx`, `frontend/app/admin/layout.tsx`, `frontend/app/scan/page.tsx`, `frontend/components/scanner/success-card.tsx`, `frontend/lib/utils.ts`, `frontend/scripts/build-capacitor.js`, `frontend/android/**`, `frontend/ios/**`
- **CI, Scripts & Docs:** `.github/workflows/mobile-build.yml`, `Makefile`, `scripts/setup-android-sdk.sh`, `scripts/setup-ios-tools.sh`, `docs/CHANGELOG.md`, `docs/MOBILE_SIDELOAD.md`, `.agents/skills/*/SKILL.md`, `.gemini/gems/*.md`
- **Tests:** `tests/test_mobile_readiness.py`, `tests/test_ai_skills_integrity.py`, `tests/bash/mobile_scripts.bats`, `frontend/__tests__/...`
