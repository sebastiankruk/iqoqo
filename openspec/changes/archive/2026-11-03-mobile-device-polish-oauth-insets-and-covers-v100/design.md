## Context

See `proposal.md` for motivation. In Capacitor 7 Android and iOS builds, the Next.js frontend is packaged as a static export (`out/`) served from local origin `https://localhost` (Android) or `capacitor://localhost` (iOS). In addition to initial OAuth, insets, and cover resolution, production verification on a physical Pixel device surfaced critical runtime behaviors:
1. Dynamic page requests (`/item/123.txt`) were intercepted by Android's `RouteProcessor` and rewritten to HTML (`_placeholder.html`), causing Next.js flight parser crashes that reset navigation back to root.
2. Cold-start launch URLs (`https://localhost/`) triggered unconditional `router.replace("/")` in the native deep link handler.
3. User avatars from external OAuth providers (e.g. Google's `lh3.googleusercontent.com`) were either mutilated by API resolvers or rejected with 403/404 by Google due to `Referer: https://localhost/`.
4. Next.js static exports lack a Node.js server lifecycle, making cookie-based `router.refresh()` internationalization completely inoperative.
5. Inactive `<video>` elements rendered Chromium's default media player play arrow, while batch mode buttons suffered from vertical layout misalignment.
6. Mobile navigation contained redundant controls (scan and language buttons in the top bar), invisible bell icons against navy backgrounds, and lacked brand app launcher icons.

## Goals / Non-Goals

**Goals:**
- Route native OAuth initiation through `@capacitor/browser` against the remote `instanceUrl` and auto-close the browser sheet upon deep-link completion.
- Ensure top and bottom bars respect system status bar, Pixel camera hole, and navigation bar insets across Android 15+ and iOS.
- Synchronously resolve cover art and user avatar URLs against the active remote `instanceUrl` or external CDN with `no-referrer` protection.
- Route unauthenticated users to `/login` after initial server onboarding and expose a persistent `Sign In` / `Profile` tab in the mobile bottom navigation bar.
- Prevent client navigation loops on cold-start and ensure Android `RouteProcessor` serves static assets and flight payload text files correctly.
- Provide client-side internationalization with instant language switching in static export builds.
- Polish camera scanner UI, suppress Chromium video placeholders, and align batch mode controls.
- Streamline mobile navbar, hide empty notifications bell, and equip the Android app with official iqoqo brand launcher icons.

**Non-Goals:**
- Modifying backend Flask OAuth routes or introducing HTML rendering in Flask.
- Changing web browser relative URL behavior (`/api/static/covers/...` remains relative on standard web).

## Decisions

### 1. Synchronous Instance URL Cache for Covers & Avatars
- **Decision:** Keep an in-memory `cachedInstanceUrl` in `frontend/lib/capacitor/storage.ts` mirrored to `window.localStorage.getItem(INSTANCE_URL_KEY)`. Expose `resolveAvatarUrl()` in `frontend/lib/utils.ts` and update `frontend/components/ui/avatar.tsx` to use it with `referrerPolicy="no-referrer"` and `onError` fallback to user initials.
- **Rationale:** `getCoverUrl()` and `resolveAvatarUrl()` are called synchronously during render. External Google avatars cannot be prefixed with `instanceUrl` and cannot leak `localhost` referrers.

### 2. `@capacitor/browser` for Native OAuth Launch
- **Decision:** In `frontend/app/login/page.tsx` and `frontend/app/register/page.tsx`, launch OAuth flows using `@capacitor/browser` targeting `${instanceUrl}/api/auth/login/${provider}?mobile_origin=capacitor`. In `frontend/lib/capacitor/navigation.ts:handleDeepLink()`, call `await Browser.close().catch(() => {})`.
- **Rationale:** Google OAuth rejects embedded WebViews (`403 disallowed_useragent`). Chrome Custom Tabs and Safari sheets preserve security and session cookies.

### 3. Dual-Layer Inset Protection (Android Theme + CSS Safe-Area)
- **Decision:** Configure `<item name="android:fitsSystemWindows">true</item>` on `AppTheme.NoActionBar` in `frontend/android/app/src/main/res/values/styles.xml`, set `viewportFit: "cover"` in `frontend/app/layout.tsx`, and apply `pt-[env(safe-area-inset-top,0px)]` and `pb-[env(safe-area-inset-bottom,0px)]`.
- **Rationale:** Android 15 enforces edge-to-edge layout. Dual-layer handling protects UI elements across both Android display cutouts and iOS Dynamic Island.

### 4. Dynamic Route Asset Preservation in `MainActivity.java` & Deep-Link Guard
- **Decision:** In `frontend/android/app/src/main/java/cc/iqoqo/app/MainActivity.java`, update `RouteProcessor` to ignore static assets (`.js`, `.css`, `_next/`) and rewrite `.txt` flight requests to `_placeholder.txt` rather than `_placeholder.html`. In `frontend/lib/capacitor/navigation.ts`, remove unconditional `router.replace("/")` when launch URL is `https://localhost/`.
- **Rationale:** Serving HTML for RSC `.txt` requests breaks Next.js client-side navigation. Unconditional root replacement in deep-link handlers caused page clicks to snap back to the home page.

### 5. Client-Side Internationalization (`ClientI18nProvider`)
- **Decision:** Implement `ClientI18nProvider` in `frontend/components/i18n-provider.tsx` loading both `en.json` and `pl.json` (~80KB total) into memory. Listen for `LOCALE_CHANGE_EVENT` dispatched by `setLocaleCookie()` and read `getSavedLocale()` from Capacitor Preferences / localStorage.
- **Rationale:** In static export builds, `getLocale()` and `getMessages()` run at build time. Dynamic client-side provider allows instantaneous switching between Polish and English without server reloads.

### 6. Video Element Overlay & Batch Mode Alignment
- **Decision:** In `frontend/app/scan/page.tsx`, attach a transparent SVG `poster` and `opacity-0 pointer-events-none` when `scannerActive` is false. In `batch-scan-toggle.tsx`, match `h-9 rounded-xl border border-border/40` dimensions and enforce `min-w-0` on inputs.
- **Rationale:** Chromium displays an enormous media player play arrow when an empty `<video>` is present in a WebView. Unifying heights and flex boundaries prevents horizontal overflow and vertical clipping on mobile screens.

### 7. Navbar Streamlining & Official App Launcher Icons
- **Decision:** In `navbar.tsx`, hide top-bar scan and language buttons on mobile (`hidden sm:flex` / `hidden md:flex`). In `notification-center.tsx`, change icon color to `text-white/90` and return `null` when `notifications.length === 0`. Generate Android adaptive and density icons from `frontend/assets/icon.svg` via `@capacitor/assets`.
- **Rationale:** Removes UI clutter on portrait phones, ensures bell visibility, and equips the application with official iqoqo brand identity.

## Risks / Trade-offs

- **[Risk] In-memory bundle size for multi-language catalogs** → **Mitigation:** English and Polish dictionaries total ~80KB uncompressed (<15KB gzipped), well within acceptable budgets for mobile clients.
- **[Risk] RouteProcessor pattern drift on new dynamic routes** → **Mitigation:** All dynamic routes follow canonical `_placeholder` patterns covered by route definitions.
