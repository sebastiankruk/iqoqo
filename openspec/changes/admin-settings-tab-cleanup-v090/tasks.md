## 1. Sidebar & Settings Page Cleanup

- [ ] 1.1 Remove `Monetization` and `Security` links from `frontend/components/admin/admin-sidebar.tsx`
- [ ] 1.2 Remove placeholder `monetization`, `security`, and empty `federation` blocks from `frontend/app/admin/settings/page.tsx`
- [ ] 1.3 Ensure default tab routing in `page.tsx` smoothly routes to `instance` or first available custodian tab without landing on empty tabs

## 2. Test Verification

- [ ] 2.1 Update `frontend/__tests__/components/admin/admin-sidebar.test.tsx` to assert that Monetization and Security are not rendered
- [ ] 2.2 Verify navigation between Settings, API Integrations, Users, and Roles operates without errors
