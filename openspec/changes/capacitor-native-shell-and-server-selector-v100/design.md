## Context

In `origin/feat/1.0.0/mobile-capacitor`, the Capacitor TypeScript wrappers (`platform.ts`, `storage.ts`, `server-selector.tsx`, `onboarding-screen.tsx`) were created, but `npx cap add android` and `npx cap add ios` had not yet been committed. In `C96`, we cherry-pick and harden those wrappers onto `v0.9.4`, upgrade to Capacitor 7, and generate the committed `frontend/android/` and `frontend/ios/` projects.

## Goals / Non-Goals

**Goals:**
- Commit working `frontend/android/` and `frontend/ios/` Capacitor projects inside the `frontend/` monorepo.
- Enforce strict separation between `@capacitor/preferences` (for `INSTANCE_URL_KEY` / `INSTANCE_NAME_KEY`) and `@capacitor-community/secure-storage` (for `AUTH_TOKEN_KEY`).
- Provide a seamless HASS-style `ServerSelector` and `OnboardingGuard` on first native launch.

**Non-Goals:**
- Native OAuth deep-link exchange and Sign in with Apple (handled in `C97`).

## Decisions

### Split Storage Security (`Preferences` vs `SecureStoragePlugin`)
* **Decision:** Store `INSTANCE_URL_KEY`, `INSTANCE_NAME_KEY`, and `LOCALE_KEY` in `@capacitor/preferences`, and strictly store `AUTH_TOKEN_KEY` in `@capacitor-community/secure-storage`.
* **Rationale:** Plain-text `SharedPreferences` / `NSUserDefaults` must never hold bearer JWTs or `iqo_*` Personal Access Tokens. `@capacitor-community/secure-storage` uses iOS Keychain and Android Keystore-backed `EncryptedSharedPreferences`.

## Risks / Trade-offs

- **Risk:** Self-hosted instances with trailing slashes or missing `https://` prefix fail health checks.
  - **Mitigation:** Normalize input URLs (strip trailing slashes, default to `https://` unless `localhost` / private IP) and verify against `/api/health` with a 10s timeout.
