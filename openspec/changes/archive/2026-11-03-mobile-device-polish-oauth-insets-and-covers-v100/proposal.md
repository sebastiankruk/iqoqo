## Why

On-device verification of the Capacitor 7 Android APK on a Google Pixel against `preview.iqoqo.cc` surfaced UX, routing, and integration gaps that block seamless native usage:
1. Tapping "Sign in with Google" attempted to navigate the local WebView (`https://localhost/api/auth/login/google`) instead of opening the system browser against the configured instance URL.
2. Android 15 edge-to-edge rendering placed the top navigation bar underneath the system status bar, clock, battery icons, and Pixel camera cutout.
3. Cover art and user avatar depiction images resolved to relative `/api/static/covers/...` and `/static/...` paths against the local APK origin (`https://localhost`) and failed with HTTP 404, while external Google CDN avatars were blocked due to localhost referrer leakage.
4. Completing the initial server selector dropped unauthenticated users onto `/collection` with no bottom-bar Login/Profile button and no prompt to sign in.
5. Clicking through to an item or manifestation repeatedly redirected back to the root catalog due to cold-start launch URL resetting in deep-link listeners and Android `RouteProcessor` rewriting `.txt` flight data requests into HTML.
6. Language switching was inoperative in native mobile static export because there was no Node.js server to handle cookie-based request reloads.
7. The camera scanner UI displayed a giant Chromium default media play icon when the video stream was inactive, and the batch toggle button suffered from vertical misalignment and squishing.
8. The mobile navbar displayed redundant controls (scan and language buttons in the top bar), an invisible black notification bell, and the Android package lacked official iqoqo brand launcher icons.

## What Changes

- **Native OAuth System Browser Launch (`frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, `frontend/lib/capacitor/navigation.ts`):** When `isNativeApp()` is true, launch Google and Apple OAuth flows via `@capacitor/browser` targeting the active remote instance URL, and automatically close the system browser (`Browser.close()`) when `handleDeepLink` captures the `iqoqo://auth-exchange` callback.
- **System Window & Safe-Area Insets (`frontend/android/app/src/main/res/values/styles.xml`, `frontend/app/layout.tsx`, `frontend/components/dashboard/navbar.tsx`, `frontend/components/scanner/top-bar.tsx`):** Configure `android:fitsSystemWindows="true"` on `AppTheme.NoActionBar`, export `viewport: Viewport = { viewportFit: "cover", width: "device-width", initialScale: 1 }`, and apply `pt-[env(safe-area-inset-top,0px)]` and `pb-[env(safe-area-inset-bottom,0px)]` to navigation bars.
- **Remote Instance Cover Art & User Avatar Resolution (`frontend/lib/capacitor/storage.ts`, `frontend/lib/utils.ts`, `frontend/components/ui/avatar.tsx`):** Synchronously mirror `instanceUrl` in memory and `localStorage` (`getSyncInstanceUrl()`), resolve relative covers and avatar paths to `${instanceUrl}/...` on native apps, add `referrerPolicy="no-referrer"` to avatar images to prevent Google CDN 403/404 blocks, and provide graceful initials fallback on error.
- **Post-Onboarding Auth Flow & Bottom Navigation Account Tab (`frontend/components/mobile/onboarding-screen.tsx`, `frontend/components/dashboard/navbar.tsx`):** Route unauthenticated users directly to `/login` upon completing initial onboarding, and include a 5th item (**Profile** when authenticated, **Sign In** when unauthenticated) in the mobile bottom navigation bar.
- **Deep-Link Launch Guard & Dynamic Route Asset Processor (`frontend/lib/capacitor/navigation.ts`, `frontend/android/app/src/main/java/cc/iqoqo/app/MainActivity.java`):** Prevent unconditional root redirection when `launch.url` is `https://localhost/`, and update Capacitor's `RouteProcessor` to preserve static assets (`.js`, `.css`, `_next/`) and route RSC flight data (`.txt`) requests to `_placeholder.txt` instead of HTML shells.
- **Client-Side Internationalization & Dynamic Language Switching (`frontend/components/i18n-provider.tsx`, `frontend/lib/locale-cookie.ts`, `frontend/app/layout.tsx`):** Provide `ClientI18nProvider` loading in-memory message catalogs for `en` and `pl`, dispatch `LOCALE_CHANGE_EVENT` and persist to Capacitor Preferences on language toggle, enabling immediate UI translation without requiring a server reload.
- **Camera Scanner UI Polish & Batch Button Alignment (`frontend/app/scan/page.tsx`, `frontend/components/scanner/batch-scan-toggle.tsx`):** Provide transparent SVG video poster and opacity transitions to eliminate Chromium's default media player play overlay, and unify search form and batch mode button heights (`h-9`), curves (`rounded-xl`), and layout boundaries.
- **Navbar Streamlining & Notification Center Optimization (`frontend/components/dashboard/navbar.tsx`, `frontend/components/dashboard/notification-center.tsx`):** Remove redundant top-bar language and scan buttons on mobile viewports, fix notification bell color to high-contrast white against navy navbar, hide the bell completely when empty (`notifications.length === 0`), and add desktop navbar "Profile" link.
- **Official iqoqo Android Adaptive App Icons (`frontend/android/app/src/main/res/`):** Generate adaptive icons, legacy icons, and splash screens across all screen densities from `frontend/assets/icon.svg` via `@capacitor/assets`.

## Capabilities

### New Capabilities
- `mobile-device-polish-and-cover-urls`: Complete mobile device polish covering native system browser OAuth, safe-area insets, remote instance cover and avatar URL resolution, post-onboarding auth routing, deep-link navigation guard, dynamic route asset processing, client-side i18n switching, camera UI video poster suppression, batch button alignment, streamlined navbar controls, and official Android launcher icons.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/lib/capacitor/storage.ts`, `frontend/lib/capacitor/navigation.ts`, `frontend/lib/capacitor/locale.ts`, `frontend/lib/utils.ts`, `frontend/lib/locale-cookie.ts`
- `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, `frontend/app/layout.tsx`, `frontend/app/scan/page.tsx`
- `frontend/components/ui/avatar.tsx`, `frontend/components/i18n-provider.tsx`, `frontend/components/dashboard/navbar.tsx`, `frontend/components/dashboard/notification-center.tsx`, `frontend/components/scanner/top-bar.tsx`, `frontend/components/scanner/batch-scan-toggle.tsx`, `frontend/components/mobile/onboarding-screen.tsx`
- `frontend/android/app/src/main/java/cc/iqoqo/app/MainActivity.java`, `frontend/android/app/src/main/AndroidManifest.xml`, `frontend/android/app/src/main/res/`
- `.context/notes/plan/1.0.x-release-plan.md`
