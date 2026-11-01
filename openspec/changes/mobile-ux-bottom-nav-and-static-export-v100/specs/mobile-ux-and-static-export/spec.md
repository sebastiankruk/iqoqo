## Purpose
Deliver a 4-tab mobile bottom navigation bar (`Home / Scan / Collection / Search`), fix mobile loading spinner and touch-target UX issues, guard `/admin/*` on native builds, and enable Next.js static export (`CAPACITOR_BUILD=true`) without rewriting dynamic path URLs (`/item/[id]`).

## ADDED Requirements

### Requirement: 4-Action Mobile Bottom Navigation Bar

The mobile bottom navigation bar SHALL expose exactly four primary collector actions: `Home`, `Scan`, `Collection`, and `Search`, and SHALL NOT render a `Login` tab in the bottom action bar.

#### Scenario: Authenticated or guest user views bottom navigation on mobile viewport
- **GIVEN** a mobile viewport (`< 640px`) or native Capacitor shell
- **WHEN** the navigation bar renders
- **THEN** it displays `Home` (`/`), `Scan` (`/scan`), `Collection` (`/collection`), and `Search` with $\le 4$ interactive items in the bottom bar, while profile/login/server actions reside in the top header menu.

### Requirement: Zero-URL-Rewrite Static Export for Dynamic FRBR Routes

When built with `CAPACITOR_BUILD=true`, the Next.js frontend SHALL export static shells for `/item/[id]`, `/manifestation/[id]`, `/work/[id]`, `/expression/[id]`, `/u/[username]`, `/share/[token]`, and `/help/[slug]` without rewriting application links to query parameters.

#### Scenario: Navigating to `/item/42` in static export / Capacitor mode
- **GIVEN** the frontend was built with `CAPACITOR_BUILD=true`
- **WHEN** the user navigates to `/item/42`
- **THEN** `useResolvedRouteParam("id")` resolves `"42"` from the URL path and fetches `GET /api/items/42` without requiring `/item?id=42`.

### Requirement: Native Admin Route Exclusion Guard

The mobile application shell SHALL exclude administrative management surfaces (`/admin/*`) and redirect administrative users to the external system browser.

#### Scenario: User navigates to `/admin/settings` inside native Capacitor app
- **GIVEN** `isNativeApp()` is `true`
- **WHEN** the `/admin/*` layout renders
- **THEN** it blocks inline rendering of admin forms and presents a button to open `${instanceUrl}/admin` in `@capacitor/browser`.
