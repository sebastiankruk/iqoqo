## Context

See `proposal.md` for motivation. Currently, the frontend assumes Google SSO is always available, leading to broken flows on unconfigured self-hosted or preview instances.

## Goals / Non-Goals

**Goals:**
- Provide a fast, public, unauthenticated `GET /api/auth/providers` endpoint.
- Conditionally render Google sign-in/sign-up buttons in Next.js based on runtime provider availability.
- Provide clean translation and alert for `oauth_not_configured` query parameters.

**Non-Goals:**
- Implementing additional OAuth providers (e.g. GitHub, Apple) in this release.
- Modifying session cookies or token issuance logic.

## Decisions

- **Decision 1: Runtime endpoint over build-time `NEXT_PUBLIC_*` variable.**
  - *Rationale:* `InstanceSettings` allows instance administrators to configure OAuth keys at runtime without rebuilding the Docker container. A runtime endpoint guarantees immediate alignment.
  - *Alternatives considered:* Static build-time environment variable (requires container rebuild upon config changes).
- **Decision 2: Lightweight caching.**
  - *Rationale:* Provider configuration changes infrequently. The endpoint checks `ConfigService.get("GOOGLE_CLIENT_ID")` and `ConfigService.get("GOOGLE_CLIENT_SECRET")` without heavy database queries.
- **Decision 3: Seamless degradation.**
  - *Rationale:* If the providers endpoint request fails or times out, the frontend defaults to hiding the SSO buttons and displaying standard email/password login.

## Risks / Trade-offs

- **[Risk]** Extra API call on login page load.
  - *Mitigation:* Endpoint is unauthenticated, lightweight (O(1) memory lookup in ConfigService cache), and can be fetched in parallel or prefetched via SWR/TanStack Query.
