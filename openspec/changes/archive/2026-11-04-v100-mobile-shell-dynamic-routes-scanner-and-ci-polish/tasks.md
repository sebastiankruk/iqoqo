## 1. Client-Hydrated `/share/[token]` & `/u/[username]` + Static Placeholder Guards

- [x] 1.1 Create `frontend/components/public/shared-collection-client.tsx` (`useResolvedRouteParam("token")`) and wire `frontend/app/share/[token]/page.tsx` so web SSR keeps full HTML + `<JsonLdScript />` while Capacitor `/share/_placeholder.html` fetches and renders shared collections on Android and iOS.
- [x] 1.2 Create `frontend/components/public/public-profile-client.tsx` (`useResolvedRouteParam("username")`) and wire `frontend/app/u/[username]/page.tsx` so web SSR keeps full HTML + `<JsonLdScript />` while Capacitor `/u/_placeholder.html` fetches and renders public user profiles and paginated items.
- [x] 1.3 Add `if (id === "_placeholder")` build-time short-circuits to `frontend/app/item/[id]/page.tsx` and `frontend/app/manifestation/[id]/page.tsx` (preventing `/api/items/NaN` fetches during static export), and wrap fallback `manifestation.meta?.["cover_url"]` in `getCoverUrl(...)` in `manifestation/[id]/page.tsx` and `manifestation-detail-client.tsx`.

## 2. Native Routers, SSE Guard, Admin Browser Guard & Prod URL Defaults

- [x] 2.1 Update both `frontend/android/app/src/main/java/cc/iqoqo/app/MainActivity.java` and `frontend/ios/App/App/AppDelegate.swift` so pre-rendered static `.html` bundle assets (e.g. `/help/<slug>.html`) are served directly when present before falling back to `_placeholder.html`.
- [x] 2.2 Update `TransitionEventsListener` in `frontend/components/providers.tsx` to skip relative cookie `EventSource("/api/v1/events/stream")` when `isNativeApp()` is `true` and include `/auth-exchange` in `isPublicRoute`.
- [x] 2.3 Refactor `frontend/app/admin/layout.tsx` to import `isNativeApp()` from `@/lib/capacitor/platform` and resolve `${instanceUrl}${pathname}` via `getInstanceUrl()` before calling `openExternalUrl()`.
- [x] 2.4 Replace staging `"https://preview.iqoqo.cc"` fallback with `"https://iqoqo.cc"` in `frontend/lib/utils.ts`, `frontend/scripts/build-capacitor.js`, and `.github/workflows/mobile-build.yml`; preserve `window.location.origin` on non-native web deployments in `getPublicBaseUrl()`; and add `SIGINT`/`SIGTERM` restoration handlers in `build-capacitor.js`.

## 3. Scanner Batch In-Flight Lock & Native `SuccessCard` Cover Resolution

- [x] 3.1 Add synchronous `inFlightBarcodesRef` locking before `await apiClient.post("/scan")` in `frontend/app/scan/page.tsx` (and/or `batch-scan-toggle.tsx`), verify `res.data?.success`, eliminate double haptic firing in batch mode, and invalidate `["works", "shelf"]` and `["expressions", "shelf"]`.
- [x] 3.2 Replace `${process.env.NEXT_PUBLIC_API_URL || ""}${coverUrl}` in `frontend/components/scanner/success-card.tsx` with `getCoverUrl(coverUrl)`.

## 4. Native Manifests, Scripts, Skills/Docs Cleanup & OpenSpec Release Archive

- [x] 4.1 Set `android:allowBackup="false"` in `frontend/android/app/src/main/AndroidManifest.xml`, set `minSdkVersion = 26` in `frontend/android/variables.gradle`, set `versionName "1.0.0"` in `frontend/android/app/build.gradle` (and iOS `MARKETING_VERSION = 1.0.0`), and remove `armv7` from `frontend/ios/App/App/Info.plist`.
- [x] 4.2 Harden `scripts/setup-android-sdk.sh` (`mktemp -d`, `trap` cleanup, SHA-256 checksum verification), update `scripts/setup-ios-tools.sh` CocoaPods pin for Xcode 16 / macOS 15 compatibility, and update `Makefile` `test-e2e-mobile` `--grep` for case-insensitive matching.
- [x] 4.3 Remove duplicate `## Upcoming (v0.9.3 & Beyond)` sections across all 17 `.agents/skills/*/SKILL.md` and `.gemini/gems/*.md` files; update `docs/CHANGELOG.md` and `docs/MOBILE_SIDELOAD.md` (`capacitor-secure-storage-plugin`, Web Share API, `?code=` OAuth handoff, CI artifact accuracy); and add regression assertions across `tests/test_ai_skills_integrity.py`, `tests/test_mobile_readiness.py`, `tests/bash/mobile_scripts.bats`, and frontend Vitest/Playwright suites (`shared-collection-client.test.tsx`, `public-profile-client.test.tsx`, `scan/page.test.tsx`, `utils.test.ts`).
- [x] 4.4 Verify clean under `make secret-scan`, `make lint`, and test suites.
