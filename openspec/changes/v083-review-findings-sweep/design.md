## Context

See proposal.md for motivation. This sweep covers various frontend and backend components.

## Goals / Non-Goals

**Goals:**
- Fix potential bugs related to input parsing and cache invalidation.
- Standardize the React Query key usage.
- Add simple cursor/offset pagination to the roadmaps endpoint.

**Non-Goals:**
- No change to UI layouts or features.
- No change to the underlying database schemas.

## Decisions

- **React Query Keys (`MOD-4`, `MOD-15`):** Introduce an exported const object `queryKeys` or individual exports in `query-keys.ts` rather than hardcoding array structures across the application. When updating caches, invalidations should use exact keys or `queryClient.setQueryData` rather than wiping out broad caches (`qc.invalidateQueries()`).
- **Strict Number Parsing (`MOD-9`):** Usage of `Number(s)` and `Number.isInteger(n)` over `parseInt` prevents `"12abc"` returning `12`, which is safer for relation IDs.
- **Roadmap Pagination (`MOD-12`):** Use simple SQL limit/offset in `app/api/roadmap.py` with standard `page` (default 1) and `limit` (default 50) parameters.

## Risks / Trade-offs

- **Risk:** Modifying `run_update.py` might break if the import paths are not in the PYTHONPATH. → **Mitigation:** Ensure the script explicitly adds the current working directory to `sys.path` if needed or relies on the existing module structure.
- **Risk:** Broad refactoring of query keys may lead to missing a key invalidation. → **Mitigation:** Rely on TypeScript to ensure all usages match the exported keys.
