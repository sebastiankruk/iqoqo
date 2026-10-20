## Why
Instance administrators need full visibility and control over connected Fediverse peers, trust levels, and activity queues from the admin dashboard.
## What Changes

- Implement `/admin/federation` route and views in `frontend/app/admin/federation/page.tsx`.
- Create `federation-instances.tsx` and `federation-activity.tsx` components.
- Extend `instance-settings.tsx` with `FEDERATION_AUTO_ACCEPT_FOLLOWS`, `FEDERATION_DEFAULT_TRUST`, and key fingerprint.
- Add Federation link to `admin-sidebar.tsx` gated by `config:federation` permission.
- Add complete `en.json` and `pl.json` translation keys.

## Capabilities

### New Capabilities
- `admin-federation-dashboard`: Admin Federation management UI, instance trust settings, activity logs, and full i18n localization

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Adds admin frontend pages, API hooks, and localization strings.
