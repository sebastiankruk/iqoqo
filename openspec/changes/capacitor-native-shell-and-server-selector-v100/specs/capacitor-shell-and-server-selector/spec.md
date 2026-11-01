## Purpose
Initialize Capacitor 7 iOS and Android projects inside `frontend/`, provide hardware-encrypted token storage, and deliver a HASS-style Server Selector for self-hosted instances.

## ADDED Requirements

### Requirement: Hardware-Encrypted Auth Token Storage on Mobile

The mobile storage layer SHALL store authentication tokens (`AUTH_TOKEN_KEY`) exclusively in hardware-backed encrypted storage (`@capacitor-community/secure-storage`) and SHALL store non-sensitive instance metadata (`INSTANCE_URL_KEY`, `INSTANCE_NAME_KEY`) in `@capacitor/preferences`.

#### Scenario: Storing and retrieving auth token on native platform
- **GIVEN** the application is running on iOS or Android (`isNativeApp() === true`)
- **WHEN** `setAuthToken(token)` is called
- **THEN** the token is written via `SecureStoragePlugin.set` and never written to plain-text `Preferences`.

### Requirement: HASS-Style Dynamic Server Selector & Onboarding Guard

On first native launch when no `INSTANCE_URL_KEY` is configured, `OnboardingGuard` SHALL render `ServerSelector`, which verifies the entered server URL against `GET /api/health` before persisting it and routing to `/login`.

#### Scenario: User connects to a valid self-hosted iqoqo instance
- **GIVEN** `getInstanceUrl()` returns `null` on a native device
- **WHEN** the user enters `https://iqoqo.kruk.cc` and taps Verify Connection
- **THEN** `ServerSelector` probes `https://iqoqo.kruk.cc/api/health`, displays the verified instance name, persists the URL via `setInstanceUrl()`, and routes to `/login`.

### Requirement: Dynamic Base URL & Bearer Interceptor in API Client

In native Capacitor mode, `apiClient` SHALL dynamically prepend `${instanceUrl}/api` and attach `Authorization: Bearer ${token}` to outbound API requests.

#### Scenario: Native client dispatches an authenticated API request
- **GIVEN** `isNativeApp()` is `true`, `instanceUrl` is `https://iqoqo.kruk.cc`, and `authToken` is `jwt-123`
- **WHEN** `apiClient.get("/items")` is invoked
- **THEN** the request is sent to `https://iqoqo.kruk.cc/api/items` with header `Authorization: Bearer jwt-123`.
