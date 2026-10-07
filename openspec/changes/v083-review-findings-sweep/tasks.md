## 1. Query Keys Refactor (MOD-4, MOD-15)

- [ ] 1.1 Create `query-keys.ts` in `frontend/lib/api/hooks/` and export all hardcoded query keys (e.g. `['collections']`, `['roadmaps']`, `['globalStats']`, `['profile']`, `['users']`, `['collection-grid']`). Verify that `query-keys.ts` exports these constants.
- [ ] 1.2 Update `collections.ts`, `roadmap.ts`, `user.ts`, `intents.ts`, `stats.ts`, and `infinite-hooks.ts` to import and use the new query keys instead of hardcoded strings. Verify by checking there are no hardcoded array keys in those files.
- [ ] 1.3 Update `frontend/components/admin/relation-management-dialog.tsx` to use targeted query invalidation with the centralized query keys, replacing broad `qc.invalidateQueries()`. Verify via code review.

## 2. API Hook and Types (MOD-5, MOD-6, MOD-11)

- [ ] 2.1 Update `frontend/lib/api/hooks/admin.ts:76` to set `staleTime: 30_000` for `useFrbrTree`. Verify the value is `30_000`.
- [ ] 2.2 Add `useDeleteWorkIntent` mutation hook in `frontend/lib/api/hooks/intents.ts` and ensure it invalidates the correct query keys on success. Verify hook is correctly typed.
- [ ] 2.3 Refactor `frontend/types/frbr.ts` to replace generic `Record<string, unknown>` for common meta fields with specific interfaces (`WorkMeta`, `ManifestationMeta`). Verify TypeScript compilation succeeds without errors.

## 3. Backend and Scripts (MOD-9, MOD-12)

- [ ] 3.1 Update `frontend/components/admin/relation-management-dialog.tsx:~191` to use strict validation (`Number(s)` and `Number.isInteger()`) for IDs instead of `parseInt`. Verify that invalid strings are caught.
- [ ] 3.2 Update `app/api/roadmap.py` to add `page` (default 1) and `limit` (default 50) query parameters to `get_roadmaps`, and implement SQL `LIMIT` and `OFFSET`. Verify by hitting the endpoint or checking unit tests for pagination support.
