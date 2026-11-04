## Why
Because **iqoqo** is a decentralized, self-hosted digital library (`https://iqoqo.kruk.cc`, `https://library.local`, etc.), the native Android and iOS apps cannot hardcode a single backend URL. We need the Capacitor 7 native project shells (`frontend/android/` and `frontend/ios/`), a Home Assistant (HASS)-style Server Selector, and hardware-encrypted token storage (`@capacitor-community/secure-storage`).

## What Changes

- **Capacitor 7 Monorepo & Committed `android/` + `ios/` Projects:** Add `@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/ios`, `@capacitor/app`, `@capacitor/browser`, `@capacitor/haptics`, `@capacitor/keyboard`, `@capacitor/preferences`, `@capacitor/splash-screen`, `@capacitor/status-bar`, and `@capacitor-community/secure-storage` to `frontend/package.json`. Create `frontend/capacitor.config.ts` (`appId: "cc.iqoqo.app"`, `webDir: "out"`), PWA `frontend/public/manifest.json` + icons, and initialize `frontend/android/` and `frontend/ios/` native projects with WebView static path fallback rules.
- **Platform Detection & Split Secure Storage (`platform.ts`, `storage.ts`, `locale.ts`, `splash.ts`):** Store non-sensitive `INSTANCE_URL_KEY` and `INSTANCE_NAME_KEY` in `@capacitor/preferences` and sensitive `AUTH_TOKEN_KEY` (JWT or `iqo_*` PAT) in `@capacitor-community/secure-storage` (iOS Keychain / Android EncryptedSharedPreferences).
- **HASS-Style `ServerSelector` & `OnboardingGuard`:** Build `frontend/components/mobile/server-selector.tsx` and `onboarding-screen.tsx` to verify user-supplied instance URLs against `/api/health` and `/api/auth/providers`, persist the instance URL/name, and allow switching instances from the login/profile screens.
- **Dynamic API Client Interceptor:** Extend `frontend/lib/api/client.ts` so native requests dynamically set `config.baseURL = "${instanceUrl}/api"` and inject `Authorization: Bearer ${token}` from secure storage.

## Capabilities

### New Capabilities
- `capacitor-shell-and-server-selector`: Capacitor 7 iOS/Android native project wrappers, HASS-style dynamic instance selector, split Preferences/SecureStorage wrapper, and dynamic `apiClient` interceptor.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/package.json`, `frontend/capacitor.config.ts`, `frontend/public/manifest.json`, `frontend/icons/*`
- `frontend/android/**`, `frontend/ios/**`
- `frontend/lib/capacitor/{platform,storage,locale,splash}.ts`
- `frontend/components/mobile/{server-selector,onboarding-screen}.tsx`
- `frontend/lib/api/client.ts`, `frontend/components/providers.tsx`
