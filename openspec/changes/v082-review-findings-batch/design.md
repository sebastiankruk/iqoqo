## Context

The v0.8.2 release focuses on addressing security and performance findings from recent audits. These are primarily localized changes but touch across multiple modules including public API routes, SQLAlchemy data models, OAuth pipelines, and React Query caching.

## Goals / Non-Goals

**Goals:**
- Apply standard rate limitings using the existing `limiter` utility to public endpoints.
- Optimize specific SQLAlchemy queries causing N+1 overhead using `joinedload` or `selectinload`.
- Enhance input validation logic in OAuth flow and profile updates without schema migrations.
- Replace React component remount hacks with native TanStack Query cache updates.

**Non-Goals:**
- Introducing new caching infrastructure (e.g., Redis) or changing the database schema.
- Refactoring the entire OAuth or User Profile services beyond the specified fixes.

## Decisions

- **Rate Limits via Decorator**: We will use the existing `@limiter.limit()` pattern instead of middleware to allow granular control (60/min for read, 30/min for write) across `app/api/public_items.py`, `app/api/public_profile.py`, `app/api/lending.py`, and `app/api/roadmap.py`.
- **Query Optimization**: Use `.options(selectinload(User.roles))` and `.options(selectinload(Role.permissions))` for Admin User Lists due to 1-to-many relationships. For FRBR Service RDF Enrichment, use `joinedload(cls.contributor)` as it is a direct relationship.
- **Shim Removal**: The `_PublicModuleShim` is obsolete. We will refactor imports system-wide to point directly to submodules (`app.api.public_items`, etc.).
- **TanStack Query Cache Updates**: In `frbr-editor.tsx`, we replace `setLastFetched(Date.now())` with `queryClient.setQueryData`. This provides instantaneous UI feedback on mutations without network roundtrips.

## Risks / Trade-offs

- [Risk: Rate Limit False Positives] -> Mitigation: Ensure tests cover standard usage patterns to confirm limits aren't too tight. Use IP or User Token as the key depending on auth state.
- [Risk: N+1 Regression] -> Mitigation: Write explicit tests that assert query counts for the targeted APIs to catch regressions in the future.
