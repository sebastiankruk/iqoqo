---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

When an unregistered or unauthenticated user clicks on a shared link that requires authentication (like a wishlist or collection link), the system currently returns a 404 error. This is a poor user experience, as it doesn't inform the user why they cannot see the content. It should instead redirect them to the login page so they can authenticate and view the shared content.

## What Changes

- Update routing logic to detect when a user attempts to access a protected route without authentication.
- Instead of returning or rendering a 404 Not Found error, the system will trigger a redirect to the login page.
- Ideally, preserve the intended destination URL so the user can be redirected there after a successful login.

## Capabilities

### New Capabilities

- `unauth-redirects`: Handling unauthenticated access to protected routes by redirecting to the login flow rather than failing with a 404.

### Modified Capabilities

-

## Impact

- Frontend: Routing logic for protected pages (collections, wishlists, settings).
- Backend (if applicable): Ensure API endpoints returning 401/403 are handled correctly by the frontend to trigger a login redirect rather than a 404.
