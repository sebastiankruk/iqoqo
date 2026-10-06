---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

When unauthenticated users try to access protected routes like a shared wishlist or collection (e.g. `/<username>/wishlist` or `/<username>/collection`), they currently receive a 404 Not Found error. This happens because the system fails to load the protected resources and falls back to a 404, or the routing logic simply throws a 404.

## Goals / Non-Goals

**Goals:**

- Detect unauthenticated access to protected routes.
- Redirect the user to the `/login` page (or equivalent auth page).
- Ideally, preserve the intended URL using a `?redirect=` parameter or similar Next.js mechanism, so users land on the shared content after logging in.

**Non-Goals:**

- Changing the authentication mechanism.
- Making protected routes public.

## Decisions

- **Routing Middleware / HOC Update**: We will intercept the unauthorized state in the Next.js routing layer (e.g. `middleware.ts` or within the specific page components/layout). If a user is not authenticated and the route requires it, we trigger a redirect instead of throwing a 404.
- **Handling API 401s**: If the 404 is caused by an API returning 401/403 and the frontend blindly mapping that to a 404 state, we will update the API error handling in the frontend to explicitly redirect to login on 401.

## Risks / Trade-offs

- [Risk] Redirect loops if the login page itself is somehow protected or misconfigured. → [Mitigation] Ensure the middleware explicitly allows access to the login/auth routes.
