## 1. Synchronous Instance URL Cache & Cover Art Resolution

- [x] 1.1 Update `frontend/lib/capacitor/storage.ts` to maintain a synchronous in-memory + `localStorage` mirror of the active instance URL (`getSyncInstanceUrl(): string | null`), hydrated during `getInstanceUrl()` and updated in `setInstanceUrl()` and `clearAllMobileStorage()`, and verify via unit tests in `frontend/__tests__/lib/capacitor/storage.test.ts`
- [x] 1.2 Update `frontend/lib/utils.ts` (`resolveApiUrl` and `getCoverUrl`) so that when `isNativeApp()` is true and `getSyncInstanceUrl()` is non-null, relative `/api/static/covers/...` and `/static/covers/...` paths resolve to `${instanceUrl}/api/static/covers/...`, and verify via unit tests in `frontend/__tests__/lib/utils-cover-mobile.test.ts`

## 2. Native OAuth System Browser Launch & Auto-Close

- [x] 2.1 Update `frontend/app/login/page.tsx` and `frontend/app/register/page.tsx` so Google and Apple OAuth buttons use `@capacitor/browser` (`Browser.open({ url: "${instanceUrl}/api/auth/login/${provider}?mobile_origin=capacitor" })`) when `isNativeApp()` is true, and verify via unit tests in `frontend/__tests__/app/login/page.test.tsx`
- [x] 2.2 Update `frontend/lib/capacitor/navigation.ts` (`handleDeepLink`) to invoke `Browser.close().catch(() => {})` after persisting a token from an `iqoqo://auth-exchange` deep link, and verify via unit tests in `frontend/__tests__/lib/capacitor/navigation.test.ts`

## 3. System Window & Safe-Area Inset Protection

- [x] 3.1 Add `<item name="android:fitsSystemWindows">true</item>` to `AppTheme.NoActionBar` in `frontend/android/app/src/main/res/values/styles.xml` and export `viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" }` in `frontend/app/layout.tsx`, verifying Next.js build succeeds
- [x] 3.2 Add safe-area top and bottom inset padding (`pt-[env(safe-area-inset-top,0px)]` and `pb-[env(safe-area-inset-bottom,0px)]`) to `frontend/components/dashboard/navbar.tsx` and `frontend/components/scanner/top-bar.tsx`, and verify component rendering in `frontend/__tests__/components/dashboard/mobile-bottom-nav.test.tsx`

## 4. Post-Onboarding Login Routing & Bottom Bar Account Tab

- [x] 4.1 Update `frontend/components/mobile/onboarding-screen.tsx` (`OnboardingGuard`) so that upon connecting to an instance, if `await getAuthToken()` is null, the user is navigated directly to `/login`, and verify via `frontend/__tests__/components/mobile/onboarding-screen.test.tsx`
- [x] 4.2 Update `frontend/components/dashboard/navbar.tsx` to include a 5th mobile bottom navigation item (`Sign In` linking to `/login` when unauthenticated, `Profile` linking to `/profile` when authenticated) with localized strings in `frontend/messages/en.json` and `frontend/messages/pl.json`, and verify via `frontend/__tests__/components/dashboard/mobile-bottom-nav.test.tsx`

## 5. Build, APK Verification & Quality Gate

- [x] 5.1 Run `make secret-scan`, `make lint`, frontend unit tests, and `make mobile-android-apk` to verify the complete Capacitor static export and Android APK compile cleanly with zero errors
