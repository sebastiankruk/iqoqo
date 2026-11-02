## Purpose

Defines native device polish requirements for Capacitor Android and iOS builds, ensuring third-party OAuth authentication opens in the system browser against the configured instance URL, top and bottom navigation bars respect system status bar and camera cutout insets, cover art resolves against the remote instance URL instead of local WebView origin, and unauthenticated users are guided to sign in with a persistent bottom-bar account tab.

## ADDED Requirements

### Requirement: Native OAuth System Browser Launch
The mobile client SHALL open Google and Apple OAuth authentication flows in the native system browser (Chrome Custom Tabs on Android, `ASWebAuthenticationSession` / SFSafariViewController on iOS) targeting the configured remote instance URL rather than navigating the embedded WebView to a local origin.

#### Scenario: User initiates Google Sign-In on native mobile app
- **WHEN** a user on a native mobile device taps "Sign in with Google" on `/login` or `/register` while connected to `https://preview.iqoqo.cc`
- **THEN** the client SHALL open `https://preview.iqoqo.cc/api/auth/login/google?mobile_origin=capacitor` in the native system browser via `@capacitor/browser`

#### Scenario: System browser closes automatically on deep-link token handoff
- **WHEN** the native app receives an `iqoqo://auth-exchange?token=...` deep link from the OAuth callback
- **THEN** the client SHALL persist the token to hardware-backed secure storage, close the native system browser overlay, clear query caches, and navigate to the main view

### Requirement: System Status Bar and Camera Cutout Safe-Area Protection
The mobile application SHALL respect device system window insets and safe-area boundaries so that top navigation bars, search inputs, and bottom navigation controls never render underneath the system status bar, clock, battery indicators, camera cutout, or bottom gesture bar.

#### Scenario: Top navigation bar renders below Pixel camera hole and Android status bar
- **WHEN** the Android app launches on a device with a status bar and display cutout (such as Google Pixel running Android 15)
- **THEN** the Android activity theme and top navigation bar SHALL apply safe-area / system window top insets so the brand logo, search bar, and action buttons appear cleanly below the status bar and camera cutout

### Requirement: Remote Instance URL Resolution for Cover Art in Native WebView
When running inside a native mobile WebView, the client SHALL resolve relative cover art paths (`/api/static/covers/...` or `/static/covers/...`) against the configured remote instance URL rather than the local WebView origin (`https://localhost` or `capacitor://localhost`).

#### Scenario: Collection grid renders cover art from configured remote instance
- **WHEN** the native mobile app connected to `https://preview.iqoqo.cc` renders item or manifestation cards with `cover_url="/api/static/covers/123.jpg"`
- **THEN** `getCoverUrl()` SHALL return `"https://preview.iqoqo.cc/api/static/covers/123.jpg"` so images load with HTTP 200 instead of 404 against `localhost`

### Requirement: Post-Onboarding Authentication Routing and Bottom Navigation Account Tab
The mobile client SHALL route unauthenticated users to `/login` immediately after initial server selection and SHALL provide a dedicated account / sign-in tab in the mobile bottom navigation bar.

#### Scenario: Unauthenticated user connects to an instance on initial onboarding
- **WHEN** a user enters `preview.iqoqo.cc` on the onboarding screen, verification succeeds, and no authentication token is stored on the device
- **THEN** the client SHALL navigate to `/login` so the user can immediately sign in

#### Scenario: Mobile bottom navigation displays Sign In when unauthenticated and Profile when authenticated
- **WHEN** a user views the mobile bottom navigation bar on a small viewport
- **THEN** the bar SHALL display 5 items: `Home`, `Scan`, `Collection`, `Search`, and `Sign In` (linking to `/login` when unauthenticated) or `Profile` (linking to `/profile` when authenticated)
