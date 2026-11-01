## 1. Capacitor 7 Dependencies, Config & Native Platform Projects

- [ ] 1.1 Add Capacitor 7 dependencies (`@capacitor/core`, `@capacitor/cli`, `@capacitor/android`, `@capacitor/ios`, `@capacitor/app`, `@capacitor/browser`, `@capacitor/haptics`, `@capacitor/keyboard`, `@capacitor/preferences`, `@capacitor/splash-screen`, `@capacitor/status-bar`, `@capacitor-community/secure-storage`) to `frontend/package.json`.
- [ ] 1.2 Create `frontend/capacitor.config.ts`, `frontend/public/manifest.json`, and app icons (`frontend/icons/*`, `frontend/assets/*`) and link the manifest in `frontend/app/layout.tsx`.
- [ ] 1.3 Initialize `frontend/android/` and `frontend/ios/` projects via `npx cap add android` and `npx cap add ios`, and configure WebView fallback routing so dynamic paths (`/item/123`, `/manifestation/456`, etc.) resolve to their static `_placeholder` shells without 404s.

## 2. Platform Utilities, Secure Storage & HASS Server Selector

- [ ] 2.1 Implement `frontend/lib/capacitor/platform.ts`, `storage.ts` (`@capacitor/preferences` for instance URL/name, `@capacitor-community/secure-storage` for `AUTH_TOKEN_KEY`), `locale.ts`, and `splash.ts`.
- [ ] 2.2 Implement `frontend/components/mobile/server-selector.tsx` and `frontend/components/mobile/onboarding-screen.tsx` (`OnboardingGuard`), and mount `OnboardingGuard` in `frontend/components/providers.tsx`.
- [ ] 2.3 Add Capacitor request interceptor in `frontend/lib/api/client.ts` to dynamically inject `baseURL` (`${instanceUrl}/api`) and `Authorization: Bearer ${token}`.
- [ ] 2.4 Add `Mobile` namespace translation keys to `frontend/messages/en.json` and `frontend/messages/pl.json` (sentence case).

## 3. Verification & Tests

- [ ] 3.1 Author unit and component tests in `frontend/__tests__/lib/capacitor/platform.test.ts`, `frontend/__tests__/lib/capacitor/storage.test.ts`, `frontend/__tests__/components/mobile/server-selector.test.tsx`, `frontend/__tests__/components/mobile/onboarding-screen.test.tsx`, and `tests/test_health_endpoint.py`.
- [ ] 3.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
