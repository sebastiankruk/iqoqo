## Why

On-device verification of the Capacitor 7 Android APK on a Google Pixel against `preview.iqoqo.cc` surfaced four UX and integration gaps that block seamless native usage: (1) tapping "Sign in with Google" attempts to navigate the local WebView (`https://localhost/api/auth/login/google`) instead of opening the system browser against the configured instance URL; (2) Android 15 edge-to-edge rendering places the top navigation bar underneath the system status bar, clock, battery icons, and Pixel camera cutout; (3) cover art images resolve to relative `/api/static/covers/...` paths against the local APK origin (`https://localhost`) and fail with HTTP 404; and (4) completing the initial server selector drops unauthenticated users onto `/collection` with no bottom-bar Login/Profile button and no prompt to sign in.

## What Changes

- **Native OAuth System Browser Launch (`frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, `frontend/lib/capacitor/navigation.ts`):** When `isNativeApp()` is true, launch Google and Apple OAuth flows via `@capacitor/browser` (`Browser.open({ url: "${instanceUrl}/api/auth/login/google?mobile_origin=capacitor" })`) instead of relative `window.location.href`, and automatically close the system browser (`Browser.close()`) when `handleDeepLink` captures the `iqoqo://auth-exchange` callback.
- **System Window & Safe-Area Insets (`frontend/android/app/src/main/res/values/styles.xml`, `frontend/app/layout.tsx`, `frontend/components/dashboard/navbar.tsx`, `frontend/components/scanner/top-bar.tsx`):** Configure `android:fitsSystemWindows="true"` on `AppTheme.NoActionBar`, export `viewport: Viewport = { viewportFit: "cover", width: "device-width", initialScale: 1 }` in `layout.tsx`, and apply `pt-[env(safe-area-inset-top,0px)]` / `pb-[env(safe-area-inset-bottom,0px)]` to sticky top and bottom bars so UI controls never collide with the Pixel camera hole, status bar, or gesture pill.
- **Native Instance Cover Art Resolution (`frontend/lib/capacitor/storage.ts`, `frontend/lib/utils.ts`):** Maintain an in-memory and `localStorage`-synchronized cache of the active `instanceUrl` (`getCachedInstanceUrl()`) hydrated on startup and updated by `setInstanceUrl()`, and update `resolveApiUrl()` / `getCoverUrl()` so that when `isNativeApp()` is true, cover and static asset paths resolve to `${instanceUrl}/api/static/covers/...` instead of hitting `https://localhost` with HTTP 404.
- **Post-Onboarding Auth Flow & Bottom Bar Profile/Sign-In Tab (`frontend/components/mobile/onboarding-screen.tsx`, `frontend/components/dashboard/navbar.tsx`):** After `OnboardingGuard` connects to a server, check whether an auth token exists (`getAuthToken()`); if unauthenticated, navigate directly to `/login`. Additionally, add a 5th action item (**Profile** when authenticated, **Sign In** when unauthenticated) to the mobile bottom navigation bar so login and account/server switching are always reachable with a single thumb tap.

## Capabilities

### New Capabilities
- `mobile-device-polish-and-cover-urls`: Native `@capacitor/browser` OAuth launch, Android/iOS safe-area & camera cutout inset protection, remote instance URL resolution for cover art images, post-onboarding login routing, and bottom-bar Sign In / Profile navigation.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/lib/capacitor/storage.ts`, `frontend/lib/capacitor/navigation.ts`, `frontend/lib/utils.ts`
- `frontend/app/login/page.tsx`, `frontend/app/register/page.tsx`, `frontend/app/layout.tsx`
- `frontend/components/mobile/onboarding-screen.tsx`, `frontend/components/dashboard/navbar.tsx`, `frontend/components/scanner/top-bar.tsx`
- `frontend/android/app/src/main/res/values/styles.xml`
- `.context/notes/plan/1.0.x-release-plan.md`
