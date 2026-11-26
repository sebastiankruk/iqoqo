## Why

Mobile users who maintain multiple iqoqo instances (for example, a production home server and a preview or family library) currently have to overwrite their single saved server URL, which wipes their auth token and invalidates their offline cache on every switch.

Target release: scheduled for **v1.2.0** (`C156`).

## What Changes

- Replace single-server storage in `frontend/lib/capacitor/storage.ts` with a multi-server profile registry (`ServerProfile[]`) that preserves backward compatibility with existing single-server installations and keeps the profile schema cleanly extensible for `v1.3.0` local/external dual URLs (`C159`).
- Isolate `SecureStoragePlugin` auth tokens and `frontend/lib/capacitor/offline-cache.ts` snapshots per `serverId` so switching between servers never leaks credentials or mixes offline collections/wishlists/queues.
- Upgrade `ServerSelector` (`frontend/components/mobile/server-selector.tsx`) and mobile navigation/footer server indicator to support adding, naming, switching, and removing saved servers.

## Capabilities

### New Capabilities

<!-- None -->

### Modified Capabilities

- `capacitor-shell-and-server-selector`: Support storing multiple named iqoqo server profiles, switching the active server without wiping other servers' credentials, and displaying/selecting from saved servers.
- `mobile-offline-cache-and-deeplinks`: Namespace offline collection, wishlist, profile snapshots, and manual entry queues by active `serverId` so multi-server switching preserves per-server offline state.

## Impact

- Frontend Capacitor Storage & Cache: `frontend/lib/capacitor/storage.ts`, `frontend/lib/capacitor/offline-cache.ts`
- Frontend Mobile UI & i18n: `frontend/components/mobile/server-selector.tsx`, connected-server footer/header indicator, `frontend/messages/en.json`, `frontend/messages/pl.json`
- Tests: `frontend/__tests__/lib/capacitor/` and `frontend/__tests__/components/mobile/`, plus Playwright mobile viewport switching tests
- Specs: `openspec/specs/capacitor-shell-and-server-selector/spec.md`, `openspec/specs/mobile-offline-cache-and-deeplinks/spec.md`
