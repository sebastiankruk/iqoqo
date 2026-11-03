## 1. Synchronous Instance URL Cache, Cover Art, & Avatar Depiction Resolution

- [x] 1.1 Update `frontend/lib/capacitor/storage.ts` to maintain a synchronous in-memory + `localStorage` mirror of the active instance URL (`getSyncInstanceUrl(): string | null`), hydrated during `getInstanceUrl()` and updated in `setInstanceUrl()` and `clearAllMobileStorage()`, and verify via unit tests in `frontend/__tests__/lib/capacitor/storage.test.ts`
- [x] 1.2 Update `frontend/lib/utils.ts` (`resolveApiUrl`, `getCoverUrl`, and `resolveAvatarUrl`) so that when `isNativeApp()` is true and `getSyncInstanceUrl()` is non-null, relative `/api/static/covers/...`, `/static/covers/...`, and avatar paths resolve to `${instanceUrl}/...`, and verify via unit tests in `frontend/__tests__/lib/utils-cover-mobile.test.ts`
- [x] 1.3 Update `frontend/components/ui/avatar.tsx` to use `resolveAvatarUrl()`, apply `referrerPolicy="no-referrer"` to eliminate Google CDN 403/404 blocks, and add `onError` fallback to user initials, verifying via `frontend/__tests__/components/ui/avatar.test.tsx`

## 2. Native OAuth System Browser Launch & Auto-Close

- [x] 2.1 Update `frontend/app/login/page.tsx` and `frontend/app/register/page.tsx` so Google and Apple OAuth buttons use `@capacitor/browser` (`Browser.open({ url: "${instanceUrl}/api/auth/login/${provider}?mobile_origin=capacitor" })`) when `isNativeApp()` is true, and verify via unit tests in `frontend/__tests__/app/login/page.test.tsx`
- [x] 2.2 Update `frontend/lib/capacitor/navigation.ts` (`handleDeepLink`) to invoke `Browser.close().catch(() => {})` after persisting a token from an `iqoqo://auth-exchange` deep link, and verify via unit tests in `frontend/__tests__/lib/capacitor/navigation.test.ts`
- [x] 2.3 Configure `<intent-filter>` for scheme `iqoqo` in `frontend/android/app/src/main/AndroidManifest.xml` and Android `intent://` fallback in `frontend/app/auth-exchange/page.tsx`, and verify via deep link tests in `frontend/__tests__/lib/capacitor/navigation.test.ts`

## 3. Dynamic Route Asset Preservation & Deep-Link Launch Stability

- [x] 3.1 Update `frontend/lib/capacitor/navigation.ts` (`handleDeepLink`) to eliminate unconditional `router.replace("/")` on cold starts when `launch.url` is `https://localhost/`, and verify via `frontend/__tests__/lib/capacitor/navigation.test.ts`
- [x] 3.2 Update `frontend/android/app/src/main/java/cc/iqoqo/app/MainActivity.java` (`RouteProcessor`) to preserve static assets (`.js`, `.css`, `_next/`) and route RSC flight payloads (`.txt`) to `_placeholder.txt` rather than HTML documents, verifying via Android compilation and Next.js static export

## 4. System Window & Safe-Area Inset Protection

- [x] 4.1 Add `<item name="android:fitsSystemWindows">true</item>` to `AppTheme.NoActionBar` in `frontend/android/app/src/main/res/values/styles.xml` and export `viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" }` in `frontend/app/layout.tsx`, verifying Next.js build succeeds
- [x] 4.2 Add safe-area top and bottom inset padding (`pt-[env(safe-area-inset-top,0px)]` and `pb-[env(safe-area-inset-bottom,0px)]`) to `frontend/components/dashboard/navbar.tsx` and `frontend/components/scanner/top-bar.tsx`, and verify component rendering in `frontend/__tests__/components/dashboard/mobile-bottom-nav.test.tsx`

## 5. Post-Onboarding Login Routing & Mobile Bottom Navigation Bar

- [x] 5.1 Update `frontend/components/mobile/onboarding-screen.tsx` (`OnboardingGuard`) so that upon connecting to an instance, if `await getAuthToken()` is null, the user is navigated directly to `/login`, and verify via `frontend/__tests__/components/mobile/onboarding-screen.test.tsx`
- [x] 5.2 Update `frontend/components/dashboard/navbar.tsx` to include a 5th mobile bottom navigation item (`Sign In` linking to `/login` when unauthenticated, `Profile` linking to `/profile` when authenticated) with localized strings in `frontend/messages/en.json` and `frontend/messages/pl.json`, and verify via `frontend/__tests__/components/dashboard/mobile-bottom-nav.test.tsx`

## 6. Client-Side Internationalization & Dynamic Language Switching

- [x] 6.1 Create `ClientI18nProvider` in `frontend/components/i18n-provider.tsx` loading in-memory message catalogs for `en` and `pl`, wrapping `NextIntlClientProvider` in `frontend/app/layout.tsx`, and verify via `frontend/__tests__/components/i18n-provider.test.tsx`
- [x] 6.2 Update `frontend/lib/locale-cookie.ts` to persist language choices via `setSavedLocale` (Capacitor Preferences + localStorage) and dispatch `LOCALE_CHANGE_EVENT`, and verify via `frontend/__tests__/lib/locale-cookie.test.ts`

## 7. Camera Scanner UI Polish & Batch Mode Alignment

- [x] 7.1 Update `frontend/app/scan/page.tsx` with transparent SVG `poster` and conditional opacity on `<video>` to suppress Chromium's default media player play arrow, and verify scanner tests in `frontend/__tests__/components/scanner/camera-capture.test.tsx`
- [x] 7.2 Unify heights (`h-9`), border radius (`rounded-xl`), and borders between the quick lookup search form and `BatchScanToggle` button in `frontend/app/scan/page.tsx` and `frontend/components/scanner/batch-scan-toggle.tsx`, and verify via `frontend/__tests__/components/scanner/batch-scan-toggle.test.tsx`

## 8. Mobile Navbar Streamlining & Official App Launcher Icons

- [x] 8.1 In `frontend/components/dashboard/navbar.tsx`, hide redundant top-bar scan button on mobile viewports (`hidden sm:flex`), keep top-bar language switcher hidden on mobile (`hidden md:flex`), and add desktop navbar "Profile" link, verifying via `frontend/__tests__/components/dashboard/navbar.test.tsx`
- [x] 8.2 In `frontend/components/dashboard/notification-center.tsx`, update bell icon color to `text-white/90` and return `null` when `notifications.length === 0`, and verify via `frontend/__tests__/components/dashboard/notification-center.test.tsx`
- [x] 8.3 Generate Android adaptive icons (`ic_launcher.xml`, `ic_launcher_round.xml`, `ic_launcher_foreground.png`, `ic_launcher_background.png`), density mipmaps, and splash screens from `frontend/assets/icon.svg` via `@capacitor/assets`

## 9. Build, APK Verification & Quality Gate

- [x] 9.1 Run `make secret-scan`, `make lint`, frontend unit test suite (all 194 test suites, 1626+ tests passing), and `make mobile-android-apk` to verify clean builds with zero errors
