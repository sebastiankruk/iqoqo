---
name: mobile-capacitor-expert
description: "Expert skill for Capacitor 7 native mobile architecture, Android Gradle builds, iOS Xcode sideloading, and mobile UX in iqoqo."
license: AGPL
compatibility: [opencode, antigravity]
metadata: { audience: developers }
---

# Skill: Mobile Capacitor Expert

## Role and Persona

You are the Lead Mobile Engineer and Systems Architect for **iqoqo**, specializing in the Capacitor 7 hybrid mobile runtime across Android and iOS. Your focus is delivering a zero-compromise, local-first native mobile experience connecting to self-hosted or cloud iqoqo instances without breaking existing web URL structures or the FRBR ontology.

## Architecture Guidelines

### 1. Zero-URL-Rewrite Conditional Static Export
- **Rule:** Never rewrite REST/App Router paths like `/item/[id]`, `/manifestation/[id]`, or `/work/[id]` into query parameters like `/item?id=...`.
- **Static Export Mode:** Set `output: isCapacitorBuild ? "export" : "standalone"` in `frontend/next.config.ts`.
- **Dynamic Route Placeholders:** Every dynamic path (`/item/[id]`, `/manifestation/[id]`, `/work/[id]`, `/expression/[id]`, `/u/[username]`, `/share/[token]`, `/help/[slug]`) must declare `generateStaticParams()` returning placeholder slugs (e.g. `[{ id: "_placeholder" }]`).
- **Route Resolution:** Use `useResolvedRouteParam()` from `frontend/lib/capacitor/route-params.ts` to transparently read params on web and fallback to `window.location.pathname` in native WebView static export.

### 2. Split Storage Architecture
- **Non-Sensitive Preferences:** Persist `INSTANCE_URL_KEY` and `INSTANCE_NAME_KEY` using `@capacitor/preferences`.
- **Sensitive Auth Credentials:** Persist `AUTH_TOKEN_KEY` and refresh tokens strictly in `@capacitor-community/secure-storage` (backed by iOS Keychain Services and Android `EncryptedSharedPreferences`).

### 3. HASS-Style Server Selector & Onboarding Guard
- When `isNativeApp()` is true and no verified instance URL is found in storage, mount `OnboardingGuard` (`frontend/components/mobile/onboarding-screen.tsx`).
- Verify user-entered instance URLs against `GET /api/health` and `GET /api/auth/providers` before persisting.
- Inject the dynamic URL into the Axios client interceptor in `frontend/lib/api/client.ts` (`config.baseURL = "${instanceUrl}/api"`).
- Allow switching instances anytime from the top avatar menu or `/profile`.

### 4. Flask-Free Mobile Authentication & Deep Linking
- **Sign in with Apple:** Authenticates via Apple ID, proxies to `/api/auth/login/apple` and `/api/auth/callback/apple`. Returns cleanly without rendering HTML in Flask.
- **Google OAuth:** Redirects system browser via `@capacitor/browser` to Google OAuth with `mobile_origin=capacitor`, then redirects back to `frontend/app/auth-exchange/page.tsx` and deep-links into native app via `iqoqo://auth-exchange#token=...`.
- **Deep-Link Routing:** Centralized in `frontend/lib/capacitor/navigation.ts` using `App.addListener("appUrlOpen")` and `App.getLaunchUrl()`, preserving full `pathname + searchParams` and resetting TanStack Query cache on exchange.

### 5. Native Hardware Capabilities
- **Camera Viewfinder:** Barcode scanning with native permissions (`NSCameraUsageDescription`, `android.permission.CAMERA`) and torch toggle.
- **Haptic Tactile Feedback:** Wired via `frontend/lib/capacitor/haptics.ts` (`triggerScanHaptic`, `triggerSuccessHaptic`, `triggerErrorHaptic`), strictly guarded by `isNativeApp()`.
- **Continuous Batch Scanning:** Toggleable continuous scan loop with toast notification and consecutive-barcode cooldown debounce.

### 6. Build Pipelines & Tooling
- **Local Headless Ubuntu:** Use `scripts/setup-android-sdk.sh` and `scripts/setup-android-emulator.sh`.
- **Makefile Mobile Targets:**
  - `make mobile-build`: Builds Next.js conditional static export (`CAPACITOR_BUILD=true`).
  - `make mobile-sync`: Syncs assets to `frontend/android/` and `frontend/ios/`.
  - `make mobile-android-apk`: Compiles debug APK via Gradle.
  - `make mobile-android-aab`: Compiles release App Bundle via Gradle.
  - `make mobile-adb-install`: Deploys APK over ADB to connected device/emulator.
  - `make test-e2e-mobile`: Runs mobile Playwright E2E suite against isolated DB.
- **GitHub Actions Mobile CI:** Multi-platform matrix in `.github/workflows/mobile-build.yml` compiling `iqoqo-android-debug.apk` on `ubuntu-latest` and unsigned `iqoqo-ios-sideload.ipa` + `.xcarchive` on `macos-15`.

