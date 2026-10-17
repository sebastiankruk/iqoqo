## Context

In previous versions, administrative settings contained stubbed categories for monetization (Amazon affiliate tracking), security (junk phashes), and federation. As iqoqo approaches v0.9.0 release, having dead or "Coming soon" placeholder cards degrades UX quality and confuses instance administrators.

## Goals / Non-Goals

**Goals:**
- Eliminate unpopulated or dead placeholder tabs from the admin sidebar and settings page.
- Ensure all visible links navigate to functioning administrative workflows.
- Prepare the navigation structure for the upcoming `v0.9.1` Admin Federation Dashboard (`/admin/federation`).

**Non-Goals:**
- Removing underlying database settings in `InstanceSettings` (the settings remain in the DB schema for when features land).
- Prematurely implementing affiliate monetization or hash junk detection.

## Decisions

### 1. Remove Monetization and Security Tabs from Navigation
- **Decision:** Delete the `Monetization` and `Security` items from `admin-sidebar.tsx` and their corresponding render blocks in `app/admin/settings/page.tsx`.
- **Rationale:** Neither tab has operational functionality in v0.9.0. They will be reintroduced with full management UIs in their respective milestones (`v1++`).

### 2. Federation Navigation Bridge
- **Decision:** Remove the empty "Coming soon" card from `/admin/settings`. Federation instance management will launch as a dedicated route (`/admin/federation`) in `v0.9.1` (`admin-federation-dashboard-v091`).
- **Rationale:** Prevents routing confusion between `/admin/settings?tab=federation` and `/admin/federation`.
