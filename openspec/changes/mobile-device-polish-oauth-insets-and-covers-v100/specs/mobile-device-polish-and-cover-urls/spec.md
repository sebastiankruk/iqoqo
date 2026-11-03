## Purpose

Defines native device polish requirements for Capacitor Android and iOS builds, ensuring third-party OAuth authentication opens in the system browser against the configured instance URL, top and bottom navigation bars respect system status bar and camera cutout insets, cover art and avatars resolve against the remote instance URL or external CDN, dynamic navigation and client-side flight data resolve cleanly, internationalization switches dynamically on the client, camera and navbar UI elements are cleanly streamlined, and the Android package carries official iqoqo brand launcher icons.

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

### Requirement: Remote Instance URL Resolution for Cover Art & User Avatars
When running inside a native mobile WebView, the client SHALL resolve relative cover art and avatar paths against the configured remote instance URL rather than the local WebView origin (`https://localhost` or `capacitor://localhost`), and SHALL preserve external avatar URLs while suppressing localhost referrers.

#### Scenario: Collection grid renders cover art from configured remote instance
- **WHEN** the native mobile app connected to `https://preview.iqoqo.cc` renders item or manifestation cards with `cover_url="/api/static/covers/123.jpg"`
- **THEN** `getCoverUrl()` SHALL return `"https://preview.iqoqo.cc/api/static/covers/123.jpg"` so images load with HTTP 200 instead of 404 against `localhost`

#### Scenario: User profile renders external Google avatar without localhost referrer
- **WHEN** a user logs in with Google and has an avatar hosted on `https://lh3.googleusercontent.com/`
- **THEN** the `Avatar` component SHALL load the image with `referrerPolicy="no-referrer"` and fall back gracefully to initials on load failure

### Requirement: Dynamic Route Asset Processing and Deep-Link Launch Stability
The mobile application SHALL correctly serve static assets and Next.js flight data payloads for dynamic routes, and SHALL NOT reset client navigation to root on cold start.

#### Scenario: User taps item card to navigate to item detail
- **WHEN** a user taps an item card linking to `/item/123`
- **THEN** the client-side router SHALL fetch `/item/123.txt` as `_placeholder.txt` flight data without HTML substitution errors, and the detail view SHALL resolve ID `123`

#### Scenario: Cold-start launch URL does not clobber user navigation
- **WHEN** the application boots and `App.getLaunchUrl()` returns `https://localhost/` without an auth token or explicit route
- **THEN** `handleDeepLink` SHALL NOT trigger `router.replace("/")`

### Requirement: Client-Side Internationalization in Static Export
The mobile client SHALL support real-time language toggling between English and Polish within static export environments where server-side rendering is unavailable.

#### Scenario: User switches language to Polish on native mobile device
- **WHEN** a user selects Polish from the user menu
- **THEN** `ClientI18nProvider` SHALL update in-memory message catalogs to Polish and update `document.documentElement.lang` to `pl` immediately without reloading the page

### Requirement: Camera Scanner UI Polish and Video Placeholder Isolation
The camera scanner view SHALL isolate empty video elements from native WebView media controls and SHALL maintain consistent sizing between search input and batch mode toggle.

#### Scenario: Camera scanner page mounts before video stream starts
- **WHEN** the user navigates to `/scan`
- **THEN** the `<video>` element SHALL render a transparent SVG poster and remain hidden until active, preventing Chromium's default play button icon from displaying

#### Scenario: Search input and batch mode toggle align on mobile viewport
- **WHEN** the user views the quick lookup bar on `/scan`
- **THEN** the search form and `BatchScanToggle` button SHALL share identical `h-9 rounded-xl` dimensions and align seamlessly on the same horizontal baseline

### Requirement: Mobile Navbar Streamlining & Official App Launcher Icons
The mobile interface SHALL minimize redundant top-bar actions, conceal empty notification indicators, and supply official iqoqo brand launcher icons.

#### Scenario: Top navigation bar on small mobile viewports
- **WHEN** viewed on viewport width `<640px`
- **THEN** the top bar SHALL conceal redundant scan and language buttons, relying on the bottom navigation bar and user menu respectively

#### Scenario: Notification center with zero notifications
- **WHEN** the authenticated user has no unread or pending notifications
- **THEN** the `NotificationCenter` component SHALL return `null` and omit the bell icon from the top bar

#### Scenario: Android launcher icon display
- **WHEN** the user views the app icon on the Android launcher or home screen
- **THEN** the device SHALL display the official terracotta iqoqo brand icon