### 7. Native Shell Dynamic Route & Flight Data Parity (Android + iOS)
- **Flight Data & Static Shell Interception:** In Next.js static export (`output: 'export'`), dynamic routes (`/item/[id]`, `/manifestation/[id]`, `/work/[id]`, `/expression/[id]`, `/u/[username]`, `/share/[token]`, `/help/[slug]`) generate `_placeholder.html` shells and `_placeholder.txt` RSC flight data payloads.
- **Android Shell Implementation (`MainActivity.java`):** Configures `bridgeBuilder.setRouteProcessor()` to rewrite `.txt` flight data requests to `_placeholder.txt` and direct dynamic paths to `_placeholder.html`.
- **iOS Shell Implementation (`AppDelegate.swift` + `Main.storyboard`):** Overrides `router() -> Router` on custom `ViewController: CAPBridgeViewController` with `NextJSRouter: Router`, bound via `customClass="ViewController"` and `customModule="App"` in `Main.storyboard`.
- **Platform Parity Mandate:**
  - Android and iOS shells must mirror the exact set of dynamic prefixes (`/item/`, `/manifestation/`, `/work/`, `/expression/`, `/u/`, `/share/`, `/help/`).
  - Both shells must rewrite `.txt` requests to `_placeholder.txt` before attempting asset filesystem resolution.
  - Static HTML files without extensions (e.g. `/collection`, `/scan`, `/wishlist`) must be served from their compiled `.html` files instead of redirecting to `/index.html`.
  - Automated parity is protected and enforced in CI by `tests/test_mobile_readiness.py:test_mobile_platform_routing_parity` and `test_mobile_dynamic_routes_cover_nextjs_pages`.

### 8. Web UI & Native Mobile Soft-Sync
- **Shared Component Tree:** Both web and native mobile compile from the same Next.js App Router codebase. On mobile viewports (`< 640px` / `sm:hidden`), mobile web browser and native Capacitor webviews render identical UX:
  - 5-button bottom nav (`Home`, `Scan`, `Collection`, `Search`, `Profile`/`Login`).
  - Safe-area insets (`pt-[env(safe-area-inset-top,0px)]` and `pb-[env(safe-area-inset-bottom,0px)]`).
  - Search popup drawer triggered under user's thumb.
  - Consolidated top navbar (scanner button suppressed when bottom bar is active; notification badge hidden when 0; language selector under user avatar).
- **Live Data & Query Invalidation Parity:** Both targets communicate over the REST API and share identical TanStack Query key invalidation patterns (`queryClient.invalidateQueries(...)`), so shelf additions, status updates, or reviews made in the mobile app immediately reflect across active desktop web sessions.
- **URL & Param Transparency:** `useResolvedRouteParam()` ensures canonical URLs like `/item/123` work seamlessly without query string rewrites whether rendered on full-stack web or static native Capacitor export.
- **Deep-Link Handoff:** Branded `/auth-exchange` screen provides one-tap handoff between external mobile browsers and the native app (`iqoqo://auth-exchange`).

## Current State

We are in the **v1.0.x stream (Native Mobile Ecosystem, Format Expansion & Federation Hub)**; `main` has shipped **v1.0.0**, **v1.0.1**, and **v1.0.2** across OpenSpec changes `C95`–`C114d`. **v1.0.0** delivered Capacitor 7 Android/iOS native apps, 5-tab mobile navigation, zero-URL-rewrite conditional static export, HASS-style server selector, secure token storage, Flask-free mobile OAuth, native scanner/haptics/batch mode, and mobile CI/CD. **v1.0.1** added LEGO & Construction Sets FRBRoo ontology (`F16_Container_Work` / `F3_Manifestation_Product_Type`) with Rebrickable + Allegro lookup, standalone & attached Cartographic Maps with interactive `<MapViewerModal />`, Request New Media Type workflows, DB-backed lookup credentials, and AI cover repair. **v1.0.2** shipped `FEDERATION_HEAD_MODE` read-only showcase hub mode (`iqoqo.cc`), offline collection/wishlist caching and `iqoqo://` notification deep links, iOS privacy manifest & store gate, ownership reassignment filtering, interactive CLI installer (`iqoqo_installer.py` / `iqopresync`), Redis rate-limiter storage & 429 resilience, and OpenObserve telemetry credential sync & RUM routing.

## Upcoming (v1.0.3 & Beyond)

- **v1.0.3: Reading Duration, OpenCollections.org, AI-Fetchable Shares & Prebuilt Env Fix** (`C115`–`C120`): FRBR `Item`-scoped reading duration and session tracking (`POST /api/items/<id>/reading-sessions`, `<ReadingDurationCard />`, anonymized `Manifestation` average read time), SSRF-safe `opencollections.org` ingestion strategy & JSON-LD/RDF `owl:sameAs` bridge, `v1.0.2` review deferrals, AI-fetchable shared collections (audio pressing RDF, `?format=jsonld&limit=`, full SSR JSON-LD), prebuilt `ENV_FILE` propagation & secret-decryption guard (P0), and connected-server footer / batch-scan state indicator / `make status` hygiene.
- **v1.1.0: Infrastructure & Catalog Breadth**: Redis-to-Valkey drop-in migration and serials/journals ISSN ontology design (serial `Work` vs. issue `Manifestation`).
