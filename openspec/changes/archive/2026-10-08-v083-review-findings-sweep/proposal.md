## Why

Address low-severity findings and minor architecture improvements from the v0.8.1 code review, scheduled for v0.8.3. These changes improve code quality, type safety, performance, and API structure.

## What Changes

- **MOD-4:** Centralize hardcoded React Query keys in `frontend/lib/api/hooks/` to exported constants in `query-keys.ts`.
- **MOD-5:** Increase `staleTime` for FRBR Tree hook from 1s to 30s.
- **MOD-6:** Add `useDeleteWorkIntent` hook wrapping API mutation and cache invalidation.
- **MOD-9:** Implement strict integer validation in `Relation Management Dialog` to prevent silent parsing errors.
- **MOD-12:** Add pagination parameters (`page`, `limit`) to the `get_roadmaps` endpoint and implement SQL limits.
- **MOD-15:** Replace global query invalidation with targeted `queryClient.setQueryData` in Relation Management.
- **MOD-11:** Enhance TypeScript type safety for FRBR metadata types, replacing generic `Record<string, unknown>`.

## Capabilities

### New Capabilities
None

### Modified Capabilities
None (These are bug fixes and minor internal architectural improvements. `skip_specs: true` has been set).

## Impact

- Frontend API hooks and types will be cleaner and less prone to typos or cache invalidation misses.
- API performance for roadmaps will be improved for large datasets due to pagination.
- Admin UI for relations will be more robust against bad inputs and perform more efficient cache updates.
