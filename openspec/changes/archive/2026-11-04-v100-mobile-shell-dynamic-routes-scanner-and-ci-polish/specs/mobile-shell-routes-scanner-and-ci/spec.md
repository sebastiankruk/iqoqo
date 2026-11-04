## Purpose

Deliver functional client-hydrated `/share/[token]` and `/u/[username]` views on Capacitor mobile shells, strict Android/iOS asset routing parity, native `EventSource` and `AdminLayout` guards, race-free batch barcode scanning with remote cover previews, production `https://iqoqo.cc` defaults, hardened native manifests and setup scripts, and clean `v1.0.0` skills and documentation.

## ADDED Requirements

### Requirement: Client-Hydrated `/share/[token]` & `/u/[username]` Views on Native Mobile

`frontend/app/share/[token]/page.tsx` and `frontend/app/u/[username]/page.tsx` SHALL delegate rendering to client components (`SharedCollectionClient` and `PublicProfileClient`) that resolve runtime route parameters via `useResolvedRouteParam()` when served from `_placeholder.html` on Capacitor mobile shells while preserving full SSR HTML and Schema.org JSON-LD on web deployments. `item/[id]/page.tsx` and `manifestation/[id]/page.tsx` SHALL short-circuit `_placeholder` during static export without requesting `/items/NaN` or `/manifestations/NaN`.

#### Scenario: Native mobile user opens a shared collection deep link
- **GIVEN** the Capacitor app opens `/share/abc123token` (served via `/share/_placeholder.html`)
- **WHEN** `SharedCollectionClient` mounts in the WebView
- **THEN** `useResolvedRouteParam("token")` resolves `"abc123token"`, fetches `${instanceUrl}/api/public/share/abc123token`, and renders the collection title, author, items grid, and RSS/share controls rather than an empty `<Navbar />` page.

#### Scenario: Native mobile user opens a public profile deep link
- **GIVEN** the Capacitor app opens `/u/collector_jane` (served via `/u/_placeholder.html`)
- **WHEN** `PublicProfileClient` mounts in the WebView
- **THEN** `useResolvedRouteParam("username")` resolves `"collector_jane"`, fetches `${instanceUrl}/api/public/u/collector_jane` and paginated `/items`, and renders the profile header, inventory checker, and collection grid.

### Requirement: Native Shell Asset Routing, SSE Guard, Admin External Browser & Prod URL Defaults

Both Android (`MainActivity.java`) and iOS (`AppDelegate.swift`) native routers SHALL serve existing static `.html` bundle assets (such as pre-rendered `/help/<slug>.html`) before falling back to `_placeholder.html`. On native mobile (`isNativeApp() === true`), `TransitionEventsListener` SHALL NOT open relative cookie-authenticated `EventSource("/api/v1/events/stream")` connections, `AdminLayout` SHALL open `${instanceUrl}${pathname}` in the system browser rather than `localhost`, and default fallback URLs across `utils.ts`, `build-capacitor.js`, and `.github/workflows/mobile-build.yml` SHALL target `"https://iqoqo.cc"` without hijacking non-native web `window.location.origin`.

#### Scenario: Pre-rendered Help article is opened on Android and iOS
- **GIVEN** `/help/camera-to-catalog.html` is pre-rendered in the Capacitor static bundle
- **WHEN** the Android or iOS WebView navigates to `/help/camera-to-catalog`
- **THEN** the native router serves `/help/camera-to-catalog.html` directly, and falls back to `/help/_placeholder.html` only for unknown dynamic slugs.

#### Scenario: Native user opens Admin portal from `/admin/settings`
- **GIVEN** a native mobile user connected to `https://my-library.example.com` visits `/admin/settings`
- **WHEN** the user taps `"Open in Web Browser"` in `AdminLayout`
- **THEN** `openExternalUrl` opens `https://my-library.example.com/admin/settings` (never `https://localhost/admin/settings`).

### Requirement: Race-Free Scanner Batch Mode & Remote Cover Resolution in `SuccessCard`

`ScanPage` batch mode SHALL guard in-flight `/scan` submissions synchronously per barcode so consecutive camera frames cannot trigger duplicate concurrent `POST /scan` calls, SHALL validate `res.data.success`, SHALL invalidate Work and Expression shelf queries alongside Items and Stats, and `SuccessCard` SHALL resolve cover image URLs via `getCoverUrl()` against the active mobile `instanceUrl`.

#### Scenario: Rapid consecutive barcode frames arrive while `/scan` is in-flight
- **GIVEN** continuous batch mode is enabled on `/scan`
- **WHEN** barcode `9780451524935` is detected on two frames 100ms apart while the first `POST /scan` is still pending
- **THEN** only 1 `POST /scan` request is sent, `["items"]`, `["works", "shelf"]`, `["expressions", "shelf"]`, and `["stats"]` are invalidated on completion, and a single haptic confirmation fires.

#### Scenario: Scanned item with `/static/covers/...` cover renders in `SuccessCard` on native mobile
- **GIVEN** a native mobile user connected to `https://my-library.example.com` scans an item whose `cover_url` is `"/static/covers/42.jpg"`
- **WHEN** `SuccessCard` renders the cover preview
- **THEN** the image `src` resolves via `getCoverUrl()` to `"https://my-library.example.com/api/static/covers/42.jpg"` (or `${instanceUrl}/static/covers/42.jpg`).

### Requirement: Native Manifest Hardening, Tooling Safety & Documentation/Skills Integrity

Android and iOS project manifests SHALL disable cloud auto-backup (`android:allowBackup="false"`), align `minSdkVersion = 26` and `versionName = "1.0.0"` / `MARKETING_VERSION = 1.0.0` with `docs/MOBILE_TARGETS.md`, omit deprecated 32-bit `armv7` from `Info.plist`, use `mktemp -d` + SHA-256 verification in `scripts/setup-android-sdk.sh`, and keep all AI Skills, Gemini Gems, `CHANGELOG.md`, and `MOBILE_SIDELOAD.md` free of duplicate `v0.9.3` sections or inaccurate package names.

#### Scenario: AI Skills and Gems integrity test enforces zero duplicate Upcoming sections
- **GIVEN** all `.agents/skills/*/SKILL.md` and `.gemini/gems/*.md` files
- **WHEN** `pytest tests/test_ai_skills_integrity.py` runs
- **THEN** every persona skill and gem contains exactly one `## Upcoming` section targeting `v1.0.0`–`v1.0.2` and zero stale `## Upcoming (v0.9.3 & Beyond)` headings.
